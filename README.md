# InkLathe

<img src="assets/brand/github-wordmark-white.png" alt="InkLathe terminal wordmark" width="820">

`restore / isolate / upscale / distress`

InkLathe is a self-hosted AI image workshop for transforming logos and artwork.

![InkLathe showing two source images and four Worn results made with different scanned wear masks](assets/screenshots/inklathe-wear-showcase.png)

## Initial scope

- Upload one or multiple images
- Preview and compare results
- AI-based image upscaling
- AI-based background removal
- Optional scanned halftone and engraved print treatments
- Reproducible print wear using locally installed scan masks
- Download individual PNG files or a batch archive
- Keep downloads sortable with `original-name-00000.png` style Base62 timestamps
- Deploy reproducibly on NixOS

## Model direction

- **Upscaling:** evaluate UCAN (CVPR 2026) as the first lightweight backend
- **Background removal:** evaluate Lucida for logo and typography preservation
- **Future backends:** keep the processing API modular so newer models can be added

## Current prototype

The local MVP currently supports:

- one or multiple PNG, JPEG, or WebP uploads
- a five-image recent-source tray with selection and active-processing states
- a monochrome background-removal baseline
- 2× and 4× Lanczos previews
- reproducible, print-oriented wear with local bitmap masks
- five clear wear levels: Clean, Subtle, Worn, Heavy, and Extreme
- a compact, newest-first result gallery with dimensions, file sizes, and wear values
- full-size image previews with button and keyboard navigation
- a 2.5× click-to-zoom preview with pointer-position panning
- a movable circular original-image lens for pixel-aligned before/after comparison
- individual PNG downloads from every result card
- confirmed result deletion from cards or the full-size preview
- Alt-click deletion without confirmation for faster result cleanup
- a single-worker job queue suitable for the target server
- a persistent content-addressed stage cache for normalization, scaling, and background removal
- a 20 GB storage ceiling that evicts least-recently-used cache files before old jobs

Lucida and the selected AI upscaler are exposed as optional worker adapters. They remain disabled in the UI until their commands and model weights are installed.

## Run the prototype

Requires Python 3.12 or newer.

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
INKLATHE_DATA_DIR=./data .venv/bin/inklathe
```

Set `INKLATHE_MAX_DATA_GB` to change the total storage ceiling. When the limit is
reached, InkLathe cleans down to 90%, evicting cache files before completed jobs.
The current and queued jobs are always protected. Set it to `0` to disable cleanup.

### Local print masks

InkLathe can use high-resolution grayscale texture scans without redistributing them.
Place licensed copies in `$INKLATHE_DATA_DIR/textures` (the default) or set
`INKLATHE_TEXTURE_DIR` to another private directory. InkLathe recognizes the locally
installed `Grunge_141XL.jpg`, `Grunge_197XL.jpg`, `Grunge_198XL.jpg`,
`Grunge_272XL.jpg`, `Grunge_296XL.jpg` through `Grunge_299XL.jpg`,
`Grunge_306XL.jpg` through `Grunge_311XL.jpg`, `Grunge_313XL.jpg`, and
`Grunge_327XL.jpg` files.
Detected masks appear first in the Wear style menu. The app converts dark scanned
marks into binary transparent ink knockouts, uses one large non-tiled crop, and keeps
the result reproducible through the Pattern variation control.

The optional Print treatment menu recognizes `Texturelabs_Grunge_234XL.jpg`,
`Texturelabs_Grunge_242XL.jpg`, `Texturelabs_Grunge_246XL.jpg`,
`Texturelabs_Grunge_283XL.jpg`, `Texturelabs_Grunge_289XL.jpg`,
`Texturelabs_Grunge_290XL.jpg`, `Texturelabs_Grunge_340XL.jpg`,
`Texturelabs_Grunge_351XL.jpg`, `Texturelabs_Grunge_354XL.jpg`, and
`Texturelabs_Grunge_356XL.jpg` in the same directory. These masks screen the isolated
ink into binary printable dots or engraved lines before the selected wear is applied.

Do not commit third-party texture files unless their license explicitly permits
redistribution as part of an image-processing application.

Open <http://127.0.0.1:8787>.

Run the checks with:

```bash
.venv/bin/ruff check src tests scripts
.venv/bin/pytest -q
```

The next milestone is packaging the AI workers and benchmarking them on the target NixOS server.

## License

To be decided before the first public release.
