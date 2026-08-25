# InkLathe

<img src="assets/brand/github-wordmark-white.png" alt="InkLathe terminal wordmark" width="820">

`restore / isolate / upscale / distress`

InkLathe is a self-hosted AI image workshop for transforming logos and artwork.

## Initial scope

- Upload one or multiple images
- Preview and compare results
- AI-based image upscaling
- AI-based background removal
- Reproducible grunge effects
- Download individual PNG files or a batch archive
- Deploy reproducibly on NixOS

## Model direction

- **Upscaling:** evaluate UCAN (CVPR 2026) as the first lightweight backend
- **Background removal:** evaluate Lucida for logo and typography preservation
- **Future backends:** keep the processing API modular so newer models can be added

## Current prototype

The local MVP currently supports:

- one or multiple PNG, JPEG, or WebP uploads
- a monochrome background-removal baseline
- 2× and 4× Lanczos previews
- reproducible, progressively scaled grunge
- retained result runs with settings, dimensions, and file sizes
- full-size image previews
- individual PNG and batch ZIP downloads
- a single-worker job queue suitable for the target server

Lucida and the selected AI upscaler are exposed as optional worker adapters. They remain disabled in the UI until their commands and model weights are installed.

## Run the prototype

Requires Python 3.12 or newer.

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
INKLATHE_DATA_DIR=./data .venv/bin/inklathe
```

Open <http://127.0.0.1:8787>.

Run the checks with:

```bash
.venv/bin/ruff check src tests scripts
.venv/bin/pytest -q
```

The next milestone is packaging the AI workers and benchmarking them on the target NixOS server.

## License

To be decided before the first public release.
