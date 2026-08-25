from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SCALE = 3
WHITE = "#ffffff"


def render_wordmark(source: Path, destination: Path) -> None:
    font_paths = (
        Path("/System/Library/Fonts/Menlo.ttc"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),
        Path("/run/current-system/sw/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),
    )
    font_path = next((path for path in font_paths if path.exists()), None)
    if font_path is None:
        raise RuntimeError("A supported monospace font is required to render the wordmark")

    art = source.read_text(encoding="utf-8").rstrip()
    font = ImageFont.truetype(str(font_path), 24 * SCALE)
    probe = Image.new("RGB", (1, 1))
    probe_draw = ImageDraw.Draw(probe)
    bounds = probe_draw.multiline_textbbox((0, 0), art, font=font, spacing=0)
    padding = 24 * SCALE
    width = bounds[2] - bounds[0] + padding * 2
    height = bounds[3] - bounds[1] + padding * 2
    canvas = Image.new("RGB", (width, height), WHITE)
    draw = ImageDraw.Draw(canvas)
    draw.multiline_text(
        (padding - bounds[0], padding - bounds[1]),
        art,
        fill="#111111",
        font=font,
        spacing=0,
    )
    canvas.resize((width // SCALE, height // SCALE), Image.Resampling.LANCZOS).save(
        destination,
        "PNG",
        optimize=True,
    )


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    render_wordmark(
        root / "assets" / "brand" / "github-wordmark.txt",
        root / "assets" / "brand" / "github-wordmark-white.png",
    )
