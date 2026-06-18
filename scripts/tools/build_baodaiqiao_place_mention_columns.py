from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "baodaiqiao"
INPUT = DATA_DIR / "baodaiqiao_place_mention_top_mapped_gcj02.geojson"
OUT_COLUMNS = DATA_DIR / "baodaiqiao_place_mention_columns_3857.geojson"
OUT_LABELS = DATA_DIR / "baodaiqiao_place_mention_column_labels_3857.geojson"
OUT_SUMMARY = DATA_DIR / "baodaiqiao_place_mention_columns_summary.json"


LEVEL_COLORS = {
    "极高频": "#d83b2d",
    "高频": "#e57f2a",
    "中高频": "#f0c34a",
    "中频": "#5aa469",
    "低频": "#6d8fb8",
}


def lonlat_to_web_mercator(lon: float, lat: float) -> tuple[float, float]:
    origin_shift = 20_037_508.342789244
    x = lon * origin_shift / 180.0
    lat = max(min(lat, 89.5), -89.5)
    y = math.log(math.tan((90.0 + lat) * math.pi / 360.0)) / (math.pi / 180.0)
    y = y * origin_shift / 180.0
    return x, y


def circle_ring(x: float, y: float, radius_m: float, segments: int = 48) -> list[list[float]]:
    ring = []
    for i in range(segments + 1):
        angle = 2 * math.pi * i / segments
        ring.append([x + radius_m * math.cos(angle), y + radius_m * math.sin(angle)])
    return ring


def short_text(text: str, limit: int = 34) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def height_for_count(count: int) -> float:
    # Square-root scaling keeps 宝带桥 dominant without crushing mid-frequency places.
    return round(18 + math.sqrt(max(count, 1)) * 5.4, 2)


def radius_for_count(count: int) -> float:
    return round(20 + math.sqrt(max(count, 1)) * 1.55, 2)


def read_geojson(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_columns() -> list[dict[str, Any]]:
    data = read_geojson(INPUT)
    features = []
    for feature in data["features"]:
        props = dict(feature["properties"])
        lon, lat = feature["geometry"]["coordinates"]
        x, y = lonlat_to_web_mercator(float(lon), float(lat))
        count = int(props.get("canonical_mention_count") or 0)
        height = height_for_count(count)
        radius = radius_for_count(count)
        level = props.get("mention_level", "")
        color = LEVEL_COLORS.get(level, "#888888")
        props.update(
            {
                "scene_class": "mention_column",
                "rank_num": int(props.get("curated_rank") or props.get("rank") or 999),
                "height_m": height,
                "base_m": 0,
                "radius_m": radius,
                "color": color,
                "opacity": 0.84,
                "label": props.get("rank_label", props.get("gazetteer_name", "")),
                "label_3d": f"{props.get('curated_rank') or props.get('rank')}. {props.get('gazetteer_name')}\\n{count}次 | {height}m",
                "info_panel": f"{props.get('gazetteer_name')}：{count}次；{short_text(props.get('reason', ''))}",
                "height_rule": "height_m = 18 + sqrt(canonical_mention_count) * 5.4",
                "radius_rule": "radius_m = 20 + sqrt(canonical_mention_count) * 1.55",
                "x_3857": round(x, 3),
                "y_3857": round(y, 3),
            }
        )
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": [circle_ring(x, y, radius)]},
                "properties": props,
            }
        )
    return features


def build_labels(column_features: list[dict[str, Any]]) -> list[dict[str, Any]]:
    labels = []
    for feature in column_features:
        props = dict(feature["properties"])
        x = float(props["x_3857"])
        y = float(props["y_3857"])
        height = float(props["height_m"])
        rank = int(props.get("curated_rank") or props.get("rank") or 999)
        # Offset labels slightly to reduce overlap while keeping them visually tied to the column.
        angle = (rank % 8) * math.pi / 4
        offset = 42 + min(rank, 20) * 1.8
        label_x = x + math.cos(angle) * offset
        label_y = y + math.sin(angle) * offset
        props.update(
            {
                "label_z_m": round(height + 12, 2),
                "label_offset_m": round(offset, 2),
                "label_display": props.get("label_3d", props.get("label", "")),
                "label_detail": (
                    f"{props.get('rank_label')}\\n"
                    f"提及次数：{props.get('canonical_mention_count')} 次\\n"
                    f"柱高：{props.get('height_m')} m\\n"
                    f"原因：{short_text(props.get('reason', ''), 48)}"
                ),
            }
        )
        labels.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [label_x, label_y, height + 12]},
                "properties": props,
            }
        )
    return labels


def main() -> None:
    features = build_columns()
    labels = build_labels(features)
    payload = {
        "type": "FeatureCollection",
        "name": OUT_COLUMNS.stem,
        "crs": {"type": "name", "properties": {"name": "EPSG:3857"}},
        "features": features,
    }
    OUT_COLUMNS.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    label_payload = {
        "type": "FeatureCollection",
        "name": OUT_LABELS.stem,
        "crs": {"type": "name", "properties": {"name": "EPSG:3857"}},
        "features": labels,
    }
    OUT_LABELS.write_text(json.dumps(label_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    heights = [float(f["properties"]["height_m"]) for f in features]
    summary = {
        "columns": len(features),
        "labels": len(labels),
        "min_height_m": min(heights) if heights else 0,
        "max_height_m": max(heights) if heights else 0,
        "output": str(OUT_COLUMNS),
        "label_output": str(OUT_LABELS),
    }
    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
