#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Export georeference control-point CSV to editable GeoJSON layers."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def truthy(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "enabled", "\u662f", "\u542f\u7528"}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def as_float(row: dict[str, str], key: str) -> float | None:
    try:
        value = str(row.get(key, "")).strip()
        return float(value) if value else None
    except ValueError:
        return None


def props_for(row: dict[str, str], space: str) -> dict[str, Any]:
    keep = [
        "control_id",
        "enabled",
        "map_id",
        "name",
        "matched_standard_name",
        "match_type",
        "match_score",
        "role",
        "source_ocr_id",
        "source_text",
        "candidate_texts",
        "ocr_confidence",
        "quality",
        "osm_reference",
        "weight",
        "notes",
    ]
    props = {key: row.get(key, "") for key in keep}
    props["enabled_bool"] = truthy(row.get("enabled", ""))
    props["control_space"] = space
    return props


def feature(row: dict[str, str], x: float, y: float, space: str) -> dict[str, Any]:
    return {
        "type": "Feature",
        "properties": props_for(row, space),
        "geometry": {
            "type": "Point",
            "coordinates": [round(x, 3), round(y, 3)],
        },
    }


def collection(name: str, features: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "type": "FeatureCollection",
        "name": name,
        "crs": {"type": "name", "properties": {"name": "EPSG:3857"}},
        "features": features,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--control-points", type=Path, required=True)
    parser.add_argument("--image-output", type=Path, required=True)
    parser.add_argument("--osm-output", type=Path, required=True)
    args = parser.parse_args()

    rows = read_rows(args.control_points)
    image_features = []
    osm_features = []
    for row in rows:
        pixel_x = as_float(row, "pixel_x")
        pixel_y = as_float(row, "pixel_y")
        map_x = as_float(row, "map_x")
        map_y = as_float(row, "map_y")
        if pixel_x is not None and pixel_y is not None:
            image_features.append(feature(row, pixel_x, -pixel_y, "image_pixel"))
        if map_x is not None and map_y is not None:
            osm_features.append(feature(row, map_x, map_y, "osm_epsg3857"))

    args.image_output.parent.mkdir(parents=True, exist_ok=True)
    args.osm_output.parent.mkdir(parents=True, exist_ok=True)
    args.image_output.write_text(
        json.dumps(collection(args.image_output.stem, image_features), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    args.osm_output.write_text(
        json.dumps(collection(args.osm_output.stem, osm_features), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"image control points: {len(image_features)} -> {args.image_output}")
    print(f"osm control points: {len(osm_features)} -> {args.osm_output}")


if __name__ == "__main__":
    main()
