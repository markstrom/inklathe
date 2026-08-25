from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps


@dataclass(frozen=True)
class ProcessOptions:
    background: str = "threshold"
    upscale: str = "lanczos"
    scale: int = 4
    grunge: int = 0
    seed: int = 1


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


def apply_grunge(image: Image.Image, amount: int, seed: int) -> Image.Image:
    """Deterministically erode opaque regions to create printable wear."""
    if amount <= 0:
        return image.convert("RGBA")
    amount = min(100, amount)
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    rng = random.Random(seed)
    damage = Image.new("L", rgba.size, 0)
    draw = ImageDraw.Draw(damage)
    area = rgba.width * rgba.height
    short_side = max(1, min(rgba.size))
    strength = amount / 100
    aspect_density = area / (short_side * short_side)
    foreground_bounds = alpha.getbbox() or (0, 0, rgba.width, rgba.height)
    marks = max(1, round((20 + 250 * aspect_density) * strength**1.6))
    min_radius = max(1, round(short_side * (0.001 + 0.0015 * strength)))
    max_radius = max(min_radius + 1, round(short_side * (0.0025 + 0.018 * strength)))
    damage_low = round(30 + 85 * strength)
    damage_high = round(70 + 185 * strength)

    for _ in range(marks):
        radius = rng.randint(min_radius, max_radius)
        x, y = _foreground_point(alpha, foreground_bounds, rng)
        stretch = rng.uniform(0.35, 2.8)
        box = (x - radius * stretch, y - radius, x + radius * stretch, y + radius)
        draw.ellipse(box, fill=rng.randint(damage_low, damage_high))

    speckles = max(1, round((30 + 400 * aspect_density) * strength**1.8))
    max_length = max(2, round(short_side * (0.001 + 0.01 * strength)))
    for _ in range(speckles):
        length = rng.randint(1, max_length)
        x, y = _foreground_point(alpha, foreground_bounds, rng)
        draw.line(
            (x, y, min(rgba.width - 1, x + length), y + rng.randint(-2, 2)),
            fill=rng.randint(damage_low, damage_high),
            width=max(1, round(short_side * (0.0005 + 0.002 * strength))),
        )
    damage = damage.filter(ImageFilter.GaussianBlur(0.35))
    damaged_alpha = ImageChops.subtract(alpha, ImageChops.multiply(alpha, damage))
    rgba.putalpha(damaged_alpha)
    return rgba


def _foreground_point(
    alpha: Image.Image, bounds: tuple[int, int, int, int], rng: random.Random
) -> tuple[int, int]:
    left, top, right, bottom = bounds
    for _ in range(40):
        point = (rng.randrange(left, right), rng.randrange(top, bottom))
        if alpha.getpixel(point) > 32:
            return point
    return (rng.randrange(left, right), rng.randrange(top, bottom))


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
    image = apply_grunge(image, options.grunge, options.seed)
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, format="PNG", optimize=True)
