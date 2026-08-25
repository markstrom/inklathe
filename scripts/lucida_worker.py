from __future__ import annotations

import argparse
from pathlib import Path

LUCIDA_MODEL = "egeorcun/lucida"
LUCIDA_REVISION = "6cbedc9722652dc9a3df91dd871f0c4f3334e922"


def load_model(model_id: str):
    import torch
    from transformers import AutoModelForImageSegmentation

    if model_id != "lucida":
        raise ValueError(f"Unsupported Lucida model: {model_id}")
    model = AutoModelForImageSegmentation.from_pretrained(
        LUCIDA_MODEL,
        revision=LUCIDA_REVISION,
        trust_remote_code=True,
    )
    model.eval()
    return model, torch


def remove_background(source: Path, destination: Path, model_id: str) -> None:
    from PIL import Image
    from torchvision import transforms

    model, torch = load_model(model_id)
    image = Image.open(source).convert("RGB")
    preprocess = transforms.Compose(
        [
            transforms.Resize((1024, 1024)),
            transforms.ToTensor(),
            transforms.Normalize(
                [0.485, 0.456, 0.406],
                [0.229, 0.224, 0.225],
            ),
        ]
    )
    with torch.no_grad():
        alpha = model(preprocess(image).unsqueeze(0))[-1].sigmoid().cpu()[0]
    alpha_image = transforms.ToPILImage()(alpha).resize(
        image.size, Image.Resampling.LANCZOS
    )
    image.putalpha(alpha_image)
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, "PNG")


def main() -> None:
    parser = argparse.ArgumentParser(prog="inklathe-lucida")
    commands = parser.add_subparsers(dest="command", required=True)

    prepare = commands.add_parser("prepare")
    prepare.add_argument("--model", default="lucida")

    remove = commands.add_parser("remove")
    remove.add_argument("source", type=Path)
    remove.add_argument("-o", "--output", required=True, type=Path)
    remove.add_argument("--model", default="lucida")

    arguments = parser.parse_args()
    if arguments.command == "prepare":
        load_model(arguments.model)
        return
    remove_background(arguments.source, arguments.output, arguments.model)


if __name__ == "__main__":
    main()
