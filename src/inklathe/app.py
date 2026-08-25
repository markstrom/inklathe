from __future__ import annotations

import base64
import binascii
import secrets
import warnings
from mimetypes import guess_type
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError

from .config import Settings
from .jobs import JobStore
from .processing import ProcessOptions, available_bitmap_textures, available_halftones

PACKAGE_DIR = Path(__file__).parent


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    Image.MAX_IMAGE_PIXELS = settings.max_pixels
    store = JobStore(settings)
    bitmap_textures = available_bitmap_textures(settings.texture_dir)
    halftones = available_halftones(settings.texture_dir)
    api = FastAPI(title="InkLathe", version="0.1.0")
    api.state.settings = settings
    api.state.jobs = store
    api.mount("/static", StaticFiles(directory=PACKAGE_DIR / "static"), name="static")

    @api.middleware("http")
    async def require_authentication(request: Request, call_next):
        if settings.auth_password is None:
            return await call_next(request)
        authorization = request.headers.get("authorization", "")
        scheme, _, credentials = authorization.partition(" ")
        username = ""
        password = ""
        if scheme.lower() == "basic" and credentials:
            try:
                decoded = base64.b64decode(credentials, validate=True).decode("utf-8")
                username, separator, password = decoded.partition(":")
                if not separator:
                    username = ""
            except (binascii.Error, UnicodeDecodeError):
                pass
        valid_username = secrets.compare_digest(username, settings.auth_username)
        valid_password = secrets.compare_digest(password, settings.auth_password)
        if not (valid_username and valid_password):
            return Response(
                status_code=401,
                content="Authentication required",
                media_type="text/plain",
                headers={
                    "WWW-Authenticate": 'Basic realm="InkLathe", charset="UTF-8"'
                },
            )
        return await call_next(request)

    @api.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(PACKAGE_DIR / "static" / "index.html")

    @api.get("/api/health")
    def health() -> dict:
        return {
            "status": "ok",
            "workers": 1,
            "storage_limit_bytes": settings.max_data_bytes,
            "max_image_pixels": settings.max_pixels,
            "capabilities": {
                "lucida": bool(settings.lucida_command),
                "ai_upscaler": bool(settings.ai_upscaler_command),
                "bitmap_textures": [
                    {
                        "id": key,
                        "label": str(profile["label"]),
                        "category": str(profile["category"]),
                        "maximum_percent": float(profile["maximum"]) * 100,
                        "kind": "scanned",
                    }
                    for key, profile in bitmap_textures.items()
                ],
                "halftones": [
                    {
                        "id": key,
                        "label": str(profile["label"]),
                        "category": str(profile["category"]),
                        "kind": "scanned",
                    }
                    for key, profile in halftones.items()
                ],
            },
            "setup": {
                "managed_by": "server",
                "ai_upscaler": {
                    "configured": bool(settings.ai_upscaler_command),
                    "nixos_options": [
                        "services.inklathe.aiUpscalerCommand",
                        "services.inklathe.realEsrganBinary",
                    ],
                },
                "lucida": {
                    "configured": bool(settings.lucida_command),
                    "nixos_options": ["services.inklathe.lucidaCommand"],
                },
            },
        }

    @api.post("/api/jobs", status_code=202)
    async def create_job(
        files: Annotated[list[UploadFile], File()],
        background: Annotated[str, Form()] = "threshold",
        upscale: Annotated[str, Form()] = "lanczos",
        scale: Annotated[int, Form()] = 4,
        grunge: Annotated[int, Form()] = 0,
        seed: Annotated[int, Form()] = 1,
        texture: Annotated[str, Form()] = "scan-g306",
        halftone: Annotated[str, Form()] = "none",
    ) -> dict:
        if not 1 <= len(files) <= 20:
            raise HTTPException(400, "Upload between 1 and 20 images")
        if background not in {"none", "threshold", "lucida"}:
            raise HTTPException(400, "Unsupported background mode")
        if upscale not in {"none", "lanczos", "ai"} or scale not in {1, 2, 4}:
            raise HTTPException(400, "Unsupported upscale mode")
        if not 0 <= grunge <= 100:
            raise HTTPException(400, "Wear must be between 0 and 100")
        if grunge > 0 and texture not in bitmap_textures:
            raise HTTPException(400, "Unsupported texture")
        if halftone != "none" and halftone not in halftones:
            raise HTTPException(400, "Unsupported print treatment")
        if background == "lucida" and not settings.lucida_command:
            raise HTTPException(409, "Lucida is not installed on this worker")
        if upscale == "ai" and not settings.ai_upscaler_command:
            raise HTTPException(409, "AI upscaler is not installed on this worker")

        uploads = []
        for upload in files:
            content = await upload.read(settings.max_upload_bytes + 1)
            if len(content) > settings.max_upload_bytes:
                raise HTTPException(413, f"{upload.filename} is too large")
            name = upload.filename or "image"
            width, height = _validate_image(content, name, settings.max_pixels)
            _validate_processing_size(
                name,
                width,
                height,
                upscale,
                scale,
                settings.max_pixels,
            )
            uploads.append((upload.filename or "image", content))

        options = ProcessOptions(
            background=background,
            upscale=upscale,
            scale=1 if upscale == "none" else scale,
            grunge=grunge,
            seed=seed,
            texture=texture,
            halftone=halftone,
        )
        return store.create(uploads, options).public()

    @api.get("/api/jobs/{job_id}")
    def get_job(job_id: str) -> dict:
        job = store.get(job_id)
        if not job:
            raise HTTPException(404, "Job not found")
        return job.public()

    @api.get("/api/jobs/{job_id}/files/{index}")
    def get_file(job_id: str, index: int) -> FileResponse:
        job = store.get(job_id)
        if not job or not 0 <= index < len(job.files):
            raise HTTPException(404, "File not found")
        item = job.files[index]
        if not item.output_path.exists():
            raise HTTPException(404, "Result is not ready")
        return FileResponse(
            item.output_path, media_type="image/png", filename=item.output_path.name
        )

    @api.get("/api/jobs/{job_id}/sources/{index}")
    def get_source(job_id: str, index: int) -> FileResponse:
        job = store.get(job_id)
        if not job or not 0 <= index < len(job.files):
            raise HTTPException(404, "Source image not found")
        item = job.files[index]
        if not item.input_path.exists():
            raise HTTPException(404, "Source image not found")
        media_type = guess_type(item.input_path.name)[0] or "application/octet-stream"
        return FileResponse(item.input_path, media_type=media_type, filename=item.name)

    @api.get("/api/jobs/{job_id}/previews/{index}")
    def get_preview(job_id: str, index: int) -> FileResponse:
        job = store.get(job_id)
        if not job or not 0 <= index < len(job.files):
            raise HTTPException(404, "Preview not found")
        item = job.files[index]
        if not item.preview_path.exists():
            raise HTTPException(404, "Preview is not ready")
        return FileResponse(item.preview_path, media_type="image/png")

    @api.delete("/api/jobs/{job_id}/files/{index}", status_code=204)
    def delete_file(job_id: str, index: int) -> Response:
        if not store.delete_result(job_id, index):
            raise HTTPException(404, "Result not found")
        return Response(status_code=204)

    @api.get("/api/jobs/{job_id}/archive")
    def get_archive(job_id: str) -> FileResponse:
        job = store.get(job_id)
        if not job or not job.archive_path:
            raise HTTPException(404, "Archive is not ready")
        return FileResponse(
            job.archive_path, media_type="application/zip", filename="inklathe-results.zip"
        )

    return api


def _megapixels(pixels: int) -> str:
    return f"{pixels / 1_000_000:.1f} MP"


def _validate_image(content: bytes, name: str, max_pixels: int) -> tuple[int, int]:
    from io import BytesIO

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", Image.DecompressionBombWarning)
            with Image.open(BytesIO(content)) as image:
                width, height = image.size
                pixels = width * height
                if pixels > max_pixels:
                    raise HTTPException(
                        413,
                        f"{name} is {width}×{height} ({_megapixels(pixels)}), above "
                        f"this server's {_megapixels(max_pixels)} image limit",
                    )
                image.verify()
    except HTTPException:
        raise
    except Image.DecompressionBombError as error:
        raise HTTPException(
            413,
            f"{name} exceeds this server's {_megapixels(max_pixels)} image limit",
        ) from error
    except (UnidentifiedImageError, OSError) as error:
        raise HTTPException(400, f"{name} is not a supported image") from error
    return width, height


def _validate_processing_size(
    name: str,
    width: int,
    height: int,
    upscale: str,
    scale: int,
    max_pixels: int,
) -> None:
    applied_scale = scale if upscale != "none" else 1
    output_width = width * applied_scale
    output_height = height * applied_scale
    output_pixels = output_width * output_height
    if output_pixels <= max_pixels:
        return
    raise HTTPException(
        413,
        f"{name} would become {output_width}×{output_height} "
        f"({_megapixels(output_pixels)}) at {applied_scale}×, above this server's "
        f"{_megapixels(max_pixels)} image limit. Choose a lower scale or no upscaling",
    )


app = create_app()
