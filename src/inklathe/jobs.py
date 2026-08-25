from __future__ import annotations

import shutil
import zipfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from time import time
from uuid import uuid4

from PIL import Image

from .adapters import run_ai_upscaler, run_lucida
from .config import Settings
from .processing import ProcessOptions, apply_texture, process_builtin, upscale_lanczos

BASE62_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
TIMESTAMP_EPOCH = 1767225600  # 2026-01-01 00:00:00 UTC
TIMESTAMP_WIDTH = 5


@dataclass
class JobFile:
    name: str
    input_path: Path
    output_path: Path
    input_width: int
    input_height: int
    input_bytes: int
    output_width: int | None = None
    output_height: int | None = None
    output_bytes: int | None = None


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
            },
            "files": [
                {
                    "index": index,
                    "name": item.output_path.name,
                    "source_name": item.name,
                    "source": f"/api/jobs/{self.id}/sources/{index}",
                    "download": f"/api/jobs/{self.id}/files/{index}",
                    "delete": f"/api/jobs/{self.id}/files/{index}",
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
                if item.output_path.exists()
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

    def create(self, uploads: list[tuple[str, bytes]], options: ProcessOptions) -> Job:
        created_at = time()
        timestamp = _base62_timestamp(created_at)
        job_id = uuid4().hex
        root = self.settings.data_dir / "jobs" / job_id
        input_dir = root / "input"
        output_dir = root / "output"
        input_dir.mkdir(parents=True)
        output_dir.mkdir(parents=True)
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
                    input_width,
                    input_height,
                    len(content),
                )
            )
        job = Job(id=job_id, options=options, created_at=created_at, files=files)
        with self.lock:
            self.jobs[job_id] = job
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
            if job.archive_path:
                job.archive_path.unlink(missing_ok=True)
                job.archive_path = None
            return True

    def _process(self, job: Job, options: ProcessOptions) -> None:
        job.state = "processing"
        try:
            for index, item in enumerate(job.files):
                self._process_file(item, options, options.seed + index)
                job.completed += 1
            archive = item.output_path.parent.parent / "inklathe-results.zip"
            with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
                for item in job.files:
                    bundle.write(item.output_path, item.output_path.name)
            job.archive_path = archive
            job.state = "complete"
        except Exception as error:  # noqa: BLE001 - worker errors must be surfaced to the UI
            job.error = str(error)
            job.state = "failed"

    def _process_file(self, item: JobFile, options: ProcessOptions, seed: int) -> None:
        work = item.output_path.parent / f".{item.output_path.stem}-work.png"
        initial_options = ProcessOptions(
            background="none",
            upscale="none",
            scale=1,
            grunge=0,
            seed=seed,
        )
        process_builtin(item.input_path, work, initial_options)

        if options.upscale == "ai":
            upscaled = work.with_name(f"{work.stem}-upscaled.png")
            run_ai_upscaler(self.settings.ai_upscaler_command, work, upscaled, options.scale)
            shutil.move(upscaled, work)
        elif options.upscale == "lanczos":
            with Image.open(work) as opened:
                image = upscale_lanczos(opened, options.scale)
                image.load()
            image.save(work, "PNG")

        if options.background == "lucida":
            background_removed = work.with_name(f"{work.stem}-background.png")
            run_lucida(self.settings.lucida_command, work, background_removed)
            shutil.move(background_removed, work)
        elif options.background == "threshold":
            background_options = ProcessOptions(
                background="threshold",
                upscale="none",
                scale=1,
                grunge=0,
                seed=seed,
            )
            background_removed = work.with_name(f"{work.stem}-background.png")
            process_builtin(work, background_removed, background_options)
            shutil.move(background_removed, work)

        with Image.open(work) as opened:
            final = apply_texture(opened, options.grunge, options.texture, seed)
            final.load()
        final.save(item.output_path, "PNG", optimize=True)
        item.output_width, item.output_height = final.size
        item.output_bytes = item.output_path.stat().st_size
        work.unlink(missing_ok=True)


def _safe_name(original: str, index: int) -> str:
    suffix = Path(original).suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
        suffix = ".png"
    return f"{index + 1:02d}-{_safe_stem(original)}{suffix}"


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
