#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Normalize PaddleOCR JSON results into project OCR candidate JSON.

The script accepts several common PaddleOCR output shapes:

1. PaddleOCR 3.x result dictionaries with `dt_polys`, `rec_texts`, `rec_scores`.
2. PaddleOCR 2.x `ocr.ocr(...)` style nested lists: [[box, [text, score]], ...].
3. A list of result dictionaries or a dict containing `res` / `results`.

The output is `data/ocr/<map_id>_text_candidates.json`, compatible with the
image-space review and later georeferencing pipeline.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def flatten_results(payload: Any) -> list[Any]:
    if isinstance(payload, dict):
        if {"dt_polys", "rec_texts"}.issubset(payload.keys()):
            return [payload]
        for key in ["res", "result", "results", "data"]:
            if key in payload:
                return flatten_results(payload[key])
        return [payload]
    if isinstance(payload, list):
        items: list[Any] = []
        for item in payload:
            if isinstance(item, dict) and {"dt_polys", "rec_texts"}.issubset(item.keys()):
                items.append(item)
            elif isinstance(item, list) and item and isinstance(item[0], list):
                # Could be v2 OCR results or a page list. Keep both levels parseable.
                items.append(item)
            else:
                items.extend(flatten_results(item))
        return items
    return []


def bbox_from_poly(poly: Any) -> list[float] | None:
    if not poly:
        return None
    points = []
    for point in poly:
        if isinstance(point, dict):
            points.append((float(point["x"]), float(point["y"])))
        elif isinstance(point, (list, tuple)) and len(point) >= 2:
            points.append((float(point[0]), float(point[1])))
    if not points:
        return None
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return [min(xs), min(ys), max(xs), max(ys)]


def orientation_from_bbox(bbox: list[float]) -> str:
    width = abs(bbox[2] - bbox[0])
    height = abs(bbox[3] - bbox[1])
    if height > width * 1.6:
        return "vertical"
    if width > height * 1.6:
        return "horizontal"
    return "unknown"


def candidates_from_v3(result: dict[str, Any], map_id: str) -> list[dict[str, Any]]:
    polys = result.get("dt_polys") or result.get("det_polys") or result.get("boxes") or []
    texts = result.get("rec_texts") or result.get("texts") or []
    scores = result.get("rec_scores") or result.get("scores") or []
    candidates = []
    for index, text in enumerate(texts):
        if not str(text).strip():
            continue
        poly = polys[index] if index < len(polys) else None
        bbox = bbox_from_poly(poly)
        if not bbox:
            continue
        score = scores[index] if index < len(scores) else None
        candidates.append(
            {
                "text": str(text).strip(),
                "category": "ocr_text",
                "bbox_pixel": [round(value, 2) for value in bbox],
                "orientation": orientation_from_bbox(bbox),
                "confidence": "high" if score is not None and float(score) >= 0.85 else "medium",
                "ocr_score": float(score) if score is not None else None,
                "source_map": map_id,
                "source_stage": "paddleocr",
                "reference_logic": "PaddleOCR text detection/recognition output",
                "notes": "raw_ocr_asset",
            }
        )
    return candidates


def candidates_from_v2(items: list[Any], map_id: str) -> list[dict[str, Any]]:
    candidates = []
    for item in items:
        if not isinstance(item, list) or len(item) < 2:
            continue
        box = item[0]
        rec = item[1]
        if not isinstance(rec, (list, tuple)) or not rec:
            continue
        text = str(rec[0]).strip()
        if not text:
            continue
        bbox = bbox_from_poly(box)
        if not bbox:
            continue
        score = rec[1] if len(rec) > 1 else None
        candidates.append(
            {
                "text": text,
                "category": "ocr_text",
                "bbox_pixel": [round(value, 2) for value in bbox],
                "orientation": orientation_from_bbox(bbox),
                "confidence": "high" if score is not None and float(score) >= 0.85 else "medium",
                "ocr_score": float(score) if score is not None else None,
                "source_map": map_id,
                "source_stage": "paddleocr",
                "reference_logic": "PaddleOCR text detection/recognition output",
                "notes": "raw_ocr_asset",
            }
        )
    return candidates


def normalize(payload: Any, map_id: str) -> list[dict[str, Any]]:
    candidates = []
    for result in flatten_results(payload):
        if isinstance(result, dict):
            candidates.extend(candidates_from_v3(result, map_id))
        elif isinstance(result, list):
            # If this is a page-list, each child may be a v2 item.
            for child in result:
                if isinstance(child, list) and len(child) >= 2 and isinstance(child[1], (list, tuple)):
                    candidates.extend(candidates_from_v2([child], map_id))
                elif isinstance(child, list):
                    candidates.extend(candidates_from_v2(child, map_id))
    return candidates


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--map-id", required=True)
    parser.add_argument("--image-file", default="")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    payload = json.loads(args.input.read_text(encoding="utf-8-sig"))
    candidates = normalize(payload, args.map_id)
    output = args.output or Path("data/ocr") / f"{args.map_id}_text_candidates.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    normalized = {
        "map_id": args.map_id,
        "image_file": args.image_file,
        "crs": "EPSG:3857",
        "ocr_engine": "PaddleOCR",
        "candidates": candidates,
    }
    output.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"normalized {len(candidates)} PaddleOCR candidates")
    print(output)


if __name__ == "__main__":
    main()
