# Halftone and print-treatment masks

Place high-resolution grayscale halftone, engraved-line, or print-screen scans here.
JPEG and PNG are recommended. InkLathe converts color images to grayscale, so RGB files
also work.

Each file requires a matching `type: "halftone"` entry in the parent directory's
`textures.json` catalog, for example:

```json
{
  "id": "coarse-dots",
  "type": "halftone",
  "file": "halftone/coarse-dots.jpg",
  "name": "Coarse printed dots",
  "category": "Halftone",
  "invert": false
}
```

Set `invert` to `true` when the useful printed pattern is light on a dark scan. The
`file` path and filename must match this folder exactly. See the parent
[`README.md`](../README.md) for installation and licensing details.
