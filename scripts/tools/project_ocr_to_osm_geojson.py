#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Project OCR boxes from image pixels to OSM/EPSG:3857 using a transform."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_transform(path: Path) -> dict[str, float]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    accuracy = payload.get("accuracy") or {}
    if accuracy.get("accepted") is False:
        raise RuntimeError(
            f"Transform accuracy is not accepted: rmse={accuracy.get('rmse_m')} "
            f"max_error={accuracy.get('max_error_m')}"
        )
    coeffs = payload.get("coefficients") or {}
    required = ["x_origin", "pixel_width", "x_rotation", "y_origin", "y_rotation", "pixel_height"]
    if any(coeffs.get(key) is None for key in required):
        raise RuntimeError(f"Transform is missing coefficients: {path}")
    return {key: float(coeffs[key]) for key in required}


def pixel_to_map(px: float, py: float, transform: dict[str, float]) -> list[float]:
    return [
        transform["x_origin"] + px * transform["pixel_width"] + py * transform["x_rotation"],
        transform["y_origin"] + px * transform["y_rotation"] + py * transform["pixel_height"],
    ]


def candidate_quad(candidate: dict[str, Any]) -> list[list[float]]:
    if candidate.get("quad_pixel"):
        return [[float(p[0]), float(p[1])] for p in candidate["quad_pixel"]]
    x1, y1, x2, y2 = [float(value) for value in candidate["bbox_pixel"]]
    return [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]


def properties_for(candidate: dict[str, Any]) -> dict[str, Any]:
    keep = [
        "ocr_id",
        "text",
        "ocr_text_raw_order",
        "reading_rule",
        "raw_text",
        "category",
        "confidence",
        "quality",
        "orientation",
        "source_map",
        "source_stage",
        "engine",
        "ocr_variant",
        "ocr_pass",
        "alternative_texts",
        "alternative_count",
        "reference_logic",
        "notes",
    ]
    return {key: candidate.get(key, "") for key in keep}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", type=Path, default=Path("data/ocr/1937_rapidocr_text_candidates.json"))
    parser.add_argument("--transform", type=Path, default=Path("data/maps/transforms/1937_pixel_to_osm.json"))
    parser.add_argument("--polygon-output", type=Path, default=Path("data/ocr/osm_space/1937_rapidocr_osm_boxes.geojson"))
    parser.add_argument("--point-output", type=Path, default=Path("data/ocr/osm_space/1937_rapidocr_osm_points.geojson"))
    parser.add_argument("--allow-unaccepted-transform", action="store_true")
    args = parser.parse_args()

    if args.allow_unaccepted_transform:
        payload = json.loads(args.transform.read_text(encoding="utf-8-sig"))
        coeffs = payload["coefficients"]
        transform = {key: float(coeffs[key]) for key in coeffs}
    else:
        transform = load_transform(args.transform)

    payload = json.loads(args.candidates.read_text(encoding="utf-8-sig"))
    map_id = payload.get("map_id") or args.candidates.stem
    polygon_features = []
    point_features = []
    for candidate in payload.get("candidates", []):
        if not candidate.get("bbox_pixel"):
            continue
        quad = candidate_quad(candidate)
        map_quad = [pixel_to_map(px, py, transform) for px, py in quad]
        map_quad.append(map_quad[0])
        x1, y1, x2, y2 = [float(value) for value in candidate["bbox_pixel"]]
        center = pixel_to_map((x1 + x2) / 2.0, (y1 + y2) / 2.0, transform)
        props = properties_for(candidate)
        props.update(
            {
                "map_x": round(center[0], 3),
                "map_y": round(center[1], 3),
                "pixel_x1": x1,
                "pixel_y1": y1,
                "pixel_x2": x2,
                "pixel_y2": y2,
            }
        )
        polygon_features.append(
            {
                "type": "Feature",
                "properties": props,
                "geometry": {"type": "Polygon", "coordinates": [[list(map(lambda v: round(v, 3), p)) for p in map_quad]]},
            }
        )
        point_features.append(
            {
                "type": "Feature",
                "properties": props,
                "geometry": {"type": "Point", "coordinates": [round(center[0], 3), round(center[1], 3)]},
            }
        )

    crs = {"type": "name", "properties": {"name": "EPSG:3857"}}
    polygon_collection = {"type": "FeatureCollection", "name": f"{map_id}_osm_boxes", "crs": crs, "features": polygon_features}
    point_collection = {"type": "FeatureCollection", "name": f"{map_id}_osm_points", "crs": crs, "features": point_features}
    args.polygon_output.parent.mkdir(parents=True, exist_ok=True)
    args.point_output.parent.mkdir(parents=True, exist_ok=True)
    args.polygon_output.write_text(json.dumps(polygon_collection, ensure_ascii=False, indent=2), encoding="utf-8")
    args.point_output.write_text(json.dumps(point_collection, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {len(polygon_features)} polygons -> {args.polygon_output}")
    print(f"wrote {len(point_features)} points -> {args.point_output}")


if __name__ == "__main__":
    main()
