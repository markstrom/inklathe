import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    max_upload_bytes: int = 25 * 1024 * 1024
    max_pixels: int = 40_000_000
    ai_upscaler_command: str | None = None
    lucida_command: str | None = None

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            data_dir=Path(os.getenv("INKLATHE_DATA_DIR", "data")).resolve(),
            max_upload_bytes=int(os.getenv("INKLATHE_MAX_UPLOAD_BYTES", "26214400")),
            max_pixels=int(os.getenv("INKLATHE_MAX_PIXELS", "40000000")),
            ai_upscaler_command=os.getenv("INKLATHE_AI_UPSCALER_COMMAND") or None,
            lucida_command=os.getenv("INKLATHE_LUCIDA_COMMAND") or None,
        )
