#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Convert OCR candidate bboxes to image-space GeoJSON.

This is for reviewing OCR content and text boxes on top of the original image.
It deliberately does not georeference the text to modern map coordinates.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_payload(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(payload, list):
        return {"map_id": path.stem.replace("_text_candidates", ""), "candidates": payload}
    return payload


def bbox_polygon(bbox: list[float]) -> list[list[float]]:
    x1, y1, x2, y2 = [float(value) for value in bbox]
    # QGIS coordinates are y-up, while image pixels are y-down.
    return [
        [x1, -y1],
        [x2, -y1],
        [x2, -y2],
        [x1, -y2],
        [x1, -y1],
    ]


def feature_for_candidate(index: int, candidate: dict[str, Any]) -> dict[str, Any] | None:
    bbox = candidate.get("bbox_pixel")
    text = str(candidate.get("text") or candidate.get("name") or "").strip()
    if not bbox or len(bbox) != 4 or not text:
        return None
    x1, y1, x2, y2 = [float(value) for value in bbox]
    properties = {
        "ocr_id": candidate.get("ocr_id") or f"ocr_{index:04d}",
        "text": text,
        "ocr_text_raw_order": candidate.get("ocr_text_raw_order", ""),
        "reading_rule": candidate.get("reading_rule", ""),
        "raw_text": candidate.get("raw_text", ""),
        "category": candidate.get("category", "ocr_text"),
        "confidence": candidate.get("confidence", ""),
        "quality": candidate.get("quality", ""),
        "orientation": candidate.get("orientation", ""),
        "source_map": candidate.get("source_map", ""),
        "source_stage": candidate.get("source_stage", ""),
        "engine": candidate.get("engine", ""),
        "ocr_variant": candidate.get("ocr_variant", ""),
        "ocr_pass": candidate.get("ocr_pass", ""),
        "alternative_texts": candidate.get("alternative_texts", ""),
        "alternative_count": candidate.get("alternative_count", ""),
        "reference_logic": candidate.get("reference_logic", ""),
        "notes": candidate.get("notes", ""),
        "pixel_x1": x1,
        "pixel_y1": y1,
        "pixel_x2": x2,
        "pixel_y2": y2,
        "pixel_cx": (x1 + x2) / 2.0,
        "pixel_cy": (y1 + y2) / 2.0,
        "pixel_w": x2 - x1,
        "pixel_h": y2 - y1,
    }
    if candidate.get("quad_pixel"):
        properties["quad_pixel_json"] = json.dumps(candidate.get("quad_pixel"), ensure_ascii=False)

    return {
        "type": "Feature",
        "properties": properties,
        "geometry": {
            "type": "Polygon",
            "coordinates": [bbox_polygon(bbox)],
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    payload = load_payload(args.candidates)
    map_id = payload.get("map_id") or args.candidates.stem.replace("_text_candidates", "")
    output = args.output or Path("data/ocr/image_space") / f"{map_id}_ocr_image_space.geojson"
    output.parent.mkdir(parents=True, exist_ok=True)

    features = []
    for index, candidate in enumerate(payload.get("candidates", []), start=1):
        feature = feature_for_candidate(index, candidate)
        if feature:
            features.append(feature)

    collection = {
        "type": "FeatureCollection",
        "name": output.stem,
        "crs": {"type": "name", "properties": {"name": "EPSG:3857"}},
        "features": features,
    }
    output.write_text(json.dumps(collection, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {len(features)} image-space OCR boxes")
    print(output)


if __name__ == "__main__":
    main()
