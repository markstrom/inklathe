import os
from dataclasses import dataclass
from pathlib import Path


def _auth_password_from_env() -> str | None:
    password_file = os.getenv("INKLATHE_AUTH_PASSWORD_FILE")
    if not password_file:
        credentials_dir = os.getenv("CREDENTIALS_DIRECTORY")
        if credentials_dir:
            candidate = Path(credentials_dir) / "inklathe-auth-password"
            if candidate.is_file():
                password_file = str(candidate)
    if password_file:
        password = Path(password_file).read_text(encoding="utf-8").rstrip("\r\n")
        if not password:
            raise ValueError("InkLathe authentication password file is empty")
        return password
    return os.getenv("INKLATHE_AUTH_PASSWORD") or None


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    texture_dir: Path | None = None
    max_upload_bytes: int = 25 * 1024 * 1024
    max_pixels: int = 40_000_000
    max_data_bytes: int = 20 * 1024 * 1024 * 1024
    ai_upscaler_command: str | None = None
    lucida_command: str | None = None
    auth_username: str = "inklathe"
    auth_password: str | None = None

    @classmethod
    def from_env(cls) -> "Settings":
        data_dir = Path(os.getenv("INKLATHE_DATA_DIR", "data")).resolve()
        texture_dir = os.getenv("INKLATHE_TEXTURE_DIR")
        return cls(
            data_dir=data_dir,
            texture_dir=Path(texture_dir).resolve() if texture_dir else data_dir / "textures",
            max_upload_bytes=int(os.getenv("INKLATHE_MAX_UPLOAD_BYTES", "26214400")),
            max_pixels=int(os.getenv("INKLATHE_MAX_PIXELS", "40000000")),
            max_data_bytes=int(float(os.getenv("INKLATHE_MAX_DATA_GB", "20")) * 1024**3),
            ai_upscaler_command=os.getenv("INKLATHE_AI_UPSCALER_COMMAND") or None,
            lucida_command=os.getenv("INKLATHE_LUCIDA_COMMAND") or None,
            auth_username=os.getenv("INKLATHE_AUTH_USERNAME", "inklathe"),
            auth_password=_auth_password_from_env(),
        )
