#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render OCR candidates as boxes on top of the source map image."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont


CATEGORY_COLORS = {
    "ocr_街巷道路": (230, 130, 0),
    "ocr_城防官署": (150, 60, 210),
    "ocr_寺观": (30, 145, 70),
    "ocr_山体": (125, 90, 45),
    "ocr_水系": (0, 120, 220),
    "ocr_文字": (70, 70, 70),
}


def load_payload(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(payload, list):
        return {"map_id": path.stem.replace("_text_candidates", ""), "candidates": payload}
    return payload


def choose_font(size: int) -> ImageFont.ImageFont:
    for font_path in [
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("C:/Windows/Fonts/simsun.ttc"),
    ]:
        if font_path.exists():
            return ImageFont.truetype(str(font_path), size)
    return ImageFont.load_default()


def draw_label(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    font: ImageFont.ImageFont,
    color: tuple[int, int, int],
) -> None:
    x, y = xy
    bbox = draw.textbbox((x, y), text, font=font)
    pad = 2
    bg = (255, 255, 255, 220)
    draw.rectangle(
        [bbox[0] - pad, bbox[1] - pad, bbox[2] + pad, bbox[3] + pad],
        fill=bg,
        outline=None,
    )
    draw.text((x, y), text, fill=color + (255,), font=font)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--max-labels", type=int, default=180)
    args = parser.parse_args()

    payload = load_payload(args.candidates)
    map_id = payload.get("map_id") or args.candidates.stem.replace("_text_candidates", "")
    output = args.output or Path("data/ocr/previews") / f"{map_id}_preview.png"
    output.parent.mkdir(parents=True, exist_ok=True)

    base = Image.open(args.image).convert("RGBA")
    overlay = Image.new("RGBA", base.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)
    font = choose_font(max(14, int(max(base.size) / 115)))

    candidates = payload.get("candidates", [])
    sorted_candidates = sorted(
        candidates,
        key=lambda item: float(item.get("quality") or item.get("confidence") or 0),
        reverse=True,
    )
    label_ids = {id(item) for item in sorted_candidates[: args.max_labels]}

    for candidate in candidates:
        bbox = candidate.get("bbox_pixel")
        text = str(candidate.get("text") or "").strip()
        if not bbox or len(bbox) != 4 or not text:
            continue
        x1, y1, x2, y2 = [float(value) for value in bbox]
        color = CATEGORY_COLORS.get(candidate.get("category"), (70, 70, 70))
        draw.rectangle([x1, y1, x2, y2], outline=color + (230,), width=3)
        draw.rectangle([x1, y1, x2, y2], fill=color + (28,))
        if id(candidate) in label_ids:
            quality = candidate.get("quality") or candidate.get("confidence") or ""
            suffix = f" {float(quality):.2f}" if isinstance(quality, (int, float)) else ""
            draw_label(draw, (x1, max(0, y1 - 22)), text + suffix, font, color)

    result = Image.alpha_composite(base, overlay).convert("RGB")
    result.save(output, quality=92)
    print(f"rendered {len(candidates)} OCR boxes -> {output}")


if __name__ == "__main__":
    main()
