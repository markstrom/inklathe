# Third-party assets

InkLathe supports locally installed texture scans, but the source image files are not
part of this repository.

## Texturelabs resources

Texturelabs permits its textures to be used in personal and commercial finished
artwork, including apparel when the texture is integrated into the design. Its terms
also prohibit sharing, transferring, redistributing, or bundling the original resources
with an app.

Consequently:

- Keep the downloaded Texturelabs JPG files in the ignored local `data/textures/`
  directory.
- Do not commit the original files, archives, lossless copies, or easily extractable
  derivatives, even while this repository is private, unless Texturelabs grants
  permission in writing.
- A private GitHub repository does not provide an additional redistribution license.
- Finished flattened artwork may be committed only when the texture is integrated into
  the work and the source texture cannot be extracted.
- The catalog in `src/inklathe/textures.json` contains metadata and expected local
  filenames, not the licensed image files themselves.

Current terms:

- <https://texturelabs.org/terms/>
- <https://texturelabs.org/faq/>

## Before making the repository public

1. Confirm that no third-party source assets are tracked in the current tree.
2. Inspect the complete Git history, not only the latest commit.
3. Remove any restricted asset from the entire history before publishing.
4. Check every remaining asset against its current license and record its source.
5. Keep `data/`, `local-textures/`, and downloaded archives ignored.

This document records the project's conservative asset-handling policy. It is not legal
advice, and the asset owner's current license terms take precedence.
