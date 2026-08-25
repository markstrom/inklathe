from pathlib import Path

from PIL import Image, ImageDraw

from inklathe.processing import (
    TEXTURE_PROFILES,
    ProcessOptions,
    apply_grunge,
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


def test_texture_profiles_are_distinct() -> None:
    source = remove_light_background(logo())
    results = {
        apply_texture(source, 60, texture, 42).tobytes()
        for texture in (
            "worn-ink",
            "cracked-plastisol",
            "dry-screen",
            "scuffed-print",
            "vintage-mix",
        )
    }
    assert len(results) == 5


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

    assert first.tobytes() == repeated.tobytes()
    assert first.tobytes() != changed_seed.tobytes()
    assert set(first.getchannel("A").get_flattened_data()) <= {0, 255}


def test_wear_is_calibrated_and_uses_binary_knockouts() -> None:
    source = Image.new("RGBA", (384, 384), (0, 0, 0, 255))
    pixels = source.width * source.height

    for texture, maximum in TEXTURE_PROFILES.items():
        light = apply_texture(source, 4, texture, 42).getchannel("A")
        worn = apply_texture(source, 60, texture, 42).getchannel("A")
        light_removed = light.get_flattened_data().count(0) / pixels
        worn_removed = worn.get_flattened_data().count(0) / pixels
        expected_worn = maximum * 0.6**1.55

        assert light_removed < 0.002
        assert abs(worn_removed - expected_worn) < 0.002
        assert set(worn.get_flattened_data()) <= {0, 255}


def test_pipeline_upscales_and_writes_png(tmp_path: Path) -> None:
    source = tmp_path / "source.jpg"
    destination = tmp_path / "result.png"
    logo().save(source)
    process_builtin(source, destination, ProcessOptions(scale=4, grunge=20, seed=7))
    with Image.open(destination) as result:
        assert result.size == (256, 256)
        assert result.mode == "RGBA"
