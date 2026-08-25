# InkLathe

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

## Status

Early research and prototyping. The first milestone is a CPU inference benchmark on the target NixOS server.

## License

To be decided before the first public release.
