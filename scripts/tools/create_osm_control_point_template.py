#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Create old-map pixel to OSM control-point candidates from OCR names."""

from __future__ import annotations

import argparse
import csv
import difflib
import json
from pathlib import Path
from typing import Any


FIELDS = [
    "control_id",
    "enabled",
    "map_id",
    "name",
    "matched_standard_name",
    "match_type",
    "match_score",
    "role",
    "pixel_x",
    "pixel_y",
    "map_x",
    "map_y",
    "source_ocr_id",
    "source_text",
    "candidate_texts",
    "ocr_confidence",
    "quality",
    "osm_reference",
    "weight",
    "notes",
]

TRAD_TO_SIMP = str.maketrans(
    {
        "門": "门",
        "橋": "桥",
        "寶": "宝",
        "陽": "阳",
        "淨": "净",
        "報": "报",
        "聖": "圣",
        "學": "学",
        "圖": "图",
        "廟": "庙",
        "觀": "观",
        "縣": "县",
        "營": "营",
        "馬": "马",
        "龍": "龙",
        "灣": "湾",
        "錢": "钱",
    }
)

STRUCTURAL_CATEGORIES = {
    "城门",
    "宫城",
    "寺观",
    "山体",
    "水体",
    "桥梁",
    "衙署",
}


def clean_text(value: str) -> str:
    return (
        str(value or "")
        .strip()
        .replace(" ", "")
        .replace("\u3000", "")
        .replace("·", "")
        .replace("。", "")
        .translate(TRAD_TO_SIMP)
    )


def candidate_texts(candidate: dict[str, Any]) -> list[str]:
    values = [
        candidate.get("text", ""),
        candidate.get("ocr_text_raw_order", ""),
        candidate.get("raw_text", ""),
    ]
    alternatives = str(candidate.get("alternative_texts") or "")
    for sep in ["|", ";", ",", "，"]:
        alternatives = alternatives.replace(sep, "|")
    values.extend(alternatives.split("|"))

    seen: set[str] = set()
    result = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def special_match(candidate_norm: str, master_norm: str) -> tuple[str, float] | None:
    if master_norm == "保安门" and ("保安水门" in candidate_norm or candidate_norm == "水安保"):
        return "special_historical_gate", 0.94
    if master_norm == "净慈寺" and candidate_norm.startswith("净慈") and candidate_norm.endswith("寺"):
        return "special寺名夹字", 0.9
    if master_norm == "保俶塔" and ("保" in candidate_norm and "塔" in candidate_norm):
        return "special_partial_tower", 0.78
    if master_norm == "雷峰塔" and ("雷" in candidate_norm and "塔" in candidate_norm):
        return "special_partial_tower", 0.82
    return None


def score_match(candidate_norm: str, master_norm: str, master_category: str) -> tuple[str, float] | None:
    if not candidate_norm or not master_norm:
        return None
    if candidate_norm == master_norm:
        return "normalized_exact", 1.0

    special = special_match(candidate_norm, master_norm)
    if special:
        return special

    if len(master_norm) >= 3 and master_norm in candidate_norm:
        return "contains_standard_name", 0.88
    if (
        master_category in STRUCTURAL_CATEGORIES
        and len(candidate_norm) >= 2
        and candidate_norm in master_norm
    ):
        return "partial_structural_name", 0.84

    ratio = difflib.SequenceMatcher(None, candidate_norm, master_norm).ratio()
    if master_category in STRUCTURAL_CATEGORIES and ratio >= 0.72:
        return "fuzzy_structural_name", round(ratio, 3)
    if ratio >= 0.84 and len(master_norm) >= 3:
        return "fuzzy_name", round(ratio, 3)
    return None


def best_match_for_candidate(
    candidate: dict[str, Any],
    master_rows: list[dict[str, str]],
) -> dict[str, Any] | None:
    best: dict[str, Any] | None = None
    texts = candidate_texts(candidate)
    for source_text in texts:
        candidate_norm = clean_text(source_text)
        for master in master_rows:
            master_norm = clean_text(master.get("name", ""))
            scored = score_match(candidate_norm, master_norm, master.get("category", ""))
            if not scored:
                continue
            match_type, score = scored
            # Avoid weak one-character coincidences unless a special rule caught it.
            if score < 0.86 and not match_type.startswith("special"):
                continue
            current = {
                "source_text": source_text,
                "candidate_texts": " | ".join(texts),
                "standard": master,
                "match_type": match_type,
                "score": score,
            }
            if best is None or (score, len(master_norm)) > (
                best["score"],
                len(clean_text(best["standard"].get("name", ""))),
            ):
                best = current
    return best


def load_candidates(path: Path) -> tuple[str, list[dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(payload, list):
        return path.stem.replace("_text_candidates", ""), payload
    return payload.get("map_id") or path.stem.replace("_text_candidates", ""), payload.get("candidates", [])


def load_master(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def control_row(
    index: int,
    map_id: str,
    candidate: dict[str, Any],
    match: dict[str, Any],
) -> dict[str, str]:
    bbox = candidate.get("bbox_pixel") or [0, 0, 0, 0]
    x1, y1, x2, y2 = [float(value) for value in bbox]
    master = match["standard"]
    score = float(match["score"])
    trusted_note = (
        "Review on source image before setting enabled=true."
        if score >= 0.94
        else "Needs manual verification; OCR/name match is not strong enough for automatic fitting."
    )
    return {
        "control_id": f"cp_{index:03d}",
        "enabled": "false",
        "map_id": map_id,
        "name": candidate.get("text", ""),
        "matched_standard_name": master.get("name", ""),
        "match_type": match["match_type"],
        "match_score": f"{score:.3f}",
        "role": candidate.get("category", ""),
        "pixel_x": f"{(x1 + x2) / 2.0:.3f}",
        "pixel_y": f"{(y1 + y2) / 2.0:.3f}",
        "map_x": master.get("x", ""),
        "map_y": master.get("y", ""),
        "source_ocr_id": candidate.get("ocr_id", ""),
        "source_text": match["source_text"],
        "candidate_texts": match["candidate_texts"],
        "ocr_confidence": str(candidate.get("confidence", "")),
        "quality": str(candidate.get("quality", "")),
        "osm_reference": "linan_places_master",
        "weight": "1.0" if score >= 0.94 else "0.7",
        "notes": trusted_note,
    }


def structural_rows(start_index: int, map_id: str) -> list[dict[str, str]]:
    names = [
        ("west_lake_north_east_shore", "shoreline"),
        ("west_lake_south_east_shore", "shoreline"),
        ("qiantang_river_north_bank", "shoreline"),
        ("north_wall_west_corner", "wall_corner"),
        ("north_wall_east_corner", "wall_corner"),
        ("east_wall_midpoint", "wall"),
        ("imperial_city_center", "palace"),
    ]
    rows = []
    for offset, (name, role) in enumerate(names):
        rows.append(
            {
                "control_id": f"cp_{start_index + offset:03d}",
                "enabled": "false",
                "map_id": map_id,
                "name": name,
                "matched_standard_name": "",
                "match_type": "manual_structural_anchor",
                "match_score": "",
                "role": role,
                "pixel_x": "",
                "pixel_y": "",
                "map_x": "",
                "map_y": "",
                "source_ocr_id": "",
                "source_text": "",
                "candidate_texts": "",
                "ocr_confidence": "",
                "quality": "",
                "osm_reference": "",
                "weight": "1.0",
                "notes": "Optional manual control point. Fill both image pixel and OSM coordinates, then set enabled=true.",
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--master", type=Path, default=Path("data/places/linan_places_master.csv"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--map-id")
    args = parser.parse_args()

    map_id, candidates = load_candidates(args.candidates)
    if args.map_id:
        map_id = args.map_id
    output = args.output or Path("data/maps/control_points") / f"{map_id}_to_osm_control_points.csv"
    master_rows = load_master(args.master)

    matched_rows = []
    used_pairs: set[tuple[str, str]] = set()
    for candidate in candidates:
        match = best_match_for_candidate(candidate, master_rows)
        if not match:
            continue
        pair = (candidate.get("ocr_id", ""), match["standard"].get("name", ""))
        if pair in used_pairs:
            continue
        used_pairs.add(pair)
        matched_rows.append(control_row(len(matched_rows) + 1, map_id, candidate, match))

    matched_rows.sort(
        key=lambda row: (
            -float(row["match_score"]),
            row["matched_standard_name"],
            row["source_ocr_id"],
        )
    )
    for index, row in enumerate(matched_rows, start=1):
        row["control_id"] = f"cp_{index:03d}"

    rows = matched_rows + structural_rows(len(matched_rows) + 1, map_id)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"matched control candidates: {len(matched_rows)}")
    print(f"manual structural placeholders: {len(rows) - len(matched_rows)}")
    print(output)


if __name__ == "__main__":
    main()
