from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, UnidentifiedImageError

from .config import Settings
from .jobs import JobStore
from .processing import ProcessOptions

PACKAGE_DIR = Path(__file__).parent


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    Image.MAX_IMAGE_PIXELS = settings.max_pixels
    store = JobStore(settings)
    api = FastAPI(title="InkLathe", version="0.1.0")
    api.state.settings = settings
    api.state.jobs = store
    api.mount("/static", StaticFiles(directory=PACKAGE_DIR / "static"), name="static")

    @api.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(PACKAGE_DIR / "static" / "index.html")

    @api.get("/api/health")
    def health() -> dict:
        return {
            "status": "ok",
            "workers": 1,
            "capabilities": {
                "lucida": bool(settings.lucida_command),
                "ai_upscaler": bool(settings.ai_upscaler_command),
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
        texture: Annotated[str, Form()] = "paper-fibers",
    ) -> dict:
        if not 1 <= len(files) <= 20:
            raise HTTPException(400, "Upload between 1 and 20 images")
        if background not in {"none", "threshold", "lucida"}:
            raise HTTPException(400, "Unsupported background mode")
        if upscale not in {"none", "lanczos", "ai"} or scale not in {1, 2, 4}:
            raise HTTPException(400, "Unsupported upscale mode")
        if not 0 <= grunge <= 100:
            raise HTTPException(400, "Wear must be between 0 and 100")
        if texture not in {"paper-fibers", "dry-ink", "scratches"}:
            raise HTTPException(400, "Unsupported texture")
        if background == "lucida" and not settings.lucida_command:
            raise HTTPException(409, "Lucida is not installed on this worker")
        if upscale == "ai" and not settings.ai_upscaler_command:
            raise HTTPException(409, "AI upscaler is not installed on this worker")

        uploads = []
        for upload in files:
            content = await upload.read(settings.max_upload_bytes + 1)
            if len(content) > settings.max_upload_bytes:
                raise HTTPException(413, f"{upload.filename} is too large")
            _validate_image(content, upload.filename or "image")
            uploads.append((upload.filename or "image", content))

        options = ProcessOptions(background, upscale, scale, grunge, seed, texture)
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


def _validate_image(content: bytes, name: str) -> None:
    from io import BytesIO

    try:
        with Image.open(BytesIO(content)) as image:
            image.verify()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
        raise HTTPException(400, f"{name} is not a supported image") from error


app = create_app()
