from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageChops, ImageOps

TEXTURE_DIR = Path(__file__).parent / "assets" / "textures"
TEXTURE_PATHS = {
    "paper-fibers": TEXTURE_DIR / "paper-fibers.png",
    "dry-ink": TEXTURE_DIR / "dry-ink.png",
    "scratches": TEXTURE_DIR / "scratches.png",
    "vintage-tee": TEXTURE_DIR / "vintage-tee.png",
}


@dataclass(frozen=True)
class ProcessOptions:
    background: str = "threshold"
    upscale: str = "lanczos"
    scale: int = 4
    grunge: int = 0
    seed: int = 1
    texture: str = "paper-fibers"


def otsu_threshold(image: Image.Image) -> int:
    histogram = ImageOps.grayscale(image).histogram()
    total = sum(histogram)
    weighted_total = sum(index * count for index, count in enumerate(histogram))
    background_count = 0
    background_sum = 0
    best_variance = -1.0
    best_threshold = 127

    for threshold, count in enumerate(histogram):
        background_count += count
        if background_count == 0:
            continue
        foreground_count = total - background_count
        if foreground_count == 0:
            break
        background_sum += threshold * count
        background_mean = background_sum / background_count
        foreground_mean = (weighted_total - background_sum) / foreground_count
        variance = background_count * foreground_count * (background_mean - foreground_mean) ** 2
        if variance > best_variance:
            best_variance = variance
            best_threshold = threshold
    return best_threshold


def remove_light_background(image: Image.Image, softness: int = 18) -> Image.Image:
    """Turn a light background transparent while preserving dark logo strokes."""
    rgba = image.convert("RGBA")
    luminance = ImageOps.grayscale(rgba)
    threshold = otsu_threshold(rgba)
    low = max(0, threshold - softness)
    high = min(255, threshold + softness)
    span = max(1, high - low)

    alpha = luminance.point(
        lambda value: (
            255 if value <= low else 0 if value >= high else round(255 * (high - value) / span)
        )
    )
    if "A" in image.getbands():
        alpha = ImageChops.multiply(alpha, image.getchannel("A"))
    rgba.putalpha(alpha)
    return rgba


def upscale_lanczos(image: Image.Image, scale: int) -> Image.Image:
    if scale not in (1, 2, 4):
        raise ValueError("scale must be 1, 2, or 4")
    if scale == 1:
        return image.copy()
    return image.resize((image.width * scale, image.height * scale), Image.Resampling.LANCZOS)


def apply_texture(
    image: Image.Image, amount: int, texture: str = "paper-fibers", seed: int = 1
) -> Image.Image:
    """Erode opaque regions with a deterministic bitmap texture mask."""
    if amount <= 0:
        return image.convert("RGBA")
    if texture not in TEXTURE_PATHS:
        raise ValueError(f"Unknown texture: {texture}")

    amount = min(100, amount)
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    rng = random.Random(seed)

    with Image.open(TEXTURE_PATHS[texture]) as opened:
        damage = ImageOps.grayscale(opened)
        damage.load()
    if texture in {"dry-ink", "vintage-tee"}:
        damage = ImageOps.invert(damage)
    damage = ImageOps.autocontrast(damage, cutoff=1)
    damage = damage.rotate(rng.choice((0, 90, 180, 270)))
    if rng.choice((False, True)):
        damage = ImageOps.mirror(damage)
    if rng.choice((False, True)):
        damage = ImageOps.flip(damage)
    damage = ImageOps.fit(
        damage,
        rgba.size,
        method=Image.Resampling.LANCZOS,
        centering=(rng.random(), rng.random()),
    )

    strength = amount / 100
    if texture == "vintage-tee":
        strength *= 0.75
    threshold = round(252 - 190 * strength)
    opacity = min(1, 0.35 + 0.85 * strength)
    scale = 255 * opacity / max(1, 255 - threshold)
    damage = damage.point(
        lambda value: 0 if value <= threshold else min(255, round((value - threshold) * scale))
    )
    damaged_alpha = ImageChops.subtract(alpha, ImageChops.multiply(alpha, damage))
    rgba.putalpha(damaged_alpha)
    return rgba


def apply_grunge(image: Image.Image, amount: int, seed: int) -> Image.Image:
    """Compatibility wrapper for the original public helper."""
    return apply_texture(image, amount, "paper-fibers", seed)


def process_builtin(source: Path, destination: Path, options: ProcessOptions) -> None:
    with Image.open(source) as opened:
        image = ImageOps.exif_transpose(opened)
        image.load()
    if options.upscale == "lanczos":
        image = upscale_lanczos(image, options.scale)
    if options.background == "threshold":
        image = remove_light_background(image)
    else:
        image = image.convert("RGBA")
    image = apply_texture(image, options.grunge, options.texture, options.seed)
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, format="PNG", optimize=True)
