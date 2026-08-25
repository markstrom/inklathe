# Legacy texture masks

These bitmap masks were generated specifically for InkLathe with OpenAI ImageGen on
2026-08-25. They do not contain third-party source material.

They are retained for visual provenance but are no longer used by the processing
pipeline. InkLathe now generates calibrated, binary print-wear masks procedurally.

- `paper-fibers.png`: sparse worn paper fibers and pinholes
- `dry-ink.png`: irregular dry screen-printing flakes and broken ink islands
- `scratches.png`: multidirectional printing-plate scratches and scuffs
- `vintage-tee.png`: calibrated screen-print cracks, cotton fibers, and small ink dropouts

Earlier InkLathe builds converted each asset to grayscale and used it as an
alpha-erosion mask. The original color pixels were never composited into a result.
