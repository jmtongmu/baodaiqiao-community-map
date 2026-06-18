from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "baodaiqiao"
WEB_DATA = ROOT / "web" / "baodaiqiao_aigc_map" / "data"

MENTION_POINTS = DATA_DIR / "baodaiqiao_place_mention_top_mapped_gcj02.geojson"
MILESTONES = DATA_DIR / "baodaiqiao_timeline_milestone_points_gaode_gcj02.geojson"
TEMPORAL_POINTS = DATA_DIR / "baodaiqiao_places_temporal_points_curated_gaode_gcj02.geojson"
CURATED_STATS = DATA_DIR / "baodaiqiao_place_mention_statistics_curated.csv"
MISSING_COORDS = DATA_DIR / "baodaiqiao_place_mention_top_missing_coords.csv"


LEVEL_COLORS = {
    "极高频": "#d83b2d",
    "高频": "#e57f2a",
    "中高频": "#f0c34a",
    "中频": "#5aa469",
    "低频": "#6d8fb8",
}

TIME_COLORS = {
    "古代-清末": "#8b5e34",
    "民国时期": "#5b7f95",
    "集体化与农业建设": "#4f8a54",
    "改革开放初期": "#b9822e",
    "开发区建设": "#d45b43",
    "社区成立与城市更新": "#3867b7",
    "运河文旅更新": "#7b4ab8",
    "无明确时间": "#8b8b8b",
}


def read_geojson(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def meters_to_degrees(lon: float, lat: float, dx_m: float, dy_m: float) -> tuple[float, float]:
    lat_rad = math.radians(lat)
    dlon = dx_m / (111_320.0 * max(0.2, math.cos(lat_rad)))
    dlat = dy_m / 110_540.0
    return lon + dlon, lat + dlat


def circle_ring(lon: float, lat: float, radius_m: float, segments: int = 48) -> list[list[float]]:
    ring = []
    for i in range(segments + 1):
        angle = 2 * math.pi * i / segments
        x, y = meters_to_degrees(lon, lat, math.cos(angle) * radius_m, math.sin(angle) * radius_m)
        ring.append([x, y])
    return ring


def height_for_count(count: int) -> float:
    return round(18 + math.sqrt(max(count, 1)) * 5.4, 2)


def radius_for_count(count: int) -> float:
    return round(20 + math.sqrt(max(count, 1)) * 1.55, 2)


def as_int(value: Any, fallback: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return fallback


def as_float(value: Any, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def feature_collection(name: str, features: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "type": "FeatureCollection",
        "name": name,
        "features": features,
    }


def add_common_visual_props(props: dict[str, Any]) -> dict[str, Any]:
    count = as_int(props.get("canonical_mention_count"))
    level = props.get("mention_level", "")
    rank = as_int(props.get("curated_rank") or props.get("rank"), 999)
    height = height_for_count(count)
    radius = radius_for_count(count)
    name = props.get("gazetteer_name", "")
    return {
        **props,
        "rank_num": rank,
        "count_num": count,
        "height_m": height,
        "radius_m": radius,
        "color": LEVEL_COLORS.get(level, "#888888"),
        "label_web": f"{rank}. {name}",
        "value_label": f"{count}次",
        "column_label": f"{rank}. {name} · {count}次",
    }


def build_mention_layers() -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    source = read_geojson(MENTION_POINTS)
    point_features = []
    column_features = []
    rankings = []
    for feature in source["features"]:
        lon, lat = feature["geometry"]["coordinates"]
        props = add_common_visual_props(dict(feature["properties"]))
        point_features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": props,
            }
        )
        column_features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [circle_ring(float(lon), float(lat), props["radius_m"])],
                },
                "properties": props,
            }
        )
        rankings.append(
            {
                "rank": props["rank_num"],
                "name": props.get("gazetteer_name", ""),
                "count": props["count_num"],
                "level": props.get("mention_level", ""),
                "reason": props.get("reason", ""),
                "coordinate_quality": props.get("coordinate_quality", ""),
                "lon": as_float(lon),
                "lat": as_float(lat),
            }
        )
    rankings.sort(key=lambda item: item["rank"])
    return (
        feature_collection("mention_points", point_features),
        feature_collection("mention_columns", column_features),
        rankings,
    )


def enrich_milestones() -> dict[str, Any]:
    data = read_geojson(MILESTONES)
    features = []
    for idx, feature in enumerate(data["features"], start=1):
        props = dict(feature["properties"])
        time_type = props.get("time_type", "")
        props["order"] = idx
        props["color"] = TIME_COLORS.get(time_type, "#888888")
        props["label_web"] = f"{props.get('start_year', '')} {props.get('title', '')}"
        features.append({**feature, "properties": props})
    return feature_collection("milestones", features)


def enrich_temporal_points() -> dict[str, Any]:
    data = read_geojson(TEMPORAL_POINTS)
    features = []
    for feature in data["features"]:
        props = dict(feature["properties"])
        props["color"] = TIME_COLORS.get(props.get("time_type", ""), "#888888")
        features.append({**feature, "properties": props})
    return feature_collection("temporal_points", features)


def build_stats_payload(rankings: list[dict[str, Any]]) -> dict[str, Any]:
    stats = read_csv(CURATED_STATS)
    missing = read_csv(MISSING_COORDS)
    top_stats = []
    for row in stats[:50]:
        top_stats.append(
            {
                "rank": as_int(row.get("curated_rank") or row.get("rank"), 999),
                "name": row.get("gazetteer_name", ""),
                "count": as_int(row.get("canonical_mention_count")),
                "raw_count": as_int(row.get("raw_surface_count")),
                "place_type": row.get("place_type", ""),
                "level": row.get("mention_level", ""),
                "has_coord": row.get("has_coord", ""),
                "coordinate_quality": row.get("coordinate_quality", ""),
                "reason": row.get("reason", ""),
                "top_themes": row.get("top_themes", ""),
            }
        )
    return {
        "rankings_mapped": rankings,
        "top_stats": top_stats,
        "missing_top": [
            {
                "rank": as_int(row.get("curated_rank") or row.get("rank"), 999),
                "name": row.get("gazetteer_name", ""),
                "count": as_int(row.get("canonical_mention_count")),
                "place_type": row.get("place_type", ""),
                "reason": row.get("reason", ""),
            }
            for row in missing[:30]
        ],
        "summary": {
            "mapped_columns": len(rankings),
            "curated_places": len(stats),
            "missing_top_count": len(missing),
            "top_name": rankings[0]["name"] if rankings else "",
            "top_count": rankings[0]["count"] if rankings else 0,
        },
    }


def main() -> None:
    points, columns, rankings = build_mention_layers()
    milestones = enrich_milestones()
    temporal = enrich_temporal_points()
    stats = build_stats_payload(rankings)
    write_json(WEB_DATA / "mention_points.geojson", points)
    write_json(WEB_DATA / "mention_columns.geojson", columns)
    write_json(WEB_DATA / "milestones.geojson", milestones)
    write_json(WEB_DATA / "temporal_points.geojson", temporal)
    write_json(WEB_DATA / "stats.json", stats)
    print(json.dumps(stats["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
