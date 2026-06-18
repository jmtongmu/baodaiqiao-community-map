#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fit an affine transform from old-map image pixels to map coordinates."""

from __future__ import annotations

import argparse
import csv
import json
import math
import shutil
import statistics
from pathlib import Path
from typing import Any


def truthy(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "是", "启用", "enabled"}


def read_control_points(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    points = []
    for row in rows:
        if row.get("enabled") and not truthy(row["enabled"]):
            continue
        try:
            px = float(row.get("pixel_x", ""))
            py = float(row.get("pixel_y", ""))
            mx = float(row.get("map_x", ""))
            my = float(row.get("map_y", ""))
        except ValueError:
            continue
        points.append(
            {
                "id": row.get("control_id", ""),
                "name": row.get("name", ""),
                "pixel": [px, py],
                "map": [mx, my],
                "weight": float(row.get("weight") or 1.0),
                "source_ocr_id": row.get("source_ocr_id", ""),
                "osm_reference": row.get("osm_reference", ""),
                "notes": row.get("notes", ""),
            }
        )
    return points


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
        raise ValueError("At least 3 enabled control points are required")

    normal = [[0.0, 0.0, 0.0] for _ in range(3)]
    rhs_x = [0.0, 0.0, 0.0]
    rhs_y = [0.0, 0.0, 0.0]

    for point in control_points:
        px, py = point["pixel"]
        mx, my = point["map"]
        weight = float(point.get("weight") or 1.0)
        row = [1.0, float(px), float(py)]
        for i in range(3):
            rhs_x[i] += weight * row[i] * float(mx)
            rhs_y[i] += weight * row[i] * float(my)
            for j in range(3):
                normal[i][j] += weight * row[i] * row[j]

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


def pixel_to_map(px: float, py: float, transform: dict[str, float]) -> tuple[float, float]:
    x = transform["x_origin"] + px * transform["pixel_width"] + py * transform["x_rotation"]
    y = transform["y_origin"] + px * transform["y_rotation"] + py * transform["pixel_height"]
    return x, y


def quality_report(control_points: list[dict[str, Any]], transform: dict[str, float]) -> dict[str, Any]:
    residuals = []
    for point in control_points:
        px, py = point["pixel"]
        expected_x, expected_y = point["map"]
        actual_x, actual_y = pixel_to_map(px, py, transform)
        dx = actual_x - expected_x
        dy = actual_y - expected_y
        error = math.hypot(dx, dy)
        residuals.append(
            {
                "id": point.get("id", ""),
                "name": point.get("name", ""),
                "pixel": [round(px, 3), round(py, 3)],
                "map": [round(expected_x, 3), round(expected_y, 3)],
                "fitted_map": [round(actual_x, 3), round(actual_y, 3)],
                "dx_m": round(dx, 3),
                "dy_m": round(dy, 3),
                "error_m": round(error, 3),
                "weight": point.get("weight", 1.0),
                "source_ocr_id": point.get("source_ocr_id", ""),
                "osm_reference": point.get("osm_reference", ""),
                "notes": point.get("notes", ""),
            }
        )
    errors = [row["error_m"] for row in residuals]
    rmse = math.sqrt(sum(error * error for error in errors) / len(errors)) if errors else None
    return {
        "control_point_count": len(control_points),
        "rmse_m": round(rmse, 3) if rmse is not None else None,
        "mean_error_m": round(statistics.mean(errors), 3) if errors else None,
        "max_error_m": max(errors) if errors else None,
        "residuals": residuals,
    }


def world_file_text(transform: dict[str, float]) -> str:
    a = transform["pixel_width"]
    d = transform["y_rotation"]
    b = transform["x_rotation"]
    e = transform["pixel_height"]
    c = transform["x_origin"] + 0.5 * a + 0.5 * b
    f = transform["y_origin"] + 0.5 * d + 0.5 * e
    return f"{a:.12f}\n{d:.12f}\n{b:.12f}\n{e:.12f}\n{c:.12f}\n{f:.12f}\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--map-id", default="1937")
    parser.add_argument("--control-points", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("data/maps/transforms/1937_pixel_to_osm.json"))
    parser.add_argument("--crs", default="EPSG:3857")
    parser.add_argument("--max-rmse-m", type=float, default=60.0)
    parser.add_argument("--max-point-error-m", type=float, default=120.0)
    parser.add_argument("--image", type=Path)
    parser.add_argument("--georef-image-output", type=Path, default=Path("qgis/georef/1937_osm_affine.jpg"))
    args = parser.parse_args()

    control_points = read_control_points(args.control_points)
    transform = solve_affine(control_points)
    quality = quality_report(control_points, transform)
    accepted = (
        quality["rmse_m"] is not None
        and quality["rmse_m"] <= args.max_rmse_m
        and quality["max_error_m"] is not None
        and quality["max_error_m"] <= args.max_point_error_m
    )

    payload = {
        "map_id": args.map_id,
        "crs": args.crs,
        "method": "affine_pixel_to_map",
        "pixel_space": f"{args.map_id}_original_image_pixels",
        "coefficients": transform,
        "accuracy": {
            **quality,
            "accepted": accepted,
            "max_rmse_threshold_m": args.max_rmse_m,
            "max_point_error_threshold_m": args.max_point_error_m,
        },
        "control_points": control_points,
        "notes": f"Fitted from original {args.map_id} image pixel coordinates to OSM/EPSG:3857 map coordinates.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.image:
        args.georef_image_output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(args.image, args.georef_image_output)
        world_path = args.georef_image_output.with_suffix(".jgw")
        world_path.write_text(world_file_text(transform), encoding="ascii")
        payload["georef_image"] = args.georef_image_output.as_posix()
        payload["georef_world_file"] = world_path.as_posix()
        args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"control points: {len(control_points)}")
    print(f"rmse_m: {quality['rmse_m']} max_error_m: {quality['max_error_m']} accepted: {accepted}")
    print(args.output)


if __name__ == "__main__":
    main()
