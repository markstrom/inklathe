from __future__ import annotations

import math
import random
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

TEXTURE_PROFILES = {
    "worn-ink": 0.12,
    "cracked-plastisol": 0.08,
    "dry-screen": 0.15,
    "scuffed-print": 0.07,
    "vintage-mix": 0.15,
}


@dataclass(frozen=True)
class ProcessOptions:
    background: str = "threshold"
    upscale: str = "lanczos"
    scale: int = 4
    grunge: int = 0
    seed: int = 1
    texture: str = "vintage-mix"


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
    image: Image.Image, amount: int, texture: str = "vintage-mix", seed: int = 1
) -> Image.Image:
    """Apply deterministic, print-oriented wear as fully transparent knockouts."""
    if amount <= 0:
        return image.convert("RGBA")
    if texture not in TEXTURE_PROFILES:
        raise ValueError(f"Unknown texture: {texture}")

    amount = min(100, amount)
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    rng = random.Random(seed)
    foreground = alpha.point(lambda value: 255 if value >= 128 else 0)
    work_size = _working_size(rgba.size)
    work_foreground = foreground.resize(work_size, Image.Resampling.NEAREST)
    score = _texture_score(texture, work_size, rng)
    score = _protect_thin_marks(score, work_foreground)
    tie_breaker = _random_field(work_size, rng, 700, 0)
    score = score.resize(rgba.size, Image.Resampling.BICUBIC)
    tie_breaker = tie_breaker.resize(rgba.size, Image.Resampling.BICUBIC)
    target = _target_removed_fraction(amount, TEXTURE_PROFILES[texture])
    damage = _select_damage(score, tie_breaker, foreground, target)
    damaged_alpha = ImageChops.subtract(alpha, ImageChops.multiply(alpha, damage))
    rgba.putalpha(damaged_alpha)
    return rgba


def _working_size(size: tuple[int, int], max_side: int = 1400) -> tuple[int, int]:
    width, height = size
    longest = max(width, height)
    if longest <= max_side:
        return size
    scale = max_side / longest
    return max(1, round(width * scale)), max(1, round(height * scale))


def _target_removed_fraction(amount: int, maximum: float) -> float:
    """Map Wear to an intentionally gentle target area instead of an image threshold."""
    return maximum * (max(0, min(100, amount)) / 100) ** 1.55


def _random_field(
    size: tuple[int, int], rng: random.Random, cells_across: int, blur: float = 0
) -> Image.Image:
    width, height = size
    longest = max(width, height)
    scale = max(2, cells_across) / longest
    source_size = max(2, round(width * scale)), max(2, round(height * scale))
    field = Image.frombytes("L", source_size, rng.randbytes(source_size[0] * source_size[1]))
    field = field.resize(size, Image.Resampling.BICUBIC)
    if blur > 0:
        field = field.filter(ImageFilter.GaussianBlur(blur))
    return field


def _worn_ink_score(size: tuple[int, int], rng: random.Random) -> Image.Image:
    fine = _random_field(size, rng, 380, 0.35)
    mid = _random_field(size, rng, 105, 0.8)
    coarse = _random_field(size, rng, 28, 2.2)
    clustered = ImageChops.multiply(fine, ImageChops.blend(mid, coarse, 0.35))

    fibers = Image.new("L", size)
    draw = ImageDraw.Draw(fibers)
    width, height = size
    count = max(30, width * height // 11000)
    unit = max(1, round(min(size) / 500))
    for _ in range(count):
        x = rng.randrange(width)
        y = rng.randrange(height)
        length = rng.randint(4 * unit, 22 * unit)
        drift = rng.randint(-2 * unit, 2 * unit)
        draw.line(
            ((x, y), (x + drift, min(height - 1, y + length))),
            fill=rng.randint(150, 255),
            width=rng.randint(1, max(1, 2 * unit)),
        )
    return ImageOps.autocontrast(ImageChops.lighter(clustered, fibers), cutoff=1)


def _dry_screen_score(size: tuple[int, int], rng: random.Random) -> Image.Image:
    fine = _random_field(size, rng, 300, 0.45)
    islands = _random_field(size, rng, 72, 1.25)
    broad = _random_field(size, rng, 20, 3.0)
    score = ImageChops.multiply(fine, ImageChops.add(islands, broad, scale=2))
    score = score.filter(ImageFilter.MaxFilter(3))
    return ImageOps.autocontrast(score, cutoff=1)


def _cracked_plastisol_score(size: tuple[int, int], rng: random.Random) -> Image.Image:
    width, height = size
    background = _random_field(size, rng, 260, 0.5).point(lambda value: round(value * 0.3))
    cracks = Image.new("L", size)
    draw = ImageDraw.Draw(cracks)
    unit = max(1, round(min(size) / 650))
    crack_count = max(12, width * height // 32000)

    for _ in range(crack_count):
        x = rng.uniform(0, width - 1)
        y = rng.uniform(-height * 0.08, height * 0.72)
        length = rng.uniform(height * 0.16, height * 0.7)
        steps = max(5, round(length / max(3, height / 45)))
        step_y = length / steps
        points = [(round(x), round(y))]
        for _step in range(steps):
            x += rng.uniform(-step_y * 0.42, step_y * 0.42)
            y += step_y
            points.append((round(x), round(y)))
        intensity = rng.randint(125, 255)
        line_width = rng.randint(unit, max(unit, 3 * unit))
        draw.line(points, fill=intensity, width=line_width, joint="curve")

        if len(points) > 5 and rng.random() < 0.75:
            branch_index = rng.randint(2, len(points) - 3)
            bx, by = points[branch_index]
            direction = rng.choice((-1, 1))
            branch = [(bx, by)]
            for branch_step in range(rng.randint(3, 8)):
                bx += direction * rng.uniform(2, 7) * unit
                by += rng.uniform(2, 6) * unit
                branch.append((round(bx), round(by)))
            draw.line(
                branch,
                fill=max(90, intensity - rng.randint(10, 55)),
                width=max(1, line_width - unit),
                joint="curve",
            )

    chips = max(20, width * height // 26000)
    for _ in range(chips):
        x = rng.randrange(width)
        y = rng.randrange(height)
        radius_x = rng.randint(unit, 4 * unit)
        radius_y = rng.randint(unit, 3 * unit)
        draw.ellipse(
            (x - radius_x, y - radius_y, x + radius_x, y + radius_y),
            fill=rng.randint(75, 185),
        )
    return ImageOps.autocontrast(ImageChops.lighter(background, cracks), cutoff=1)


def _scuffed_print_score(size: tuple[int, int], rng: random.Random) -> Image.Image:
    width, height = size
    background = _random_field(size, rng, 300, 0.35).point(lambda value: round(value * 0.12))
    scuffs = Image.new("L", size)
    draw = ImageDraw.Draw(scuffs)
    unit = max(1, round(min(size) / 650))
    cluster_count = max(5, width * height // 150000)

    for _ in range(cluster_count):
        cx = rng.uniform(width * 0.06, width * 0.94)
        cy = rng.uniform(height * 0.06, height * 0.94)
        angle = rng.uniform(-0.45, 0.45) + rng.choice((0, math.pi / 2))
        along_x, along_y = math.cos(angle), math.sin(angle)
        across_x, across_y = -along_y, along_x
        for _mark in range(rng.randint(28, 70)):
            offset = rng.uniform(-34, 34) * unit
            start_shift = rng.uniform(-22, 22) * unit
            length = rng.uniform(10, 85) * unit
            start_x = cx + across_x * offset + along_x * start_shift
            start_y = cy + across_y * offset + along_y * start_shift
            end_x = start_x + along_x * length
            end_y = start_y + along_y * length
            draw.line(
                ((round(start_x), round(start_y)), (round(end_x), round(end_y))),
                fill=rng.randint(95, 255),
                width=rng.randint(1, max(1, 3 * unit)),
            )
    return ImageOps.autocontrast(ImageChops.lighter(background, scuffs), cutoff=1)


def _texture_score(texture: str, size: tuple[int, int], rng: random.Random) -> Image.Image:
    if texture == "worn-ink":
        return _worn_ink_score(size, rng)
    if texture == "cracked-plastisol":
        return _cracked_plastisol_score(size, rng)
    if texture == "dry-screen":
        return _dry_screen_score(size, rng)
    if texture == "scuffed-print":
        return _scuffed_print_score(size, rng)
    if texture == "vintage-mix":
        worn = _worn_ink_score(size, rng)
        cracks = _cracked_plastisol_score(size, rng)
        scuffs = _scuffed_print_score(size, rng)
        return ImageOps.autocontrast(
            ImageChops.blend(ImageChops.blend(worn, cracks, 0.28), scuffs, 0.14),
            cutoff=1,
        )
    raise ValueError(f"Unknown texture: {texture}")


def _protect_thin_marks(score: Image.Image, foreground: Image.Image) -> Image.Image:
    radius = max(1, round(min(foreground.size) / 320))
    interior = foreground.filter(ImageFilter.MinFilter(radius * 2 + 1))
    edge_weight = ImageChops.lighter(interior, Image.new("L", foreground.size, 72))
    return ImageChops.multiply(score, edge_weight)


def _select_damage(
    score: Image.Image, tie_breaker: Image.Image, foreground: Image.Image, target: float
) -> Image.Image:
    histogram = score.histogram(foreground)
    foreground_pixels = sum(histogram)
    target_pixels = round(foreground_pixels * target)
    if target_pixels <= 0:
        return Image.new("L", score.size)

    selected_above = 0
    threshold = 255
    for value in range(255, -1, -1):
        threshold = value
        if selected_above + histogram[value] >= target_pixels:
            break
        selected_above += histogram[value]

    damage = score.point(lambda value: 255 if value > threshold else 0)
    damage = ImageChops.multiply(damage, foreground)
    remaining = target_pixels - selected_above
    if remaining <= 0:
        return damage

    ties = score.point(lambda value: 255 if value == threshold else 0)
    ties = ImageChops.multiply(ties, foreground)
    tie_histogram = tie_breaker.histogram(ties)
    selected_ties_above = 0
    tie_threshold = 255
    for value in range(255, -1, -1):
        tie_threshold = value
        if selected_ties_above + tie_histogram[value] >= remaining:
            break
        selected_ties_above += tie_histogram[value]
    selected_ties = tie_breaker.point(
        lambda value: 255 if value >= tie_threshold else 0
    )
    selected_ties = ImageChops.multiply(selected_ties, ties)
    return ImageChops.lighter(damage, selected_ties)


def apply_grunge(image: Image.Image, amount: int, seed: int) -> Image.Image:
    """Compatibility wrapper for the original public helper."""
    return apply_texture(image, amount, "vintage-mix", seed)


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
