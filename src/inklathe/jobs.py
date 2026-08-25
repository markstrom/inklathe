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
from .processing import ProcessOptions, apply_grunge, process_builtin, upscale_lanczos


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
            },
            "files": [
                {
                    "name": item.output_path.name,
                    "source_name": item.name,
                    "download": f"/api/jobs/{self.id}/files/{index}",
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
        job_id = uuid4().hex
        root = self.settings.data_dir / "jobs" / job_id
        input_dir = root / "input"
        output_dir = root / "output"
        input_dir.mkdir(parents=True)
        output_dir.mkdir(parents=True)
        files = []
        for index, (original_name, content) in enumerate(uploads):
            safe_name = _safe_name(original_name, index)
            input_path = input_dir / safe_name
            input_path.write_bytes(content)
            output_name = f"{Path(safe_name).stem}-inklathe.png"
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
        job = Job(id=job_id, options=options, files=files)
        with self.lock:
            self.jobs[job_id] = job
        self.executor.submit(self._process, job, options)
        return job

    def get(self, job_id: str) -> Job | None:
        with self.lock:
            return self.jobs.get(job_id)

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
        if options.background == "lucida":
            run_lucida(self.settings.lucida_command, item.input_path, work)
        else:
            builtin_options = ProcessOptions(
                background=options.background,
                upscale="none",
                scale=1,
                grunge=0,
                seed=seed,
            )
            process_builtin(item.input_path, work, builtin_options)

        if options.upscale == "ai":
            upscaled = work.with_name(f"{work.stem}-upscaled.png")
            run_ai_upscaler(self.settings.ai_upscaler_command, work, upscaled, options.scale)
            shutil.move(upscaled, work)
        elif options.upscale == "lanczos":
            with Image.open(work) as opened:
                image = upscale_lanczos(opened, options.scale)
                image.load()
            image.save(work, "PNG")

        with Image.open(work) as opened:
            final = apply_grunge(opened, options.grunge, seed)
            final.load()
        final.save(item.output_path, "PNG", optimize=True)
        item.output_width, item.output_height = final.size
        item.output_bytes = item.output_path.stat().st_size
        work.unlink(missing_ok=True)


def _safe_name(original: str, index: int) -> str:
    suffix = Path(original).suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
        suffix = ".png"
    stem = "".join(
        character for character in Path(original).stem if character.isalnum() or character in "-_"
    )
    return f"{index + 1:02d}-{stem[:80] or 'image'}{suffix}"
