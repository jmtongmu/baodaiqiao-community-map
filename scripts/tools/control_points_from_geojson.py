#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Update georeference control-point CSV from edited GeoJSON layers."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any


def truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "enabled", "\u662f", "\u542f\u7528"}


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def read_features(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    features = {}
    for item in payload.get("features", []):
        props = item.get("properties") or {}
        control_id = str(props.get("control_id") or "").strip()
        coords = ((item.get("geometry") or {}).get("coordinates") or [])
        if control_id and len(coords) >= 2:
            features[control_id] = {"properties": props, "x": float(coords[0]), "y": float(coords[1])}
    return features


def update_attrs(row: dict[str, str], props: dict[str, Any]) -> None:
    for key in [
        "enabled",
        "name",
        "matched_standard_name",
        "match_type",
        "match_score",
        "role",
        "weight",
        "notes",
    ]:
        if key in props and props[key] is not None:
            row[key] = str(props[key])
    if "enabled_bool" in props:
        row["enabled"] = "true" if truthy(props["enabled_bool"]) else str(row.get("enabled", "false"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--control-points", type=Path, required=True)
    parser.add_argument("--image-input", type=Path, required=True)
    parser.add_argument("--osm-input", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    fields, rows = read_csv(args.control_points)
    output = args.output or args.control_points
    image_features = read_features(args.image_input)
    osm_features = read_features(args.osm_input)

    updated_image = 0
    updated_osm = 0
    updated_enabled = 0
    for row in rows:
        control_id = str(row.get("control_id") or "").strip()
        image = image_features.get(control_id)
        osm = osm_features.get(control_id)
        if image:
            row["pixel_x"] = f"{image['x']:.3f}"
            row["pixel_y"] = f"{-image['y']:.3f}"
            update_attrs(row, image["properties"])
            updated_image += 1
        if osm:
            row["map_x"] = f"{osm['x']:.3f}"
            row["map_y"] = f"{osm['y']:.3f}"
            before = row.get("enabled", "")
            update_attrs(row, osm["properties"])
            if row.get("enabled", "") != before:
                updated_enabled += 1
            updated_osm += 1

    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with output.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
    except PermissionError:
        pending = output.with_name(output.stem + ".pending.csv")
        with pending.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        print(f"could not overwrite locked CSV: {output}")
        print(f"wrote pending CSV instead: {pending}")
        print("close Excel/QGIS/file preview handles, then rerun the sync or replace the CSV with the pending file.")
        sys.exit(4)

    print(f"updated image controls: {updated_image}")
    print(f"updated osm controls: {updated_osm}")
    print(f"enabled updates from properties: {updated_enabled}")
    print(output)


if __name__ == "__main__":
    main()
