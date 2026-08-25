from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image, ImageOps


def _model_input(image: Image.Image) -> tuple[Image.Image, Image.Image]:
    rgba = ImageOps.exif_transpose(image).convert("RGBA")
    alpha = rgba.getchannel("A")
    rgb = Image.new("RGB", rgba.size, "white")
    rgb.paste(rgba.convert("RGB"), mask=alpha)
    return rgb, alpha


def _restore_alpha(image: Image.Image, alpha: Image.Image, size: tuple[int, int]) -> Image.Image:
    if image.size != size:
        raise RuntimeError(
            f"Real-ESRGAN returned {image.width}x{image.height}; expected {size[0]}x{size[1]}"
        )
    result = image.convert("RGBA")
    result.putalpha(alpha.resize(size, Image.Resampling.LANCZOS))
    return result


def upscale(source: Path, destination: Path, scale: int) -> None:
    if scale not in {2, 4}:
        raise ValueError(f"InkLathe supports Real-ESRGAN scale 2 or 4, received: {scale}")

    binary = os.getenv("INKLATHE_REALESRGAN_BIN")
    if not binary:
        raise RuntimeError("INKLATHE_REALESRGAN_BIN is not configured")
    model = os.getenv("INKLATHE_REALESRGAN_MODEL", "realesrgan-x4plus")

    with Image.open(source) as opened:
        model_input, alpha = _model_input(opened)
        model_input.load()
        alpha.load()

    destination.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="inklathe-realesrgan-") as temporary:
        temporary_dir = Path(temporary)
        prepared_source = temporary_dir / "input.png"
        model_output = temporary_dir / "output.png"
        model_input.save(prepared_source, "PNG")

        command = [
            binary,
            "-i",
            str(prepared_source),
            "-o",
            str(model_output),
            "-s",
            str(scale),
            "-n",
            model,
            "-f",
            "png",
        ]
        model_dir = os.getenv("INKLATHE_REALESRGAN_MODEL_DIR")
        if model_dir:
            command.extend(["-m", model_dir])

        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()
            raise RuntimeError(
                f"Real-ESRGAN exited with {completed.returncode}: {detail[-2000:]}"
            )
        if not model_output.is_file():
            raise RuntimeError("Real-ESRGAN completed without creating an output image")

        with Image.open(model_output) as opened:
            result = _restore_alpha(
                opened,
                alpha,
                (model_input.width * scale, model_input.height * scale),
            )
            result.load()
        result.save(destination, "PNG", optimize=True)


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("Usage: inklathe-realesrgan-adapter INPUT OUTPUT SCALE")
    try:
        upscale(Path(sys.argv[1]), Path(sys.argv[2]), int(sys.argv[3]))
    except (OSError, RuntimeError, ValueError) as error:
        raise SystemExit(str(error)) from error


if __name__ == "__main__":
    main()
