from __future__ import annotations

import random
import warnings
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter, ImageOps

# These files are intentionally not distributed with InkLathe. They may be placed in
# INKLATHE_TEXTURE_DIR by a server owner who has obtained the corresponding licenses.
BITMAP_TEXTURE_PROFILES = {
    "scan-g306": {
        "filename": "Grunge_306XL.jpg",
        "label": "Heavy screen ink · G306",
        "category": "Screen print",
        "maximum": 0.12,
    },
    "scan-g296": {
        "filename": "Grunge_296XL.jpg",
        "label": "Vintage screen distress · G296",
        "category": "Screen print",
        "maximum": 0.10,
    },
    "scan-g307": {
        "filename": "Grunge_307XL.jpg",
        "label": "Large print crackle · G307",
        "category": "Screen print",
        "maximum": 0.12,
    },
    "scan-g308": {
        "filename": "Grunge_308XL.jpg",
        "label": "Vintage ink wear · G308",
        "category": "Screen print",
        "maximum": 0.12,
    },
    "scan-g297": {
        "filename": "Grunge_297XL.jpg",
        "label": "Distressed plastisol · G297",
        "category": "Plastisol",
        "maximum": 0.10,
    },
    "scan-g298": {
        "filename": "Grunge_298XL.jpg",
        "label": "Vintage washed T-shirt · G298",
        "category": "Plastisol",
        "maximum": 0.09,
    },
    "scan-g299": {
        "filename": "Grunge_299XL.jpg",
        "label": "Cracked screen-print ink · G299",
        "category": "Plastisol",
        "maximum": 0.09,
    },
    "scan-g309": {
        "filename": "Grunge_309XL.jpg",
        "label": "Fine plastisol fissures · G309",
        "category": "Plastisol",
        "maximum": 0.09,
    },
    "scan-g310": {
        "filename": "Grunge_310XL.jpg",
        "label": "Heavy plastisol cracks · G310",
        "category": "Plastisol",
        "maximum": 0.11,
    },
    "scan-g313": {
        "filename": "Grunge_313XL.jpg",
        "label": "Large print cracks · G313",
        "category": "Plastisol",
        "maximum": 0.12,
    },
    "scan-g311": {
        "filename": "Grunge_311XL.jpg",
        "label": "Medium speckles · G311",
        "category": "Fine wear",
        "maximum": 0.10,
    },
    "scan-g272": {
        "filename": "Grunge_272XL.jpg",
        "label": "Weathered ink grain · G272",
        "category": "Fine wear",
        "maximum": 0.11,
    },
    "scan-g327": {
        "filename": "Grunge_327XL.jpg",
        "label": "Heavy grunge mask · G327",
        "category": "Heavy wear",
        "maximum": 0.15,
    },
    "scan-g141": {
        "filename": "Grunge_141XL.jpg",
        "label": "Detailed cracked paint · G141",
        "category": "Paint crackle",
        "maximum": 0.10,
    },
    "scan-g197": {
        "filename": "Grunge_197XL.jpg",
        "label": "Cracked paint on canvas · G197",
        "category": "Paint crackle",
        "maximum": 0.10,
    },
    "scan-g198": {
        "filename": "Grunge_198XL.jpg",
        "label": "Dense cracked paint · G198",
        "category": "Paint crackle",
        "maximum": 0.12,
    },
}

# Halftone scans are also user-installed and intentionally excluded from the
# repository. ``invert`` describes scans whose printable marks are dark on a
# light background; the generated alpha mask always uses white for printed ink.
HALFTONE_PROFILES = {
    "halftone-g289": {
        "filename": "Texturelabs_Grunge_289XL.jpg",
        "label": "Black halftone floodcoat",
        "category": "Halftone",
        "invert": True,
    },
    "halftone-g290": {
        "filename": "Texturelabs_Grunge_290XL.jpg",
        "label": "Distressed halftone print",
        "category": "Halftone",
        "invert": True,
    },
    "halftone-g242": {
        "filename": "Texturelabs_Grunge_242XL.jpg",
        "label": "Printed halftone gradient",
        "category": "Halftone",
        "invert": True,
    },
    "halftone-g283": {
        "filename": "Texturelabs_Grunge_283XL.jpg",
        "label": "Detailed money pattern",
        "category": "Engraved",
        "invert": True,
    },
}


def available_bitmap_textures(texture_dir: Path | None) -> dict[str, dict[str, object]]:
    if texture_dir is None:
        return {}
    return {
        key: {**profile, "path": texture_dir / str(profile["filename"])}
        for key, profile in BITMAP_TEXTURE_PROFILES.items()
        if (texture_dir / str(profile["filename"])).is_file()
    }


def available_halftones(texture_dir: Path | None) -> dict[str, dict[str, object]]:
    if texture_dir is None:
        return {}
    return {
        key: {**profile, "path": texture_dir / str(profile["filename"])}
        for key, profile in HALFTONE_PROFILES.items()
        if (texture_dir / str(profile["filename"])).is_file()
    }


def _load_grayscale_scan(path: Path) -> Image.Image:
    # Configured local masks are trusted assets, unlike images uploaded through
    # the public endpoint, and several XL scans intentionally exceed 40 MP.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", Image.DecompressionBombWarning)
        with Image.open(path) as opened:
            grayscale = ImageOps.grayscale(ImageOps.exif_transpose(opened))
            grayscale.load()
    return grayscale


@dataclass(frozen=True)
class ProcessOptions:
    background: str = "threshold"
    upscale: str = "lanczos"
    scale: int = 4
    grunge: int = 0
    seed: int = 1
    texture: str = "scan-g306"
    halftone: str = "none"


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


def apply_halftone(
    image: Image.Image,
    treatment: str = "none",
    seed: int = 1,
    *,
    texture_path: Path | None = None,
    invert: bool = False,
) -> Image.Image:
    """Screen existing ink through a scanned, binary print pattern."""
    if treatment == "none":
        return image.convert("RGBA")
    if texture_path is None:
        raise ValueError(f"Halftone file is not installed: {treatment}")

    rgba = image.convert("RGBA")
    rng = random.Random(seed)
    scan = _load_grayscale_scan(texture_path)

    # Remove incidental scanner edges while retaining one non-repeating field.
    margin_x = round(scan.width * 0.02)
    margin_y = round(scan.height * 0.02)
    scan = scan.crop((margin_x, margin_y, scan.width - margin_x, scan.height - margin_y))
    if rng.random() < 0.5:
        scan = ImageOps.mirror(scan)
    if rng.random() < 0.5:
        scan = ImageOps.flip(scan)
    mask = ImageOps.fit(
        scan,
        rgba.size,
        method=Image.Resampling.LANCZOS,
        centering=(rng.uniform(0.35, 0.65), rng.uniform(0.35, 0.65)),
    )
    mask = ImageOps.autocontrast(mask, cutoff=0.5)
    if invert:
        mask = ImageOps.invert(mask)
    mask = mask.point(lambda value: 255 if value >= 128 else 0)

    rgba.putalpha(ImageChops.multiply(rgba.getchannel("A"), mask))
    return rgba


def apply_texture(
    image: Image.Image,
    amount: int,
    texture: str = "scan-g306",
    seed: int = 1,
    *,
    texture_path: Path | None = None,
    maximum: float | None = None,
) -> Image.Image:
    """Apply deterministic, print-oriented wear as fully transparent knockouts."""
    if amount <= 0:
        return image.convert("RGBA")
    if texture_path is None:
        raise ValueError(f"Texture file is not installed: {texture}")

    amount = min(100, amount)
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    rng = random.Random(seed)
    foreground = alpha.point(lambda value: 255 if value >= 128 else 0)
    work_size = _working_size(rgba.size)
    work_foreground = foreground.resize(work_size, Image.Resampling.NEAREST)
    score = _bitmap_texture_score(texture_path, work_size, rng)
    score = _protect_thin_marks(score, work_foreground)
    tie_breaker = _random_field(work_size, rng, 700, 0)
    score = score.resize(rgba.size, Image.Resampling.BICUBIC)
    tie_breaker = tie_breaker.resize(rgba.size, Image.Resampling.BICUBIC)
    profile_maximum = maximum if maximum is not None else 0.12
    target = _target_removed_fraction(amount, profile_maximum)
    damage = _select_damage(score, tie_breaker, foreground, target)
    damaged_alpha = ImageChops.subtract(alpha, ImageChops.multiply(alpha, damage))
    rgba.putalpha(damaged_alpha)
    return rgba


def _bitmap_texture_score(
    texture_path: Path, size: tuple[int, int], rng: random.Random
) -> Image.Image:
    """Turn a licensed, user-installed grayscale scan into a deterministic wear field."""
    grayscale = _load_grayscale_scan(texture_path)

    # Texture scans often contain hard frame shadows. Use the useful central 89%.
    margin_x = round(grayscale.width * 0.055)
    margin_y = round(grayscale.height * 0.055)
    grayscale = grayscale.crop(
        (margin_x, margin_y, grayscale.width - margin_x, grayscale.height - margin_y)
    )
    if rng.random() < 0.5:
        grayscale = ImageOps.mirror(grayscale)
    if rng.random() < 0.5:
        grayscale = ImageOps.flip(grayscale)

    # Never tile: a single large crop preserves the natural scale and clustering.
    fitted = ImageOps.fit(
        grayscale,
        size,
        method=Image.Resampling.LANCZOS,
        centering=(rng.uniform(0.35, 0.65), rng.uniform(0.35, 0.65)),
    )
    # Dark marks in the scan are the parts removed from the printed ink.
    return ImageOps.autocontrast(ImageOps.invert(fitted), cutoff=0.35)


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
