from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "baodaiqiao"

CURATED_POINTS = DATA_DIR / "baodaiqiao_places_temporal_points_curated_gaode_gcj02.geojson"
MILESTONE_POINTS = DATA_DIR / "baodaiqiao_timeline_milestone_points_gaode_gcj02.geojson"

OUT_STAGE = DATA_DIR / "baodaiqiao_3d_scene_stage.geojson"
OUT_BLOCKS = DATA_DIR / "baodaiqiao_3d_scene_place_blocks.geojson"
OUT_COLUMNS = DATA_DIR / "baodaiqiao_3d_scene_milestone_columns.geojson"
OUT_PATH = DATA_DIR / "baodaiqiao_3d_scene_milestone_path.geojson"
OUT_STAGE_3857 = DATA_DIR / "baodaiqiao_3d_scene_stage_3857.geojson"
OUT_BLOCKS_3857 = DATA_DIR / "baodaiqiao_3d_scene_place_blocks_3857.geojson"
OUT_COLUMNS_3857 = DATA_DIR / "baodaiqiao_3d_scene_milestone_columns_3857.geojson"
OUT_PATH_3857 = DATA_DIR / "baodaiqiao_3d_scene_milestone_path_3857.geojson"
OUT_SUMMARY = DATA_DIR / "baodaiqiao_3d_scene_summary.json"


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


CLASS_COLORS = {
    "stage": "#eadfca",
    "water": "#55a7d9",
    "waterway": "#4b9ed0",
    "road": "#b7b0a1",
    "bridge": "#9b8265",
    "heritage": "#b7894b",
    "culture": "#8e62bf",
    "education": "#4f79b7",
    "residential": "#d28c69",
    "transport": "#d45b43",
    "park": "#65a86a",
    "scenic": "#6da76d",
    "industry": "#8b8f96",
    "service": "#4aa790",
    "religious": "#b98a3a",
    "admin": "#777777",
    "other": "#9a9a9a",
}


PLACE_STYLE = {
    "community": ("admin", "circle", 70, 70, 12),
    "heritage_bridge": ("heritage", "rect", 140, 28, 8),
    "bridge": ("bridge", "rect", 80, 18, 6),
    "water": ("water", "ellipse", 180, 110, 0.2),
    "waterway": ("waterway", "ellipse", 160, 48, 0.2),
    "road": ("road", "rect", 150, 18, 1.2),
    "transport": ("transport", "circle", 70, 70, 18),
    "culture_facility": ("culture", "rect", 90, 70, 22),
    "education": ("education", "rect", 85, 60, 14),
    "residential": ("residential", "rect", 90, 70, 24),
    "park": ("park", "ellipse", 140, 90, 1.5),
    "scenic_area": ("scenic", "ellipse", 190, 120, 1.0),
    "commercial": ("transport", "rect", 90, 70, 24),
    "industry": ("industry", "rect", 85, 65, 12),
    "service_facility": ("service", "rect", 70, 55, 10),
    "medical": ("service", "rect", 70, 55, 14),
    "religious_site": ("religious", "circle", 60, 60, 10),
    "heritage": ("heritage", "circle", 60, 60, 12),
    "admin_context": ("admin", "circle", 55, 55, 6),
    "historic_admin": ("admin", "circle", 50, 50, 5),
    "historic_settlement": ("residential", "circle", 55, 55, 8),
    "place": ("other", "circle", 45, 45, 5),
}


EVENT_HEIGHT = {
    "culture": 95,
    "governance": 80,
    "service": 72,
    "economy": 68,
    "transport": 88,
    "construction": 84,
}


def read_geojson(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def meters_to_degrees(lon: float, lat: float, dx_m: float, dy_m: float) -> tuple[float, float]:
    lat_rad = math.radians(lat)
    dlon = dx_m / (111_320.0 * max(0.2, math.cos(lat_rad)))
    dlat = dy_m / 110_540.0
    return lon + dlon, lat + dlat


def rect_ring(lon: float, lat: float, width_m: float, height_m: float) -> list[list[float]]:
    half_w = width_m / 2
    half_h = height_m / 2
    offsets = [(-half_w, -half_h), (half_w, -half_h), (half_w, half_h), (-half_w, half_h), (-half_w, -half_h)]
    return [list(meters_to_degrees(lon, lat, dx, dy)) for dx, dy in offsets]


def ellipse_ring(lon: float, lat: float, width_m: float, height_m: float, segments: int = 36) -> list[list[float]]:
    pts = []
    rx = width_m / 2
    ry = height_m / 2
    for i in range(segments + 1):
        angle = 2 * math.pi * i / segments
        pts.append(list(meters_to_degrees(lon, lat, rx * math.cos(angle), ry * math.sin(angle))))
    return pts


def polygon_feature(ring: list[list[float]], props: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "Feature",
        "geometry": {"type": "Polygon", "coordinates": [ring]},
        "properties": props,
    }


def line_feature(coords: list[list[float]], props: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": coords},
        "properties": props,
    }


def feature_collection(name: str, features: list[dict[str, Any]], crs_name: str = "urn:ogc:def:crs:OGC:1.3:CRS84") -> dict[str, Any]:
    return {
        "type": "FeatureCollection",
        "name": name,
        "crs": {"type": "name", "properties": {"name": crs_name}},
        "features": features,
    }


def write_geojson(path: Path, name: str, features: list[dict[str, Any]], crs_name: str = "urn:ogc:def:crs:OGC:1.3:CRS84") -> None:
    path.write_text(json.dumps(feature_collection(name, features, crs_name), ensure_ascii=False, indent=2), encoding="utf-8")


def lonlat_to_web_mercator(lon: float, lat: float) -> list[float]:
    origin_shift = 20_037_508.342789244
    x = lon * origin_shift / 180.0
    lat = max(min(lat, 89.5), -89.5)
    y = math.log(math.tan((90.0 + lat) * math.pi / 360.0)) / (math.pi / 180.0)
    y = y * origin_shift / 180.0
    return [x, y]


def transform_geometry_to_3857(geometry: dict[str, Any]) -> dict[str, Any]:
    geom_type = geometry["type"]
    if geom_type == "Point":
        lon, lat = geometry["coordinates"]
        return {"type": "Point", "coordinates": lonlat_to_web_mercator(float(lon), float(lat))}
    if geom_type == "LineString":
        return {
            "type": "LineString",
            "coordinates": [lonlat_to_web_mercator(float(lon), float(lat)) for lon, lat in geometry["coordinates"]],
        }
    if geom_type == "Polygon":
        return {
            "type": "Polygon",
            "coordinates": [
                [lonlat_to_web_mercator(float(lon), float(lat)) for lon, lat in ring]
                for ring in geometry["coordinates"]
            ],
        }
    raise ValueError(f"Unsupported geometry type: {geom_type}")


def transform_features_to_3857(features: list[dict[str, Any]]) -> list[dict[str, Any]]:
    transformed = []
    for feature in features:
        transformed.append(
            {
                "type": "Feature",
                "geometry": transform_geometry_to_3857(feature["geometry"]),
                "properties": dict(feature["properties"]),
            }
        )
    return transformed


def coords_from_features(features: list[dict[str, Any]]) -> list[tuple[float, float]]:
    coords = []
    for feature in features:
        lon, lat = feature["geometry"]["coordinates"]
        coords.append((float(lon), float(lat)))
    return coords


def build_stage(coords: list[tuple[float, float]]) -> list[dict[str, Any]]:
    min_lon = min(lon for lon, _ in coords)
    max_lon = max(lon for lon, _ in coords)
    min_lat = min(lat for _, lat in coords)
    max_lat = max(lat for _, lat in coords)
    center_lon = (min_lon + max_lon) / 2
    center_lat = (min_lat + max_lat) / 2
    width_m = max(2400, (max_lon - min_lon) * 111_320 * math.cos(math.radians(center_lat)) + 700)
    height_m = max(1800, (max_lat - min_lat) * 110_540 + 700)
    return [
        polygon_feature(
            rect_ring(center_lon, center_lat, width_m, height_m),
            {
                "scene_name": "宝带桥社区3D叙事底座",
                "scene_class": "stage",
                "height_m": 0.2,
                "base_m": -0.3,
                "color": CLASS_COLORS["stage"],
                "opacity": 0.42,
                "label": "宝带桥社区发展叙事舞台",
                "note": "演示用底座，后续可替换为真实社区边界。",
            },
        )
    ]


def build_place_blocks(curated_features: list[dict[str, Any]]) -> list[dict[str, Any]]:
    blocks = []
    for feature in curated_features:
        props = feature["properties"]
        lon, lat = feature["geometry"]["coordinates"]
        place_type = props.get("place_type", "place")
        scene_class, shape, width_m, height_m_footprint, z = PLACE_STYLE.get(place_type, PLACE_STYLE["place"])
        if shape == "rect":
            ring = rect_ring(lon, lat, width_m, height_m_footprint)
        else:
            ring = ellipse_ring(lon, lat, width_m, height_m_footprint)
        blocks.append(
            polygon_feature(
                ring,
                {
                    "name": props.get("gazetteer_name", ""),
                    "place_type": place_type,
                    "scene_class": scene_class,
                    "time_type": props.get("time_type", ""),
                    "primary_year": props.get("primary_year", ""),
                    "height_m": z,
                    "base_m": 0,
                    "color": CLASS_COLORS.get(scene_class, CLASS_COLORS["other"]),
                    "opacity": 0.68 if scene_class not in {"water", "waterway", "park", "scenic"} else 0.48,
                    "label": props.get("gazetteer_name", ""),
                    "coord_status": props.get("coord_status", ""),
                    "note": props.get("time_anchor_note", "") or props.get("coord_note", ""),
                },
            )
        )
    return blocks


def build_milestone_columns(milestone_features: list[dict[str, Any]]) -> list[dict[str, Any]]:
    columns = []
    for order, feature in enumerate(milestone_features, start=1):
        props = feature["properties"]
        lon, lat = feature["geometry"]["coordinates"]
        height = EVENT_HEIGHT.get(props.get("event_type", ""), 78) + order * 2
        time_type = props.get("time_type", "")
        columns.append(
            polygon_feature(
                ellipse_ring(lon, lat, 58, 58, 40),
                {
                    "event_id": props.get("event_id", ""),
                    "title": props.get("title", ""),
                    "place": props.get("gazetteer_place", ""),
                    "start_year": props.get("start_year", ""),
                    "time_type": time_type,
                    "event_type": props.get("event_type", ""),
                    "scene_class": "milestone",
                    "height_m": height,
                    "base_m": 0,
                    "color": TIME_COLORS.get(time_type, "#888888"),
                    "opacity": 0.82,
                    "label": props.get("story_label", props.get("title", "")),
                    "significance": props.get("milestone_significance", ""),
                    "source_text": props.get("source_text", ""),
                },
            )
        )
    return columns


def build_milestone_path(milestone_features: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered = sorted(
        milestone_features,
        key=lambda feature: (int(feature["properties"].get("start_year") or 999999), feature["properties"].get("event_id", "")),
    )
    coords = [feature["geometry"]["coordinates"] for feature in ordered]
    return [
        line_feature(
            coords,
            {
                "name": "20秒里程碑时间路径",
                "scene_class": "timeline_path",
                "height_m": 2,
                "color": "#222222",
                "opacity": 0.72,
                "label": "20秒里程碑时间路径",
                "event_count": len(coords),
            },
        )
    ]


def main() -> None:
    curated = read_geojson(CURATED_POINTS)
    milestones = read_geojson(MILESTONE_POINTS)
    curated_features = curated["features"]
    milestone_features = milestones["features"]
    all_coords = coords_from_features(curated_features) + coords_from_features(milestone_features)

    stage = build_stage(all_coords)
    blocks = build_place_blocks(curated_features)
    columns = build_milestone_columns(milestone_features)
    path = build_milestone_path(milestone_features)

    write_geojson(OUT_STAGE, "baodaiqiao_3d_scene_stage", stage)
    write_geojson(OUT_BLOCKS, "baodaiqiao_3d_scene_place_blocks", blocks)
    write_geojson(OUT_COLUMNS, "baodaiqiao_3d_scene_milestone_columns", columns)
    write_geojson(OUT_PATH, "baodaiqiao_3d_scene_milestone_path", path)
    write_geojson(OUT_STAGE_3857, "baodaiqiao_3d_scene_stage_3857", transform_features_to_3857(stage), "EPSG:3857")
    write_geojson(OUT_BLOCKS_3857, "baodaiqiao_3d_scene_place_blocks_3857", transform_features_to_3857(blocks), "EPSG:3857")
    write_geojson(OUT_COLUMNS_3857, "baodaiqiao_3d_scene_milestone_columns_3857", transform_features_to_3857(columns), "EPSG:3857")
    write_geojson(OUT_PATH_3857, "baodaiqiao_3d_scene_milestone_path_3857", transform_features_to_3857(path), "EPSG:3857")

    summary = {
        "stage_features": len(stage),
        "place_block_features": len(blocks),
        "milestone_column_features": len(columns),
        "timeline_path_features": len(path),
        "outputs": [
            str(OUT_STAGE),
            str(OUT_BLOCKS),
            str(OUT_COLUMNS),
            str(OUT_PATH),
            str(OUT_STAGE_3857),
            str(OUT_BLOCKS_3857),
            str(OUT_COLUMNS_3857),
            str(OUT_PATH_3857),
        ],
    }
    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
