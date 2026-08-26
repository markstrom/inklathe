# Private texture library scaffold

This directory documents the file layout for InkLathe's private print masks. Files
placed here are not loaded automatically. The active directory is normally:

- `data/textures/` when InkLathe runs locally from the repository
- `/var/lib/inklathe/textures/` on the NixOS server
- the directory specified by `INKLATHE_TEXTURE_DIR`, when that variable is set

Copy the wanted image files and a catalog named exactly `textures.json` into the active
directory. [`textures.example.json`](textures.example.json) shows the required catalog
shape.

## Layout

```text
textures/
├── textures.json
├── wear/
│   └── dry-ink-crackle.jpg
└── halftone/
    └── coarse-dots.jpg
```

The `file` value in each `textures.json` entry is relative to the directory containing
that catalog. It is case-sensitive on Linux and must match the real path exactly:

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

- `id` is the stable internal value. Use lowercase letters, numbers, and hyphens.
- `type` decides the menu: `wear` for Wear style or `halftone` for Print treatment.
- `file` connects the catalog entry to the image file.
- `name` is the text shown in the dropdown.
- `category` creates the dropdown group.
- `maximum` is required for wear masks and limits the strongest ink removal.
- `invert` is used by halftone masks to reverse the scan's light/dark interpretation.

A local `textures.json` replaces the bundled catalog completely. An entry is shown only
when its referenced image exists. Restart InkLathe after changing the catalog or files.

The image folders ignore common bitmap formats in Git by default because downloaded
third-party textures may not be redistributable. Remove or override those ignore rules
only for files whose license permits committing them. Review
[`THIRD_PARTY_ASSETS.md`](../THIRD_PARTY_ASSETS.md) before making the repository public.

