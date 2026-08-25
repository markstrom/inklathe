from __future__ import annotations

import shutil
import zipfile
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from threading import Lock
from time import time
from uuid import uuid4

from PIL import Image

from .adapters import run_ai_upscaler, run_lucida
from .config import Settings
from .processing import (
    ProcessOptions,
    apply_halftone,
    apply_texture,
    available_bitmap_textures,
    available_halftones,
    process_builtin,
    upscale_lanczos,
)

BASE62_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
TIMESTAMP_EPOCH = 1767225600  # 2026-01-01 00:00:00 UTC
TIMESTAMP_WIDTH = 5
PREVIEW_MAX_SIZE = 640


@dataclass
class JobFile:
    name: str
    input_path: Path
    output_path: Path
    preview_path: Path
    input_width: int
    input_height: int
    input_bytes: int
    content_hash: str
    output_width: int | None = None
    output_height: int | None = None
    output_bytes: int | None = None
    cache_hits: list[str] = field(default_factory=list)


@dataclass
class Job:
    id: str
    options: ProcessOptions
    state: str = "queued"
    error: str | None = None
    completed: int = 0
    created_at: float = field(default_factory=time)
    files: list[JobFile] = field(default_factory=list)
    archive_path: Path | None = None

    def public(self) -> dict:
        return {
            "id": self.id,
            "state": self.state,
            "error": self.error,
            "completed": self.completed,
            "total": len(self.files),
            "created_at": self.created_at,
            "settings": {
                "background": self.options.background,
                "upscale": self.options.upscale,
                "scale": self.options.scale,
                "grunge": self.options.grunge,
                "seed": self.options.seed,
                "texture": self.options.texture,
                "halftone": self.options.halftone,
            },
            "files": [
                {
                    "index": index,
                    "name": item.output_path.name,
                    "source_name": item.name,
                    "source": f"/api/jobs/{self.id}/sources/{index}",
                    "preview": f"/api/jobs/{self.id}/previews/{index}",
                    "download": f"/api/jobs/{self.id}/files/{index}",
                    "delete": f"/api/jobs/{self.id}/files/{index}",
                    "cache_hits": item.cache_hits,
                    "input": {
                        "width": item.input_width,
                        "height": item.input_height,
                        "bytes": item.input_bytes,
                    },
                    "output": {
                        "width": item.output_width,
                        "height": item.output_height,
                        "bytes": item.output_bytes,
                    },
                }
                for index, item in enumerate(self.files)
                if index < self.completed and item.output_path.exists()
            ],
            "archive": f"/api/jobs/{self.id}/archive" if self.archive_path else None,
        }


class JobStore:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.settings.data_dir.mkdir(parents=True, exist_ok=True)
        self.jobs: dict[str, Job] = {}
        self.lock = Lock()
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="inklathe-worker")
        self.bitmap_textures = available_bitmap_textures(settings.texture_dir)
        self.halftones = available_halftones(settings.texture_dir)

    def create(self, uploads: list[tuple[str, bytes]], options: ProcessOptions) -> Job:
        created_at = time()
        timestamp = _base62_timestamp(created_at)
        job_id = uuid4().hex
        root = self.settings.data_dir / "jobs" / job_id
        input_dir = root / "input"
        output_dir = root / "output"
        preview_dir = root / "preview"
        input_dir.mkdir(parents=True)
        output_dir.mkdir(parents=True)
        preview_dir.mkdir(parents=True)
        files = []
        output_names: set[str] = set()
        for index, (original_name, content) in enumerate(uploads):
            safe_name = _safe_name(original_name, index)
            input_path = input_dir / safe_name
            input_path.write_bytes(content)
            output_name = f"{_safe_stem(original_name)}-{timestamp}.png"
            if output_name in output_names:
                output_name = f"{_safe_stem(original_name)}-{index + 1}-{timestamp}.png"
            output_names.add(output_name)
            with Image.open(input_path) as image:
                input_width, input_height = image.size
            files.append(
                JobFile(
                    safe_name,
                    input_path,
                    output_dir / output_name,
                    preview_dir / output_name,
                    input_width,
                    input_height,
                    len(content),
                    sha256(content).hexdigest(),
                )
            )
        job = Job(id=job_id, options=options, created_at=created_at, files=files)
        with self.lock:
            self.jobs[job_id] = job
        try:
            self._enforce_storage_limit(job.id)
        except OSError:
            pass
        self.executor.submit(self._process, job, options)
        return job

    def get(self, job_id: str) -> Job | None:
        with self.lock:
            return self.jobs.get(job_id)

    def delete_result(self, job_id: str, index: int) -> bool:
        with self.lock:
            job = self.jobs.get(job_id)
            if not job or job.state != "complete" or not 0 <= index < len(job.files):
                return False
            item = job.files[index]
            if not item.output_path.exists():
                return False
            item.output_path.unlink()
            item.preview_path.unlink(missing_ok=True)
            if job.archive_path:
                job.archive_path.unlink(missing_ok=True)
                job.archive_path = None
            return True

    def _process(self, job: Job, options: ProcessOptions) -> None:
        job.state = "processing"
        try:
            for item in job.files:
                self._process_file(item, options, options.seed)
                job.completed += 1
            archive = item.output_path.parent.parent / "inklathe-results.zip"
            with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
                for item in job.files:
                    bundle.write(item.output_path, item.output_path.name)
            job.archive_path = archive
            job.state = "complete"
            try:
                self._enforce_storage_limit(job.id)
            except OSError:
                pass
        except Exception as error:  # noqa: BLE001 - worker errors must be surfaced to the UI
            job.error = str(error)
            job.state = "failed"

    def _process_file(self, item: JobFile, options: ProcessOptions, seed: int) -> None:
        item.cache_hits = []
        initial_options = ProcessOptions(
            background="none",
            upscale="none",
            scale=1,
            grunge=0,
            seed=seed,
        )
        normalized_key = _cache_key("normalize-v1", item.content_hash)
        normalized = self._cached_stage(
            item,
            "normalized",
            normalized_key,
            lambda destination: process_builtin(item.input_path, destination, initial_options),
        )

        prepared = normalized
        prepared_key = normalized_key

        if options.upscale == "ai":
            prepared_key = _cache_key(
                "upscale-ai-v1",
                normalized_key,
                options.scale,
                self.settings.ai_upscaler_command or "",
            )
            prepared = self._cached_stage(
                item,
                "upscale",
                prepared_key,
                lambda destination: run_ai_upscaler(
                    self.settings.ai_upscaler_command, normalized, destination, options.scale
                ),
            )
        elif options.upscale == "lanczos":
            prepared_key = _cache_key("upscale-lanczos-v1", normalized_key, options.scale)

            def build_lanczos(destination: Path) -> None:
                with Image.open(normalized) as opened:
                    image = upscale_lanczos(opened, options.scale)
                    image.load()
                image.save(destination, "PNG")

            prepared = self._cached_stage(
                item, "upscale", prepared_key, build_lanczos
            )

        if options.background == "lucida":
            background_key = _cache_key(
                "background-lucida-v1",
                prepared_key,
                self.settings.lucida_command or "",
            )
            source = prepared
            prepared = self._cached_stage(
                item,
                "background",
                background_key,
                lambda destination: run_lucida(
                    self.settings.lucida_command, source, destination
                ),
            )
            prepared_key = background_key
        elif options.background == "threshold":
            background_options = ProcessOptions(
                background="threshold",
                upscale="none",
                scale=1,
                grunge=0,
                seed=seed,
            )
            background_key = _cache_key("background-threshold-v1", prepared_key)
            source = prepared
            prepared = self._cached_stage(
                item,
                "background",
                background_key,
                lambda destination: process_builtin(source, destination, background_options),
            )
            prepared_key = background_key

        if options.halftone != "none":
            profile = self.halftones.get(options.halftone)
            if profile is None:
                raise ValueError(f"Halftone file is not installed: {options.halftone}")
            path = Path(str(profile["path"]))
            stat = path.stat()
            halftone_key = _cache_key(
                "halftone-v1",
                prepared_key,
                options.halftone,
                seed,
                stat.st_size,
                stat.st_mtime_ns,
            )
            source = prepared

            def build_halftone(destination: Path) -> None:
                with Image.open(source) as opened:
                    image = apply_halftone(
                        opened,
                        options.halftone,
                        seed,
                        texture_path=path,
                        invert=bool(profile["invert"]),
                    )
                    image.load()
                image.save(destination, "PNG", optimize=True)

            prepared = self._cached_stage(
                item, "print-treatment", halftone_key, build_halftone
            )
            prepared_key = halftone_key

        with Image.open(prepared) as opened:
            bitmap = self.bitmap_textures.get(options.texture)
            final = apply_texture(
                opened,
                options.grunge,
                options.texture,
                seed,
                texture_path=Path(str(bitmap["path"])) if bitmap else None,
                maximum=float(bitmap["maximum"]) if bitmap else None,
            )
            final.load()
        preview = final.copy()
        preview.thumbnail((PREVIEW_MAX_SIZE, PREVIEW_MAX_SIZE), Image.Resampling.LANCZOS)
        preview.save(item.preview_path, "PNG", optimize=True)
        final.save(item.output_path, "PNG", optimize=True)
        item.output_width, item.output_height = final.size
        item.output_bytes = item.output_path.stat().st_size

    def _cached_stage(
        self,
        item: JobFile,
        stage: str,
        key: str,
        build: Callable[[Path], None],
    ) -> Path:
        destination = self.settings.data_dir / "cache" / stage / f"{key}.png"
        if destination.exists():
            item.cache_hits.append(stage)
            destination.touch()
            return destination

        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(f".{destination.stem}-{uuid4().hex}.png")
        try:
            build(temporary)
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)
        return destination

    def _enforce_storage_limit(self, current_job_id: str) -> None:
        limit = self.settings.max_data_bytes
        if limit <= 0:
            return
        total = _directory_size(self.settings.data_dir)
        if total <= limit:
            return
        target = int(limit * 0.9)

        cache_dir = self.settings.data_dir / "cache"
        cache_files = sorted(
            (path for path in cache_dir.glob("*/*.png") if path.is_file()),
            key=lambda path: path.stat().st_mtime_ns,
        )
        for path in cache_files:
            if total <= target:
                break
            size = path.stat().st_size
            path.unlink(missing_ok=True)
            total -= size

        with self.lock:
            protected_jobs = {
                job_id
                for job_id, job in self.jobs.items()
                if job.state in {"queued", "processing"}
            }
        protected_jobs.add(current_job_id)
        jobs_dir = self.settings.data_dir / "jobs"
        job_directories = (
            sorted(
                (
                    path
                    for path in jobs_dir.iterdir()
                    if path.is_dir() and path.name not in protected_jobs
                ),
                key=lambda path: path.stat().st_mtime_ns,
            )
            if jobs_dir.exists()
            else []
        )
        for path in job_directories:
            if total <= target:
                break
            size = _directory_size(path)
            shutil.rmtree(path)
            total -= size
            with self.lock:
                self.jobs.pop(path.name, None)


def _safe_name(original: str, index: int) -> str:
    suffix = Path(original).suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
        suffix = ".png"
    return f"{index + 1:02d}-{_safe_stem(original)}{suffix}"


def _cache_key(*parts: object) -> str:
    digest = sha256()
    for part in parts:
        digest.update(str(part).encode())
        digest.update(b"\0")
    return digest.hexdigest()


def _directory_size(directory: Path) -> int:
    if not directory.exists():
        return 0
    return sum(path.stat().st_size for path in directory.rglob("*") if path.is_file())


def _safe_stem(original: str) -> str:
    stem = "".join(
        character for character in Path(original).stem if character.isalnum() or character in "-_"
    )
    return stem[:80] or "image"


def _base62_timestamp(timestamp: float) -> str:
    value = int(timestamp) - TIMESTAMP_EPOCH
    limit = len(BASE62_ALPHABET) ** TIMESTAMP_WIDTH
    if not 0 <= value < limit:
        raise ValueError("Timestamp is outside the five-character InkLathe range")

    encoded = ""
    for _ in range(TIMESTAMP_WIDTH):
        value, remainder = divmod(value, len(BASE62_ALPHABET))
        encoded = BASE62_ALPHABET[remainder] + encoded
    return encoded
