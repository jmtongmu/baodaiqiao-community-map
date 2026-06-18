#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create a standard place table from the current Lin'an POC CSV."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


DEFAULT_INPUT = Path("data/places/linan_places_v4_osm_yfix.csv")
DEFAULT_RULES = Path("data/config/layer_rules.csv")
DEFAULT_OUTPUT = Path("data/places/linan_places_standard_v1.csv")

FIELDS = [
    "place_id",
    "name",
    "category",
    "target_layer",
    "display_layer",
    "qgis_geometry",
    "semantic_geometry",
    "geometry_level",
    "x",
    "y",
    "confidence",
    "version",
    "source_map",
    "source_stage",
    "reference_logic",
    "notes",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def load_rules(path: Path) -> dict[str, dict[str, str]]:
    return {row["category"]: row for row in read_csv(path)}


def standardize(raw_places: list[dict[str, str]], rules: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    fallback = rules["其他"]
    rows = []
    for index, place in enumerate(raw_places, start=1):
        rule = rules.get(place.get("Category", ""), fallback)
        rows.append(
            {
                "place_id": f"linan_v4_{index:03d}",
                "name": place.get("Name", "").strip(),
                "category": place.get("Category", "其他").strip() or "其他",
                "target_layer": rule["target_layer"],
                "display_layer": rule["display_name"],
                "qgis_geometry": rule["qgis_geometry"],
                "semantic_geometry": rule["semantic_geometry"],
                "geometry_level": rule["geometry_level"],
                "x": place.get("X", "").strip(),
                "y": place.get("Y", "").strip(),
                "confidence": place.get("Confidence", "").strip(),
                "version": "v4_osm_yfix",
                "source_map": "jingchengtu;linan_reference;qgis_poc",
                "source_stage": "ai_spatial_reasoning_poc",
                "reference_logic": place.get("Reference_Logic", "").strip(),
                "notes": "",
            }
        )
    return rows


def write_csv(rows: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--rules", type=Path, default=DEFAULT_RULES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    rules = load_rules(args.rules)
    raw_places = read_csv(args.input)
    rows = standardize(raw_places, rules)
    write_csv(rows, args.output)
    print(f"standardized {len(rows)} places")
    print(args.output)


if __name__ == "__main__":
    main()
