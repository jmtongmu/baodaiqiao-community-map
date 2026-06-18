from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "baodaiqiao"

CURATED_POINTS = DATA_DIR / "baodaiqiao_places_temporal_points_curated_gaode_gcj02.geojson"
MILESTONE_POINTS = DATA_DIR / "baodaiqiao_timeline_milestone_points_gaode_gcj02.geojson"

OUT_CSV = DATA_DIR / "baodaiqiao_3d_animation_keyframes.csv"
OUT_POINTS = DATA_DIR / "baodaiqiao_3d_animation_keyframe_targets_3857.geojson"
OUT_PATH = DATA_DIR / "baodaiqiao_3d_animation_camera_path_3857.geojson"


def lonlat_to_web_mercator(lon: float, lat: float) -> tuple[float, float]:
    origin_shift = 20_037_508.342789244
    x = lon * origin_shift / 180.0
    lat = max(min(lat, 89.5), -89.5)
    y = math.log(math.tan((90.0 + lat) * math.pi / 360.0)) / (math.pi / 180.0)
    y = y * origin_shift / 180.0
    return x, y


def read_geojson(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def collect_named_coords() -> dict[str, tuple[float, float]]:
    coords: dict[str, tuple[float, float]] = {}
    for path in [CURATED_POINTS, MILESTONE_POINTS]:
        data = read_geojson(path)
        for feature in data["features"]:
            props = feature["properties"]
            lon, lat = feature["geometry"]["coordinates"]
            for key in ["gazetteer_name", "gazetteer_place", "place"]:
                name = props.get(key)
                if name and name not in coords:
                    coords[name] = (float(lon), float(lat))
    return coords


def avg(points: list[tuple[float, float]]) -> tuple[float, float]:
    return sum(x for x, _ in points) / len(points), sum(y for _, y in points) / len(points)


def get(coords: dict[str, tuple[float, float]], *names: str) -> tuple[float, float]:
    for name in names:
        if name in coords:
            return coords[name]
    raise KeyError(f"Missing coordinate for {names}")


def build_keyframes() -> list[dict[str, Any]]:
    coords = collect_named_coords()
    all_points = list(coords.values())
    center = avg(all_points)
    baodai_bridge = get(coords, "宝带桥")
    community = get(coords, "宝带桥社区")
    station = get(coords, "宝带桥南", "宝带桥南站")
    lake = get(coords, "澹台湖", "宝带桥·澹台湖景区")
    museum = get(coords, "吴文化博物馆", "吴中博物馆")
    development = avg(
        [
            get(coords, "石湖东路"),
            get(coords, "迎春南路"),
            get(coords, "宝尹花园"),
            get(coords, "钱家新村"),
        ]
    )

    plan = [
        {
            "keyframe": "K0",
            "time_s": 0,
            "shot_name": "全域开场",
            "target": center,
            "camera_distance_m": 2600,
            "pitch_deg": 48,
            "heading_deg": 315,
            "duration_hint_s": 3,
            "visible_focus": "底座、水系、全部里程碑光柱",
            "narration": "宝带桥社区的时间叙事从水网和古桥展开。",
        },
        {
            "keyframe": "K1",
            "time_s": 3,
            "shot_name": "古桥起点",
            "target": baodai_bridge,
            "camera_distance_m": 900,
            "pitch_deg": 42,
            "heading_deg": 300,
            "duration_hint_s": 3,
            "visible_focus": "宝带桥、816/1831/1872/2014光柱",
            "narration": "宝带桥奠定社区最核心的历史地标。",
        },
        {
            "keyframe": "K2",
            "time_s": 6,
            "shot_name": "基层治理与农业",
            "target": community,
            "camera_distance_m": 1150,
            "pitch_deg": 44,
            "heading_deg": 330,
            "duration_hint_s": 3,
            "visible_focus": "1949、1956、1962节点",
            "narration": "解放、通电和农业示范把地方社会推向新的治理与生产阶段。",
        },
        {
            "keyframe": "K3",
            "time_s": 9,
            "shot_name": "开发区建设",
            "target": development,
            "camera_distance_m": 1500,
            "pitch_deg": 40,
            "heading_deg": 20,
            "duration_hint_s": 4,
            "visible_focus": "1992道路桥梁、宝尹花园、钱家新村",
            "narration": "1992年后，空间开发、道路桥梁和旧村改造加速展开。",
        },
        {
            "keyframe": "K4",
            "time_s": 13,
            "shot_name": "轨交接入",
            "target": station,
            "camera_distance_m": 900,
            "pitch_deg": 42,
            "heading_deg": 350,
            "duration_hint_s": 3,
            "visible_focus": "宝带桥南站、2011节点",
            "narration": "轨交宝带桥南站改变社区出行和空间组织。",
        },
        {
            "keyframe": "K5",
            "time_s": 16,
            "shot_name": "澹台湖文旅更新",
            "target": lake,
            "camera_distance_m": 1200,
            "pitch_deg": 38,
            "heading_deg": 280,
            "duration_hint_s": 2,
            "visible_focus": "澹台湖、2016景区一期节点",
            "narration": "古桥、运河与湖景被组织为新的公共景观空间。",
        },
        {
            "keyframe": "K6",
            "time_s": 20,
            "shot_name": "文化展示收束",
            "target": museum,
            "camera_distance_m": 1050,
            "pitch_deg": 40,
            "heading_deg": 305,
            "duration_hint_s": 4,
            "visible_focus": "吴文化博物馆、2020核心展示园节点",
            "narration": "社区南堍成为吴地文化展示和大运河文旅叙事节点。",
        },
    ]

    rows = []
    for item in plan:
        lon, lat = item.pop("target")
        x, y = lonlat_to_web_mercator(lon, lat)
        rows.append(
            {
                **item,
                "target_lon": f"{lon:.7f}",
                "target_lat": f"{lat:.7f}",
                "target_x_3857": f"{x:.3f}",
                "target_y_3857": f"{y:.3f}",
                "label": f"{item['keyframe']} {item['time_s']}s {item['shot_name']}",
            }
        )
    return rows


def write_csv(rows: list[dict[str, Any]]) -> None:
    fields = [
        "keyframe",
        "time_s",
        "shot_name",
        "target_lon",
        "target_lat",
        "target_x_3857",
        "target_y_3857",
        "camera_distance_m",
        "pitch_deg",
        "heading_deg",
        "duration_hint_s",
        "visible_focus",
        "narration",
        "label",
    ]
    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_geojson(rows: list[dict[str, Any]]) -> None:
    features = []
    for row in rows:
        features.append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [float(row["target_x_3857"]), float(row["target_y_3857"])],
                },
                "properties": row,
            }
        )
    target_payload = {
        "type": "FeatureCollection",
        "name": "baodaiqiao_3d_animation_keyframe_targets_3857",
        "crs": {"type": "name", "properties": {"name": "EPSG:3857"}},
        "features": features,
    }
    OUT_POINTS.write_text(json.dumps(target_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    path_payload = {
        "type": "FeatureCollection",
        "name": "baodaiqiao_3d_animation_camera_path_3857",
        "crs": {"type": "name", "properties": {"name": "EPSG:3857"}},
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": [[float(row["target_x_3857"]), float(row["target_y_3857"])] for row in rows],
                },
                "properties": {
                    "name": "20秒动画镜头目标路径",
                    "keyframe_count": len(rows),
                    "duration_s": 20,
                },
            }
        ],
    }
    OUT_PATH.write_text(json.dumps(path_payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    rows = build_keyframes()
    write_csv(rows)
    write_geojson(rows)
    print(f"keyframes={len(rows)}")
    print(OUT_CSV)
    print(OUT_POINTS)
    print(OUT_PATH)


if __name__ == "__main__":
    main()
