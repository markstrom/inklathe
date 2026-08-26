# Wear masks

Place high-resolution grayscale wear scans here. JPEG and PNG are recommended. InkLathe
converts color images to grayscale, so RGB files also work.

Dark marks in a scan become transparent knockouts in the artwork. Each file requires a
matching `type: "wear"` entry in the parent directory's `textures.json` catalog, for
example:

```json
{
  "id": "dry-ink-crackle",
  "type": "wear",
  "file": "wear/dry-ink-crackle.jpg",
  "name": "Dry ink crackle",
  "category": "Screen print",
  "maximum": 0.12
}
```

The `file` path and filename must match this folder exactly. See the parent
[`README.md`](../README.md) for installation and licensing details.
