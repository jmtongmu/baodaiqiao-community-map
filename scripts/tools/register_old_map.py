#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Register a new old-map image and create import templates."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from pathlib import Path


MAP_FIELDS = ["map_id", "title", "file_path", "map_type", "crs", "status", "notes"]
DEFAULT_MAPS_CSV = Path("data/maps/maps.csv")


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=MAP_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in MAP_FIELDS})


def upsert_map(path: Path, new_row: dict[str, str]) -> None:
    rows = [row for row in read_rows(path) if row.get("map_id") != new_row["map_id"]]
    rows.append(new_row)
    write_rows(path, rows)


def write_json_template(path: Path, payload: dict, force: bool) -> None:
    if path.exists() and not force:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--map-id", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--source", type=Path, required=True, help="Source image path.")
    parser.add_argument("--maps-csv", type=Path, default=DEFAULT_MAPS_CSV)
    parser.add_argument("--assets-dir", type=Path, default=Path("assets/maps"))
    parser.add_argument("--copy", action="store_true", help="Copy source image into assets/maps.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing templates.")
    parser.add_argument("--notes", default="")
    args = parser.parse_args()

    source = args.source
    if not source.exists():
        raise FileNotFoundError(source)

    if args.copy:
        args.assets_dir.mkdir(parents=True, exist_ok=True)
        target = args.assets_dir / f"{args.map_id}{source.suffix.lower()}"
        if target.exists() and not args.force:
            raise FileExistsError(f"{target} already exists; pass --force to overwrite")
        shutil.copy2(source, target)
        file_path = target.as_posix()
    else:
        file_path = source.as_posix()

    upsert_map(
        args.maps_csv,
        {
            "map_id": args.map_id,
            "title": args.title,
            "file_path": file_path,
            "map_type": "source_image",
            "crs": "",
            "status": "raw",
            "notes": args.notes,
        },
    )

    candidate_path = Path("data/ocr") / f"{args.map_id}_text_candidates.json"
    transform_path = Path("data/maps/transforms") / f"{args.map_id}_pixel_to_map.json"

    write_json_template(
        candidate_path,
        {
            "map_id": args.map_id,
            "image_file": file_path,
            "crs": "EPSG:3857",
            "candidates": [
                {
                    "text": "示例地名",
                    "category": "其他",
                    "bbox_pixel": [0, 0, 100, 40],
                    "orientation": "horizontal",
                    "confidence": "medium",
                    "reference_logic": "填写 AI/OCR 或人工判断的空间依据",
                    "notes": "",
                }
            ],
        },
        args.force,
    )

    write_json_template(
        transform_path,
        {
            "map_id": args.map_id,
            "crs": "EPSG:3857",
            "method": "affine_pixel_to_map",
            "pixel_space": "ocr_image_pixels",
            "coefficients": {
                "x_origin": None,
                "pixel_width": None,
                "x_rotation": 0,
                "y_origin": None,
                "y_rotation": 0,
                "pixel_height": None,
            },
            "accuracy": {
                "rmse_m": None,
                "max_error_m": None,
                "control_point_count": 0,
                "accepted": False
            },
            "control_points": [],
            "control_point_template": [
                {
                    "name": "示例控制点",
                    "pixel": [0, 0],
                    "map": [0, 0],
                    "notes": "pixel 必须来自 OCR 使用的同一张图；map 必须是 EPSG:3857 坐标"
                }
            ],
            "notes": "强烈建议用 OCR 所用原图的像素坐标 + 同一批控制点求转换；不要把原图 OCR 框直接套用到已重采样的配准栅格。",
        },
        args.force,
    )

    print(f"registered map: {args.map_id}")
    print(args.maps_csv)
    print(candidate_path)
    print(transform_path)


if __name__ == "__main__":
    main()
