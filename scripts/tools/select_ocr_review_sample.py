#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Select a spatially balanced review sample from a full OCR/AI candidate file."""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any


DEFAULT_PRIORITY_CATEGORIES = [
    "城门",
    "宫城",
    "道路",
    "水体",
    "山体",
    "桥梁",
    "寺观",
    "衙署",
    "坊巷",
    "市场",
]

CONFIDENCE_SCORE = {
    "high": 3,
    "medium": 2,
    "low": 1,
}


def slug(value: str) -> str:
    text = re.sub(r"[^0-9A-Za-z_\-]+", "_", value.strip())
    return text.strip("_") or "map"


def load_payload(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        meta = {"map_id": path.stem.replace("_text_candidates", "")}
        return meta, payload
    if isinstance(payload, dict):
        return payload, list(payload.get("candidates", []))
    raise ValueError("Candidate JSON must be a list or an object with a candidates list")


def candidate_name(candidate: dict[str, Any]) -> str:
    return str(candidate.get("text") or candidate.get("name") or "").strip()


def bbox_center(candidate: dict[str, Any]) -> tuple[float, float] | None:
    bbox = candidate.get("bbox_pixel")
    if not bbox or len(bbox) != 4:
        return None
    x1, y1, x2, y2 = [float(value) for value in bbox]
    return (x1 + x2) / 2.0, (y1 + y2) / 2.0


def candidate_center(candidate: dict[str, Any]) -> tuple[float, float] | None:
    center = bbox_center(candidate)
    if center is not None:
        return center
    if "x" in candidate and "y" in candidate:
        return float(candidate["x"]), float(candidate["y"])
    if "map_x" in candidate and "map_y" in candidate:
        return float(candidate["map_x"]), float(candidate["map_y"])
    return None


def candidate_score(candidate: dict[str, Any], priority_categories: list[str]) -> tuple[int, int, int, str]:
    category = str(candidate.get("category") or "其他")
    priority = len(priority_categories) - priority_categories.index(category) if category in priority_categories else 0
    confidence = CONFIDENCE_SCORE.get(str(candidate.get("confidence") or "").lower(), 0)
    has_center = 1 if candidate_center(candidate) is not None else 0
    return priority, confidence, has_center, candidate_name(candidate)


def bounds(candidates: list[dict[str, Any]]) -> tuple[float, float, float, float] | None:
    centers = [candidate_center(candidate) for candidate in candidates]
    centers = [center for center in centers if center is not None]
    if not centers:
        return None
    xs = [center[0] for center in centers]
    ys = [center[1] for center in centers]
    return min(xs), min(ys), max(xs), max(ys)


def grid_cell(
    candidate: dict[str, Any],
    extent: tuple[float, float, float, float],
    cols: int,
    rows: int,
) -> tuple[int, int] | None:
    center = candidate_center(candidate)
    if center is None:
        return None
    min_x, min_y, max_x, max_y = extent
    width = max(max_x - min_x, 1e-9)
    height = max(max_y - min_y, 1e-9)
    col = min(cols - 1, max(0, int((center[0] - min_x) / width * cols)))
    row = min(rows - 1, max(0, int((center[1] - min_y) / height * rows)))
    return col, row


def add_candidate(
    selected: list[dict[str, Any]],
    selected_keys: set[tuple[str, str]],
    candidate: dict[str, Any],
) -> bool:
    key = (candidate.get("place_id") or "", candidate_name(candidate))
    if key in selected_keys:
        return False
    selected.append(candidate)
    selected_keys.add(key)
    return True


def select_sample(
    candidates: list[dict[str, Any]],
    sample_size: int,
    priority_categories: list[str],
    forced_names: set[str],
    cols: int,
    rows: int,
) -> list[dict[str, Any]]:
    clean = [candidate for candidate in candidates if candidate_name(candidate)]
    ranked = sorted(clean, key=lambda item: candidate_score(item, priority_categories), reverse=True)

    selected: list[dict[str, Any]] = []
    selected_keys: set[tuple[str, str]] = set()

    for candidate in ranked:
        if candidate_name(candidate) in forced_names:
            add_candidate(selected, selected_keys, candidate)
    if len(selected) >= sample_size:
        return selected[:sample_size]

    for category in priority_categories:
        for candidate in ranked:
            if str(candidate.get("category") or "其他") == category:
                if add_candidate(selected, selected_keys, candidate):
                    break
        if len(selected) >= sample_size:
            return selected

    extent = bounds(clean)
    if extent is not None:
        by_cell: dict[tuple[int, int], list[dict[str, Any]]] = {}
        for candidate in ranked:
            cell = grid_cell(candidate, extent, cols, rows)
            if cell is not None:
                by_cell.setdefault(cell, []).append(candidate)
        for row in range(rows):
            for col in range(cols):
                for candidate in by_cell.get((col, row), []):
                    if add_candidate(selected, selected_keys, candidate):
                        break
                if len(selected) >= sample_size:
                    return selected

    for candidate in ranked:
        add_candidate(selected, selected_keys, candidate)
        if len(selected) >= sample_size:
            return selected

    return selected


def make_output_payload(
    source_meta: dict[str, Any],
    source_path: Path,
    selected: list[dict[str, Any]],
    total_count: int,
    sample_size: int,
    priority_categories: list[str],
) -> dict[str, Any]:
    map_id = source_meta.get("map_id") or source_path.stem.replace("_text_candidates", "")
    payload = {
        key: value
        for key, value in source_meta.items()
        if key not in {"candidates", "sample_of", "sample_strategy"}
    }
    payload["map_id"] = map_id
    payload["sample_of"] = source_path.as_posix()
    payload["sample_strategy"] = {
        "requested_sample_size": sample_size,
        "selected_count": len(selected),
        "total_candidates": total_count,
        "priority_categories": priority_categories,
        "purpose": "coordinate_and_layer_review_before_full_import",
    }
    payload["candidates"] = selected
    return payload


def write_report(
    path: Path,
    map_id: str,
    selected: list[dict[str, Any]],
    total_count: int,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# {map_id} 抽样导入检查",
        "",
        f"- 全量候选数：{total_count}",
        f"- 抽样候选数：{len(selected)}",
        "",
        "| 序号 | 地名 | 类别 | 置信度 | 像素中心 |",
        "| ---: | --- | --- | --- | --- |",
    ]
    for index, candidate in enumerate(selected, start=1):
        center = candidate_center(candidate)
        center_text = "" if center is None else f"{center[0]:.1f}, {center[1]:.1f}"
        lines.append(
            f"| {index} | {candidate_name(candidate)} | {candidate.get('category', '')} | "
            f"{candidate.get('confidence', '')} | {center_text} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--sample-size", type=int, default=12)
    parser.add_argument("--grid-cols", type=int, default=3)
    parser.add_argument("--grid-rows", type=int, default=3)
    parser.add_argument("--priority-categories", default=",".join(DEFAULT_PRIORITY_CATEGORIES))
    parser.add_argument("--force-names", default="", help="Comma-separated names that must be included if present.")
    args = parser.parse_args()

    meta, candidates = load_payload(args.candidates)
    map_id = meta.get("map_id") or args.candidates.stem.replace("_text_candidates", "")
    priority_categories = [item.strip() for item in args.priority_categories.split(",") if item.strip()]
    forced_names = {item.strip() for item in args.force_names.split(",") if item.strip()}

    selected = select_sample(
        candidates,
        sample_size=args.sample_size,
        priority_categories=priority_categories,
        forced_names=forced_names,
        cols=args.grid_cols,
        rows=args.grid_rows,
    )

    output = args.output or Path("data/ocr/samples") / f"{slug(map_id)}_review_sample_{len(selected)}.json"
    report = args.report or Path("data/ocr/samples") / f"{slug(map_id)}_review_sample_{len(selected)}.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = make_output_payload(meta, args.candidates, selected, len(candidates), args.sample_size, priority_categories)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(report, map_id, selected, len(candidates))

    print(f"selected {len(selected)} of {len(candidates)} candidates from {map_id}")
    print(output)
    print(report)


if __name__ == "__main__":
    main()
