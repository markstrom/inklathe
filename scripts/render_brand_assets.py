from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SIZE = 1024
SCALE = 3
INK = "#151515"
FIELD = "#1b1b1a"
PAPER = "#ece8dd"
ACID = "#d6ff3f"
WHITE = "#ffffff"


def scaled(values):
    return tuple(round(value * SCALE) for value in values)


def render_avatar(destination: Path) -> None:
    canvas = Image.new("RGB", (SIZE * SCALE, SIZE * SCALE), INK)
    draw = ImageDraw.Draw(canvas)
    draw.ellipse(scaled((80, 80, 944, 944)), fill=FIELD, outline="#302f2b", width=10 * SCALE)

    mark = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    shape = ImageDraw.Draw(mark)
    shape.ellipse(scaled((122, 122, 902, 902)), outline=PAPER, width=22 * SCALE)

    # Solid I.
    shape.rectangle(scaled((188, 245, 480, 329)), fill=PAPER)
    shape.rectangle(scaled((276, 329, 392, 695)), fill=PAPER)
    shape.rectangle(scaled((188, 695, 480, 779)), fill=PAPER)

    # Outlined L with square stroke ends.
    shape.rectangle(scaled((508, 218, 612, 777)), fill=PAPER)
    shape.rectangle(scaled((508, 673, 872, 777)), fill=PAPER)
    shape.rectangle(scaled((533, 243, 587, 752)), fill=FIELD)
    shape.rectangle(scaled((533, 698, 845, 752)), fill=FIELD)

    # Reproducible worn areas.
    holes = [
        (211, 312, 313, 344),
        (329, 456, 427, 497),
        (197, 643, 319, 689),
        (350, 716, 430, 750),
        (555, 341, 635, 380),
        (550, 557, 621, 590),
        (660, 677, 761, 715),
        (736, 720, 794, 747),
    ]
    for box in holes:
        shape.ellipse(scaled(box), fill=(0, 0, 0, 0))
    for box in [
        (265, 402, 295, 418),
        (378, 581, 422, 601),
        (562, 466, 594, 480),
        (702, 499, 748, 517),
        (805, 594, 829, 606),
    ]:
        shape.ellipse(scaled(box), fill=(0, 0, 0, 0))

    canvas.paste(mark, (0, 0), mark)
    draw = ImageDraw.Draw(canvas)
    draw.ellipse(scaled((758, 247, 820, 309)), fill=ACID)
    draw.rectangle(scaled((738, 272, 758, 284)), fill=ACID)
    draw.rectangle(scaled((820, 272, 840, 284)), fill=ACID)
    draw.rectangle(scaled((452, 846, 572, 856)), fill=ACID)
    draw.rectangle(scaled((586, 846, 614, 856)), fill=ACID)
    draw.rectangle(scaled((410, 846, 438, 856)), fill=ACID)

    canvas.resize((SIZE, SIZE), Image.Resampling.LANCZOS).save(destination, "PNG", optimize=True)


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
    render_avatar(root / "assets" / "brand" / "github-avatar.png")
    render_wordmark(
        root / "assets" / "brand" / "github-wordmark.txt",
        root / "assets" / "brand" / "github-wordmark-white.png",
    )
