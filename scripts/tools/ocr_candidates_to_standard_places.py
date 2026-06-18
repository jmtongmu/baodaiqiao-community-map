#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Convert OCR/AI text candidates into the standard Lin'an place table."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics
from pathlib import Path
from typing import Any


STANDARD_FIELDS = [
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


def slug(value: str) -> str:
    text = re.sub(r"[^0-9A-Za-z_\-]+", "_", value.strip())
    return text.strip("_") or "map"


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(rows: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=STANDARD_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def load_rules(path: Path) -> dict[str, dict[str, str]]:
    rows = read_csv(path)
    return {row["category"]: row for row in rows}


def load_candidates(path: Path) -> tuple[str, list[dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(payload, list):
        return path.stem.replace("_text_candidates", ""), payload
    if isinstance(payload, dict):
        return payload.get("map_id") or path.stem.replace("_text_candidates", ""), payload.get("candidates", [])
    raise ValueError("OCR candidate JSON must be a list or an object with a candidates list")


def gaussian_solve(matrix: list[list[float]], values: list[float]) -> list[float]:
    size = len(values)
    aug = [row[:] + [values[index]] for index, row in enumerate(matrix)]
    for col in range(size):
        pivot = max(range(col, size), key=lambda row: abs(aug[row][col]))
        if abs(aug[pivot][col]) < 1e-12:
            raise ValueError("Control points are not sufficient for an affine transform")
        aug[col], aug[pivot] = aug[pivot], aug[col]
        pivot_value = aug[col][col]
        aug[col] = [value / pivot_value for value in aug[col]]
        for row in range(size):
            if row == col:
                continue
            factor = aug[row][col]
            aug[row] = [value - factor * aug[col][i] for i, value in enumerate(aug[row])]
    return [aug[row][-1] for row in range(size)]


def solve_affine(control_points: list[dict[str, Any]]) -> dict[str, float]:
    if len(control_points) < 3:
        raise ValueError("At least 3 control points are required")

    normal = [[0.0, 0.0, 0.0] for _ in range(3)]
    rhs_x = [0.0, 0.0, 0.0]
    rhs_y = [0.0, 0.0, 0.0]

    for point in control_points:
        px, py = point["pixel"]
        mx, my = point["map"]
        row = [1.0, float(px), float(py)]
        for i in range(3):
            rhs_x[i] += row[i] * float(mx)
            rhs_y[i] += row[i] * float(my)
            for j in range(3):
                normal[i][j] += row[i] * row[j]

    x_coeffs = gaussian_solve(normal, rhs_x)
    y_coeffs = gaussian_solve(normal, rhs_y)
    return {
        "x_origin": x_coeffs[0],
        "pixel_width": x_coeffs[1],
        "x_rotation": x_coeffs[2],
        "y_origin": y_coeffs[0],
        "y_rotation": y_coeffs[1],
        "pixel_height": y_coeffs[2],
    }


def usable_control_points(control_points: list[dict[str, Any]]) -> list[dict[str, Any]]:
    usable = []
    for point in control_points:
        pixel = point.get("pixel")
        mapped = point.get("map")
        if not pixel or not mapped or len(pixel) != 2 or len(mapped) != 2:
            continue
        try:
            float(pixel[0])
            float(pixel[1])
            float(mapped[0])
            float(mapped[1])
        except (TypeError, ValueError):
            continue
        usable.append(point)
    return usable


def pixel_to_map(px: float, py: float, transform: dict[str, float]) -> tuple[float, float]:
    x = transform["x_origin"] + px * transform["pixel_width"] + py * transform["x_rotation"]
    y = transform["y_origin"] + px * transform["y_rotation"] + py * transform["pixel_height"]
    return x, y


def transform_quality(control_points: list[dict[str, Any]], transform: dict[str, float]) -> dict[str, Any]:
    residuals = []
    for point in control_points:
        px, py = point["pixel"]
        expected_x, expected_y = point["map"]
        actual_x, actual_y = pixel_to_map(float(px), float(py), transform)
        dx = actual_x - float(expected_x)
        dy = actual_y - float(expected_y)
        error = math.hypot(dx, dy)
        residuals.append(
            {
                "name": point.get("name", ""),
                "pixel": point["pixel"],
                "map": point["map"],
                "dx_m": round(dx, 3),
                "dy_m": round(dy, 3),
                "error_m": round(error, 3),
            }
        )

    errors = [item["error_m"] for item in residuals]
    rmse = math.sqrt(sum(error * error for error in errors) / len(errors)) if errors else None
    mean = statistics.mean(errors) if errors else None
    return {
        "control_point_count": len(control_points),
        "rmse_m": round(rmse, 3) if rmse is not None else None,
        "mean_error_m": round(mean, 3) if mean is not None else None,
        "max_error_m": max(errors) if errors else None,
        "residuals": residuals,
    }


def load_transform(path: Path | None) -> tuple[dict[str, float] | None, dict[str, Any]]:
    if path is None or not path.exists():
        return None, {"status": "missing"}
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    quality: dict[str, Any] = {
        "status": "loaded",
        "source": str(path),
        "method": payload.get("method", ""),
        "pixel_space": payload.get("pixel_space", ""),
        "notes": payload.get("notes", ""),
    }
    coeffs = payload.get("coefficients")
    if coeffs and coeffs.get("x_origin") is not None and coeffs.get("pixel_width") is not None:
        transform = {key: float(coeffs.get(key) or 0.0) for key in [
            "x_origin",
            "pixel_width",
            "x_rotation",
            "y_origin",
            "y_rotation",
            "pixel_height",
        ]}
        control_points = usable_control_points(payload.get("control_points") or [])
        if control_points:
            quality.update(transform_quality(control_points, transform))
        elif payload.get("accuracy"):
            quality.update(payload["accuracy"])
        else:
            quality["status"] = "loaded_without_accuracy"
        return transform, quality
    control_points = usable_control_points(payload.get("control_points") or [])
    if control_points:
        transform = solve_affine(control_points)
        quality.update(transform_quality(control_points, transform))
        return transform, quality
    return None, {"status": "unusable", "source": str(path)}


def bbox_center(candidate: dict[str, Any]) -> tuple[float, float] | None:
    bbox = candidate.get("bbox_pixel")
    if not bbox:
        return None
    if len(bbox) != 4:
        raise ValueError(f"bbox_pixel must have 4 numbers: {bbox}")
    x1, y1, x2, y2 = [float(value) for value in bbox]
    return (x1 + x2) / 2.0, (y1 + y2) / 2.0


def candidate_xy(candidate: dict[str, Any], transform: dict[str, float] | None) -> tuple[float, float]:
    if "x" in candidate and "y" in candidate:
        return float(candidate["x"]), float(candidate["y"])
    if "map_x" in candidate and "map_y" in candidate:
        return float(candidate["map_x"]), float(candidate["map_y"])
    center = bbox_center(candidate)
    if center and transform:
        return pixel_to_map(center[0], center[1], transform)
    raise ValueError(
        f"Candidate {candidate.get('text') or candidate.get('name')!r} needs x/y, map_x/map_y, "
        "or bbox_pixel plus a pixel_to_map transform"
    )


def note_for(candidate: dict[str, Any]) -> str:
    extras = {}
    for key in ["bbox_pixel", "orientation", "ocr_confidence", "notes"]:
        if key in candidate:
            extras[key] = candidate[key]
    if not extras:
        return candidate.get("notes", "")
    return json.dumps(extras, ensure_ascii=False, separators=(",", ":"))


def validate_transform_quality(
    quality: dict[str, Any],
    max_rmse_m: float,
    max_point_error_m: float,
    allow_unsafe_transform: bool,
) -> None:
    if allow_unsafe_transform:
        return

    if quality.get("status") == "missing":
        return

    rmse = quality.get("rmse_m")
    max_error = quality.get("max_error_m")
    control_count = int(quality.get("control_point_count") or 0)

    if quality.get("status") == "loaded_without_accuracy":
        raise RuntimeError(
            "Transform has coefficients but no accuracy report. Add control_points, "
            "or pass --allow-unsafe-transform for a deliberate manual override."
        )
    if control_count and control_count < 3:
        raise RuntimeError("At least 3 control points are required for affine accuracy checks.")
    if rmse is not None and float(rmse) > max_rmse_m:
        raise RuntimeError(f"Transform RMSE {rmse}m exceeds threshold {max_rmse_m}m.")
    if max_error is not None and float(max_error) > max_point_error_m:
        raise RuntimeError(f"Transform max error {max_error}m exceeds threshold {max_point_error_m}m.")


def write_qa_report(path: Path | None, map_id: str, quality: dict[str, Any], row_count: int) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "map_id": map_id,
        "imported_place_count": row_count,
        "transform_quality": quality,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def convert_candidates(
    map_id: str,
    candidates: list[dict[str, Any]],
    rules: dict[str, dict[str, str]],
    transform: dict[str, float] | None,
    version: str,
) -> list[dict[str, str]]:
    fallback = rules["其他"]
    map_slug = slug(map_id)
    rows = []
    for index, candidate in enumerate(candidates, start=1):
        name = str(candidate.get("text") or candidate.get("name") or "").strip()
        if not name:
            continue
        category = str(candidate.get("category") or "其他").strip() or "其他"
        rule = rules.get(category, fallback)
        x, y = candidate_xy(candidate, transform)
        rows.append(
            {
                "place_id": candidate.get("place_id") or f"{map_slug}_{index:03d}",
                "name": name,
                "category": category,
                "target_layer": candidate.get("target_layer") or rule["target_layer"],
                "display_layer": rule["display_name"],
                "qgis_geometry": rule["qgis_geometry"],
                "semantic_geometry": rule["semantic_geometry"],
                "geometry_level": candidate.get("geometry_level") or rule["geometry_level"],
                "x": f"{x:.3f}",
                "y": f"{y:.3f}",
                "confidence": candidate.get("confidence") or "medium",
                "version": version,
                "source_map": candidate.get("source_map") or map_id,
                "source_stage": candidate.get("source_stage") or "ai_ocr_import",
                "reference_logic": candidate.get("reference_logic") or "",
                "notes": note_for(candidate),
            }
        )
    return rows


def merge_master(master_rows: list[dict[str, str]], import_rows: list[dict[str, str]], map_id: str) -> list[dict[str, str]]:
    imported_ids = {row["place_id"] for row in import_rows}
    map_slug = slug(map_id)
    kept = [
        row
        for row in master_rows
        if row.get("place_id") not in imported_ids
        and not row.get("place_id", "").startswith(f"{map_slug}_")
    ]
    return kept + import_rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--rules", type=Path, default=Path("data/config/layer_rules.csv"))
    parser.add_argument("--transform", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--version", default="import_v1")
    parser.add_argument("--update-master", action="store_true")
    parser.add_argument("--master", type=Path, default=Path("data/places/linan_places_master.csv"))
    parser.add_argument("--max-rmse-m", type=float, default=60.0)
    parser.add_argument("--max-point-error-m", type=float, default=120.0)
    parser.add_argument("--allow-unsafe-transform", action="store_true")
    parser.add_argument("--qa-output", type=Path)
    args = parser.parse_args()

    map_id, candidates = load_candidates(args.candidates)
    transform_path = args.transform
    if transform_path is None:
        candidate_transform = Path("data/maps/transforms") / f"{map_id}_pixel_to_map.json"
        transform_path = candidate_transform if candidate_transform.exists() else None

    transform, quality = load_transform(transform_path)
    validate_transform_quality(
        quality,
        max_rmse_m=args.max_rmse_m,
        max_point_error_m=args.max_point_error_m,
        allow_unsafe_transform=args.allow_unsafe_transform,
    )
    rules = load_rules(args.rules)
    rows = convert_candidates(map_id, candidates, rules, transform, args.version)

    output = args.output or Path("data/places/imports") / f"{slug(map_id)}_places_standard.csv"
    write_csv(rows, output)

    qa_output = args.qa_output or Path("data/places/imports") / f"{slug(map_id)}_transform_qa.json"
    write_qa_report(qa_output, map_id, quality, len(rows))

    if args.update_master:
        master_rows = read_csv(args.master)
        write_csv(merge_master(master_rows, rows, map_id), args.master)
        print(f"updated master: {args.master}")

    print(f"converted {len(rows)} candidates from {map_id}")
    print(output)
    print(qa_output)


if __name__ == "__main__":
    main()
