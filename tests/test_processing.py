from pathlib import Path

from PIL import Image, ImageDraw

from inklathe.processing import (
    ProcessOptions,
    apply_halftone,
    apply_texture,
    process_builtin,
    remove_light_background,
)


def logo() -> Image.Image:
    image = Image.new("RGB", (64, 64), "white")
    ImageDraw.Draw(image).rectangle((16, 16, 47, 47), fill="black")
    return image


def test_background_becomes_transparent() -> None:
    result = remove_light_background(logo(), softness=4)
    assert result.getpixel((0, 0))[3] == 0
    assert result.getpixel((32, 32))[3] == 255


def test_bitmap_texture_is_reproducible_and_calibrated(tmp_path: Path) -> None:
    texture = tmp_path / "texture.jpg"
    scanned = Image.new("L", (300, 220), 245)
    draw = ImageDraw.Draw(scanned)
    for x in range(10, 290, 17):
        draw.line((x, 0, x - 35, 219), fill=20, width=2)
    scanned.save(texture)
    source = Image.new("RGBA", (256, 256), (0, 0, 0, 255))

    first = apply_texture(
        source, 60, "local-test", 42, texture_path=texture, maximum=0.12
    )
    repeated = apply_texture(
        source, 60, "local-test", 42, texture_path=texture, maximum=0.12
    )
    changed_seed = apply_texture(
        source, 60, "local-test", 43, texture_path=texture, maximum=0.12
    )
    subtle = apply_texture(
        source, 25, "local-test", 42, texture_path=texture, maximum=0.12
    )
    extreme = apply_texture(
        source, 100, "local-test", 42, texture_path=texture, maximum=0.12
    )

    assert first.tobytes() == repeated.tobytes()
    assert first.tobytes() != changed_seed.tobytes()
    assert set(first.getchannel("A").get_flattened_data()) <= {0, 255}
    pixels = source.width * source.height
    subtle_removed = subtle.getchannel("A").get_flattened_data().count(0) / pixels
    extreme_removed = extreme.getchannel("A").get_flattened_data().count(0) / pixels
    assert abs(subtle_removed - 0.12 * 0.25**1.55) < 0.002
    assert abs(extreme_removed - 0.12) < 0.002


def test_halftone_scan_becomes_binary_ink_mask(tmp_path: Path) -> None:
    texture = tmp_path / "halftone.jpg"
    scan = Image.new("L", (300, 220), 0)
    draw = ImageDraw.Draw(scan)
    for x in range(12, 290, 18):
        draw.ellipse((x, 40, x + 7, 180), fill=255)
    scan.save(texture)
    source = Image.new("RGBA", (256, 256), (0, 0, 0, 255))

    first = apply_halftone(
        source, "local-halftone", 42, texture_path=texture, invert=False
    )
    repeated = apply_halftone(
        source, "local-halftone", 42, texture_path=texture, invert=False
    )

    assert first.tobytes() == repeated.tobytes()
    assert set(first.getchannel("A").get_flattened_data()) == {0, 255}


def test_pipeline_upscales_and_writes_png(tmp_path: Path) -> None:
    source = tmp_path / "source.jpg"
    destination = tmp_path / "result.png"
    logo().save(source)
    process_builtin(source, destination, ProcessOptions(scale=4, grunge=0, seed=7))
    with Image.open(destination) as result:
        assert result.size == (256, 256)
        assert result.mode == "RGBA"
