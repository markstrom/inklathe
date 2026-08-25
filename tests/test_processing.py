from pathlib import Path

from PIL import Image, ImageDraw

from inklathe.processing import (
    ProcessOptions,
    apply_grunge,
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


def test_grunge_is_reproducible() -> None:
    source = remove_light_background(logo())
    assert apply_grunge(source, 60, 42).tobytes() == apply_grunge(source, 60, 42).tobytes()
    assert apply_grunge(source, 60, 42).tobytes() != apply_grunge(source, 60, 43).tobytes()


def test_low_grunge_is_lighter_than_high_grunge() -> None:
    source = remove_light_background(logo())
    light = apply_grunge(source, 4, 42).getchannel("A")
    heavy = apply_grunge(source, 70, 42).getchannel("A")
    source_alpha = sum(source.getchannel("A").get_flattened_data())
    light_alpha = sum(light.get_flattened_data())
    heavy_alpha = sum(heavy.get_flattened_data())
    assert light_alpha > heavy_alpha
    assert (source_alpha - light_alpha) / source_alpha < 0.02


def test_pipeline_upscales_and_writes_png(tmp_path: Path) -> None:
    source = tmp_path / "source.jpg"
    destination = tmp_path / "result.png"
    logo().save(source)
    process_builtin(source, destination, ProcessOptions(scale=4, grunge=20, seed=7))
    with Image.open(destination) as result:
        assert result.size == (256, 256)
        assert result.mode == "RGBA"
