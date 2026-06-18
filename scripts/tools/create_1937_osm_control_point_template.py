#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create a control-point CSV template for fitting 1937 pixels to OSM."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


FIELDS = [
    "control_id",
    "enabled",
    "name",
    "role",
    "pixel_x",
    "pixel_y",
    "map_x",
    "map_y",
    "source_ocr_id",
    "source_text",
    "ocr_confidence",
    "osm_reference",
    "weight",
    "notes",
]


PRIORITY_NAMES = {
    "清波门",
    "浙江病院",
    "紫陽山",
    "海潮寺",
    "外学士桥",
    "中正河下街",
    "工兵营",
    "武林",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", type=Path, default=Path("data/ocr/1937_rapidocr_text_candidates.json"))
    parser.add_argument("--master", type=Path, default=Path("data/places/linan_places_master.csv"))
    parser.add_argument("--output", type=Path, default=Path("data/maps/control_points/1937_to_osm_control_points.csv"))
    args = parser.parse_args()

    candidates = json.loads(args.candidates.read_text(encoding="utf-8-sig"))["candidates"]
    master_rows = {}
    if args.master.exists():
        with args.master.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                master_rows[row["name"]] = row

    selected = []
    for candidate in sorted(candidates, key=lambda item: item.get("quality", 0), reverse=True):
        text = candidate["text"]
        if text not in PRIORITY_NAMES and candidate.get("quality", 0) < 0.76:
            continue
        if len(selected) >= 35 and text not in PRIORITY_NAMES:
            continue
        bbox = candidate["bbox_pixel"]
        pixel_x = (float(bbox[0]) + float(bbox[2])) / 2.0
        pixel_y = (float(bbox[1]) + float(bbox[3])) / 2.0
        master = master_rows.get(text, {})
        selected.append(
            {
                "control_id": f"cp_{len(selected) + 1:03d}",
                "enabled": "false",
                "name": text,
                "role": candidate.get("category", ""),
                "pixel_x": f"{pixel_x:.3f}",
                "pixel_y": f"{pixel_y:.3f}",
                "map_x": master.get("x", ""),
                "map_y": master.get("y", ""),
                "source_ocr_id": candidate.get("ocr_id", ""),
                "source_text": candidate.get("ocr_text_raw_order") or text,
                "ocr_confidence": candidate.get("confidence", ""),
                "osm_reference": "standard_place_exact_match" if master else "",
                "weight": "1.0",
                "notes": "Fill map_x/map_y from OSM/QGIS and set enabled=true only after manual verification.",
            }
        )

    # Add a few blank structural anchors that are often better than OCR labels.
    for name, role in [
        ("西湖东北岸线控制点", "shoreline"),
        ("西湖东南岸线控制点", "shoreline"),
        ("钱塘江北岸控制点", "shoreline"),
        ("北城墙西角控制点", "wall_corner"),
        ("北城墙东角控制点", "wall_corner"),
        ("东城墙中段控制点", "wall"),
    ]:
        selected.append(
            {
                "control_id": f"cp_{len(selected) + 1:03d}",
                "enabled": "false",
                "name": name,
                "role": role,
                "pixel_x": "",
                "pixel_y": "",
                "map_x": "",
                "map_y": "",
                "source_ocr_id": "",
                "source_text": "",
                "ocr_confidence": "",
                "osm_reference": "",
                "weight": "1.0",
                "notes": "Optional structural control point. Pick pixel on 1937 source image and map coordinate on OSM.",
            }
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(selected)
    print(f"wrote {len(selected)} control point candidates -> {args.output}")


if __name__ == "__main__":
    main()
