#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract embedded Lin'an place data from a PyQGIS script.

The current POC keeps place records inside a QGIS console script. This helper
turns that embedded list into standalone CSV and GeoJSON files so later AI
iterations can update data without rewriting the whole PyQGIS layer builder.
"""

from __future__ import annotations

import argparse
import ast
import csv
import json
import math
from pathlib import Path
from typing import Any


DEFAULT_SOURCE = Path("scripts/pyqgis/create_linan_places_polygons_embedded_v4_osm_yfix.py")
DEFAULT_CSV = Path("data/places/linan_places_v4_osm_yfix.csv")
DEFAULT_GEOJSON = Path("data/places/linan_places_v4_osm_yfix.geojson")


def extract_literal(source: str, name: str) -> Any:
    tree = ast.parse(source)
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == name:
                return ast.literal_eval(node.value)
    raise ValueError(f"Could not find literal assignment for {name!r}")


def rectangle(x: float, y: float, width: float, height: float) -> list[list[float]]:
    half_width = width / 2.0
    half_height = height / 2.0
    return [
        [x - half_width, y - half_height],
        [x + half_width, y - half_height],
        [x + half_width, y + half_height],
        [x - half_width, y + half_height],
        [x - half_width, y - half_height],
    ]


def circle(x: float, y: float, radius: float, segments: int) -> list[list[float]]:
    return [
        [
            x + radius * math.cos(2 * math.pi * i / segments),
            y + radius * math.sin(2 * math.pi * i / segments),
        ]
        for i in range(segments + 1)
    ]


def geometry_for_place(place: dict[str, Any], category_sizes: dict[str, tuple]) -> dict[str, Any]:
    x = float(place["X"])
    y = float(place["Y"])
    spec = category_sizes.get(place.get("Category"), category_sizes["其他"])
    if spec[0] == "circle":
        coords = circle(x, y, float(spec[1]), int(spec[2]))
    else:
        coords = rectangle(x, y, float(spec[1]), float(spec[2]))
    return {"type": "Polygon", "coordinates": [coords]}


def write_csv(places: list[dict[str, Any]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = ["Name", "Category", "X", "Y", "Confidence", "Reference_Logic"]
    with output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for place in places:
            writer.writerow({field: place.get(field, "") for field in fields})


def write_geojson(places: list[dict[str, Any]], category_sizes: dict[str, tuple], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    features = []
    for index, place in enumerate(places, start=1):
        properties = {
            "id": index,
            "name": place.get("Name"),
            "category": place.get("Category"),
            "x": float(place["X"]),
            "y": float(place["Y"]),
            "confidence": place.get("Confidence"),
            "reference_logic": place.get("Reference_Logic"),
        }
        features.append(
            {
                "type": "Feature",
                "properties": properties,
                "geometry": geometry_for_place(place, category_sizes),
            }
        )

    collection = {
        "type": "FeatureCollection",
        "name": output.stem,
        "crs": {"type": "name", "properties": {"name": "EPSG:3857"}},
        "features": features,
    }
    output.write_text(json.dumps(collection, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--geojson", type=Path, default=DEFAULT_GEOJSON)
    args = parser.parse_args()

    source = args.source.read_text(encoding="utf-8")
    category_sizes = extract_literal(source, "CATEGORY_SIZES")
    places = extract_literal(source, "places")

    write_csv(places, args.csv)
    write_geojson(places, category_sizes, args.geojson)
    print(f"extracted {len(places)} places")
    print(args.csv)
    print(args.geojson)


if __name__ == "__main__":
    main()
