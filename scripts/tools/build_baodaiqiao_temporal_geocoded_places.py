from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "baodaiqiao"
TEXT_PATH = ROOT / "data" / "sources" / "baodaiqiao_community_gazetteer_clean.txt"
FULL_PLACES_CSV = DATA_DIR / "baodaiqiao_gazetteer_places_full.csv"
CURATED_PLACES_CSV = DATA_DIR / "baodaiqiao_gaode_place_checklist.csv"
OSM_MATCHES_CSV = DATA_DIR / "baodaiqiao_place_osm_matches.csv"
MILESTONES_CSV = DATA_DIR / "baodaiqiao_timeline_spatial_events.csv"

OUT_SEQUENCE_CSV = DATA_DIR / "baodaiqiao_places_temporal_sequence.csv"
OUT_CURATED_SEQUENCE_CSV = DATA_DIR / "baodaiqiao_places_temporal_sequence_curated.csv"
OUT_POINTS_GEOJSON = DATA_DIR / "baodaiqiao_places_temporal_points_gaode_gcj02.geojson"
OUT_CURATED_POINTS_GEOJSON = DATA_DIR / "baodaiqiao_places_temporal_points_curated_gaode_gcj02.geojson"
OUT_MISSING_CSV = DATA_DIR / "baodaiqiao_places_temporal_missing_coords.csv"
OUT_CURATED_MISSING_CSV = DATA_DIR / "baodaiqiao_places_temporal_missing_coords_curated.csv"
OUT_MILESTONE_POINTS_GEOJSON = DATA_DIR / "baodaiqiao_timeline_milestone_points_gaode_gcj02.geojson"
OUT_SUMMARY_JSON = DATA_DIR / "baodaiqiao_temporal_geocode_summary.json"


TIME_WINDOWS = [
    (-9999, 1911, "古代-清末"),
    (1912, 1948, "民国时期"),
    (1949, 1977, "集体化与农业建设"),
    (1978, 1991, "改革开放初期"),
    (1992, 2003, "开发区建设"),
    (2004, 2013, "社区成立与城市更新"),
    (2014, 2099, "运河文旅更新"),
]


MANUAL_TIME_ANCHORS = {
    "宝带桥": (816, "元和十一年至十四年（816—819）王仲舒捐带建桥"),
    "宝带桥社区": (2004, "2004年6月宝带桥居委会更名为宝带桥社区居委会"),
    "宝带桥·澹台湖景区": (2016, "2016年9月2日景区一期项目竣工"),
    "宝带桥·澹台湖核心展示园": (2020, "2020年12月景区更名为核心展示园"),
    "大运河国家文化公园": (2020, "2020年12月纳入大运河国家文化公园叙事"),
    "吴中博物馆": (2020, "2020年6月28日吴中博物馆建成开馆"),
    "吴文化博物馆": (2020, "2020年6月28日吴中博物馆建成开馆，后改名吴文化博物馆"),
    "宝带桥南": (2011, "2011年配合轨交二号线和宝带桥南站设定"),
    "宝带桥南站": (2011, "2011年配合轨交二号线和宝带桥南站设定"),
    "宝带桥公园": (2009, "社区志记载宝带桥旁建起宝带桥公园"),
    "澹台湖公园": (1996, "开发区建设阶段形成澹台湖公园公共空间"),
    "澹台湖大桥": (2004, "2004年6月澹台湖大桥建成"),
    "宝带桥商业大厦": (2016, "2016年12月宝带桥商业大厦竣工"),
    "宝信工业坊": (2015, "社区志记载宝信工业坊竣工"),
    "迎春南路": (1992, "1992年划归吴县经济技术开发区后按规划建设道路交通"),
    "石湖东路": (1992, "1992年划归吴县经济技术开发区后按规划建设道路交通"),
    "东吴南路": (1992, "1992年划归吴县经济技术开发区后按规划建设道路交通"),
    "天灵路": (1992, "1992年划归吴县经济技术开发区后按规划建设道路交通"),
    "澄湖中路": (1992, "1992年划归吴县经济技术开发区后按规划建设道路交通"),
    "澄湖东路": (1992, "1992年划归吴县经济技术开发区后按规划建设道路交通"),
    "宝通路": (1992, "1992年划归吴县经济技术开发区后按规划建设道路交通"),
    "宝丰路": (1992, "1992年划归吴县经济技术开发区后按规划建设道路交通"),
    "石湖东路公路桥": (1992, "1992年8月始境域桥梁建设速度、质量提高"),
    "石湖东路桥": (1992, "1992年8月始境域桥梁建设速度、质量提高"),
    "天灵路东2号桥": (1992, "1992年8月始境域桥梁建设速度、质量提高"),
    "天灵路西1号桥": (1992, "1992年8月始境域桥梁建设速度、质量提高"),
    "宝通路北4号桥": (1992, "1992年8月始境域桥梁建设速度、质量提高"),
    "宝通路南5号桥": (1992, "1992年8月始境域桥梁建设速度、质量提高"),
    "宝丰路9号桥": (1992, "1992年8月始境域桥梁建设速度、质量提高"),
    "澄湖东路3号桥": (1992, "1992年8月始境域桥梁建设速度、质量提高"),
    "宝南": (1950, "1950年建置沿革中境内自然村分属长桥乡、尹西乡"),
    "宝尹": (1950, "1950年建置沿革中境内自然村分属长桥乡、尹西乡"),
    "吴县经济技术开发区": (1992, "1992年8月境域划归吴县经济技术开发区"),
    "吴中经济开发区": (1992, "1992年8月境域划归吴县经济技术开发区，后属吴中经济开发区体系"),
    "吴中经济技术开发区": (1992, "1992年8月境域划归吴县经济技术开发区，后属吴中经济开发区体系"),
    "苏州吴中经济开发区": (1992, "1992年8月境域划归吴县经济技术开发区，后属吴中经济开发区体系"),
    "吴中区": (2001, "2001年2月吴县撤市建区，境域隶属苏州市吴中区"),
    "城南街道": (2004, "2004年6月吴中区城南街道办事处成立"),
}


MANUAL_TIME_ANCHORS.update(
    {
        name: (1950, "1950年建置沿革中明确列入境内自然村隶属关系")
        for name in [
            "金家村",
            "钱家村",
            "朱塔浜",
            "沉家浜",
            "沈家浜",
            "小村",
            "下田",
            "下田村",
            "西下田",
            "泥河田",
            "王家浜",
            "港南浜",
            "吴家角",
            "牛桩浜",
        ]
    }
)


PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2, "": 3}
STATUS_RANK = {"matched": 0, "review": 1, "manual": 2, "context": 3, "unmatched": 4, "": 5}


YEAR_PATTERNS = [
    re.compile(r"公元前\s*(\d{1,4})\s*年?"),
    re.compile(r"(?<!公元)前\s*(\d{1,4})\s*年?"),
    re.compile(r"(\d{3,4})\s*[—\-－~～至]\s*(\d{2,4})"),
    re.compile(r"(?<!\d)((?:[7-9]\d{2})|(?:1\d{3})|(?:20\d{2}))\s*年"),
    re.compile(r"（\s*((?:[7-9]\d{2})|(?:1\d{3})|(?:20\d{2}))\s*）"),
]


AMAP_KEY_ENV_NAMES = ["AMAP_KEY", "GAODE_KEY", "AMAP_WEB_SERVICE_KEY", "GAODE_WEB_SERVICE_KEY"]


MILESTONE_SIGNIFICANCE = {
    "bdq_001": "宝带桥奠定社区最核心的历史地标，连接运河交通、地方记忆与后续景区叙事。",
    "bdq_002": "林则徐主持修桥，使古桥在清代水运体系中继续发挥地标与交通作用。",
    "bdq_003": "同治年间重建强化了宝带桥的工程形态和文化遗存，延续古桥生命。",
    "bdq_004": "境域解放标志地方社会进入新的政权与基层治理阶段。",
    "bdq_005": "全境通电与省级文保并行，体现社区从生产生活现代化走向遗产保护。",
    "bdq_006": "高产水稻示范把水网农田转化为农业科技推广空间，形成江南高产稳产记忆。",
    "bdq_007": "划归经济技术开发区开启空间开发、道路桥梁建设和旧村改造的城市化阶段。",
    "bdq_008": "宝带桥社区居委会成立，社区作为现代基层治理单元正式成形。",
    "bdq_009": "轨交宝带桥南站带动迁移和出行结构变化，社区空间接入城市轨道网络。",
    "bdq_010": "大运河申遗成功使宝带桥从地方古桥上升为世界文化遗产节点。",
    "bdq_011": "宝带桥·澹台湖景区一期竣工，把古桥、运河、湖景组织为公共景观空间。",
    "bdq_012": "吴中博物馆开馆，使社区南堍成为吴地文化展示和文旅传播节点。",
    "bdq_013": "核心展示园更名把社区空间纳入大运河国家文化公园的整体叙事。",
}


def short_significance(text: str, limit: int = 22) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", "", text.replace("\ufeff", ""))


def parse_year_hits(fragment: str) -> list[tuple[int, int]]:
    hits: list[tuple[int, int]] = []
    for match in YEAR_PATTERNS[0].finditer(fragment):
        hits.append((-int(match.group(1)), match.start()))
    for match in YEAR_PATTERNS[1].finditer(fragment):
        hits.append((-int(match.group(1)), match.start()))
    for match in YEAR_PATTERNS[2].finditer(fragment):
        start = int(match.group(1))
        raw_end = match.group(2)
        end = int(raw_end)
        if end < 100:
            end = (start // 100) * 100 + end
        hits.extend([(start, match.start()), (end, match.start())])
    for pattern in YEAR_PATTERNS[3:]:
        for match in pattern.finditer(fragment):
            hits.append((int(match.group(1)), match.start()))
    return [(year, pos) for year, pos in hits if -6000 <= year <= 2099]


def parse_years(fragment: str) -> list[int]:
    return [year for year, _ in parse_year_hits(fragment)]


def iter_occurrences(text: str, name: str, limit: int = 80) -> list[int]:
    positions = []
    start = 0
    while len(positions) < limit:
        idx = text.find(name, start)
        if idx < 0:
            break
        positions.append(idx)
        start = idx + max(1, len(name))
    return positions


def sentence_window(text: str, pos: int, name_len: int, radius: int = 260) -> tuple[str, int]:
    hard_start = max(0, pos - radius)
    hard_end = min(len(text), pos + name_len + radius)
    left = max(text.rfind(mark, hard_start, pos) for mark in "。；！？")
    right_candidates = [idx for mark in "。；！？" if (idx := text.find(mark, pos + name_len, hard_end)) >= 0]
    start = left + 1 if left >= 0 else hard_start
    end = min(right_candidates) + 1 if right_candidates else hard_end
    return text[start:end], pos - start


def temporal_context_for_place(text: str, name: str) -> dict[str, Any]:
    years: list[int] = []
    samples: list[str] = []
    nearest_hits: list[int] = []
    positions = iter_occurrences(text, name)
    for pos in positions:
        fragment, local_pos = sentence_window(text, pos, len(name))
        hits = parse_year_hits(fragment)
        if hits:
            hits.sort(key=lambda item: abs(item[1] - local_pos))
            nearest = hits[0][0]
            nearest_hits.append(nearest)
        found = [year for year, _ in hits]
        if found:
            years.extend(found)
            if len(samples) < 3:
                samples.append(fragment)
    unique_years = sorted(set(years))
    nearest_unique = sorted(set(nearest_hits))
    extracted_primary = nearest_unique[0] if nearest_unique else ""
    earliest = unique_years[0] if unique_years else ""
    latest = unique_years[-1] if unique_years else ""
    primary_year: int | str = extracted_primary
    year_source = "context_sentence" if primary_year != "" else ""
    anchor_note = ""
    if name in MANUAL_TIME_ANCHORS:
        primary_year, anchor_note = MANUAL_TIME_ANCHORS[name]
        year_source = "manual_anchor"
    return {
        "primary_year": primary_year,
        "earliest_year": earliest,
        "latest_year": latest,
        "year_list": ";".join(str(year) for year in unique_years[:18]),
        "year_count": len(unique_years),
        "time_type": time_type_for_year(primary_year),
        "year_source": year_source,
        "time_anchor_note": anchor_note,
        "time_context": " || ".join(samples)[:900],
    }


def time_type_for_year(year: int | str) -> str:
    if year == "":
        return "无明确时间"
    value = int(year)
    for start, end, label in TIME_WINDOWS:
        if start <= value <= end:
            return label
    return "无明确时间"


def time_sort_key(row: dict[str, Any]) -> tuple[int, int, int, str]:
    year = row.get("primary_year", "")
    sort_year = int(year) if year not in {"", None} else 999999
    return (
        sort_year,
        PRIORITY_RANK.get(str(row.get("visual_priority", "")), 3),
        STATUS_RANK.get(str(row.get("match_status", "")), 5),
        str(row.get("gazetteer_name", "")),
    )


def amap_key() -> str:
    for name in AMAP_KEY_ENV_NAMES:
        value = os.environ.get(name)
        if value:
            return value
    return ""


def amap_place_search(name: str, key: str, city: str = "苏州") -> dict[str, str] | None:
    params = {
        "key": key,
        "keywords": name,
        "city": city,
        "citylimit": "true",
        "offset": "5",
        "page": "1",
        "extensions": "base",
        "output": "json",
    }
    url = "https://restapi.amap.com/v3/place/text?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=12) as response:
        payload = json.loads(response.read().decode("utf-8"))
    pois = payload.get("pois") or []
    for poi in pois:
        location = poi.get("location", "")
        if "," not in location:
            continue
        lon, lat = location.split(",", 1)
        address = poi.get("address", "")
        district = poi.get("adname", "")
        if "吴中" in district or "吴中" in address or "宝带桥" in name:
            return {
                "lon": lon,
                "lat": lat,
                "coord_source": "amap_poi",
                "coord_status": "gaode_matched",
                "coord_crs": "GCJ-02",
                "coord_note": f"{poi.get('name', name)}; {district}; {address}",
            }
    return None


def out_of_china(lon: float, lat: float) -> bool:
    return lon < 72.004 or lon > 137.8347 or lat < 0.8293 or lat > 55.8271


def transform_lat(x: float, y: float) -> float:
    ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x))
    ret += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(y * math.pi) + 40.0 * math.sin(y / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (160.0 * math.sin(y / 12.0 * math.pi) + 320 * math.sin(y * math.pi / 30.0)) * 2.0 / 3.0
    return ret


def transform_lon(x: float, y: float) -> float:
    ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x))
    ret += (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(x * math.pi) + 40.0 * math.sin(x / 3.0 * math.pi)) * 2.0 / 3.0
    ret += (150.0 * math.sin(x / 12.0 * math.pi) + 300.0 * math.sin(x / 30.0 * math.pi)) * 2.0 / 3.0
    return ret


def wgs84_to_gcj02(lon: float, lat: float) -> tuple[float, float]:
    if out_of_china(lon, lat):
        return lon, lat
    a = 6378245.0
    ee = 0.00669342162296594323
    dlat = transform_lat(lon - 105.0, lat - 35.0)
    dlon = transform_lon(lon - 105.0, lat - 35.0)
    radlat = lat / 180.0 * math.pi
    magic = math.sin(radlat)
    magic = 1 - ee * magic * magic
    sqrt_magic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((a * (1 - ee)) / (magic * sqrt_magic) * math.pi)
    dlon = (dlon * 180.0) / (a / sqrt_magic * math.cos(radlat) * math.pi)
    return lon + dlon, lat + dlat


def load_osm_coord_index() -> dict[str, dict[str, str]]:
    best: dict[str, dict[str, str]] = {}
    for row in read_csv(OSM_MATCHES_CSV):
        name = row.get("gazetteer_name", "")
        if not row.get("lon") or not row.get("lat"):
            continue
        current = best.get(name)
        if current is None or float(row.get("match_score") or 0) > float(current.get("match_score") or 0):
            best[name] = row
    return best


def add_osm_fallback_coords(rows: list[dict[str, Any]], coord_index: dict[str, dict[str, str]]) -> None:
    keyed_rows = {row["gazetteer_name"]: row for row in rows}
    for row in rows:
        name = row["gazetteer_name"]
        match = coord_index.get(name)
        if match:
            lon, lat = wgs84_to_gcj02(float(match["lon"]), float(match["lat"]))
            row.update(
                {
                    "lon": f"{lon:.7f}",
                    "lat": f"{lat:.7f}",
                    "coord_source": "osm_wgs84_to_gcj02",
                    "coord_status": "fallback_coord",
                    "coord_crs": "GCJ-02",
                    "coord_note": f"OSM {match.get('match_method', '')} -> GCJ-02; {match.get('osm_name', '')}",
                }
            )
    apply_synthetic_coords(keyed_rows)


def copy_coord(target: dict[str, Any], source: dict[str, Any], status: str, note: str) -> None:
    if not source.get("lon") or not source.get("lat"):
        return
    target.update(
        {
            "lon": source["lon"],
            "lat": source["lat"],
            "coord_source": "derived_from_related_place",
            "coord_status": status,
            "coord_crs": source.get("coord_crs", "GCJ-02"),
            "coord_note": note,
        }
    )


def average_coord(sources: list[dict[str, Any]]) -> tuple[str, str] | None:
    valid = [src for src in sources if src.get("lon") and src.get("lat")]
    if not valid:
        return None
    lon = sum(float(src["lon"]) for src in valid) / len(valid)
    lat = sum(float(src["lat"]) for src in valid) / len(valid)
    return f"{lon:.7f}", f"{lat:.7f}"


def apply_synthetic_coords(rows_by_name: dict[str, dict[str, Any]]) -> None:
    aliases = {
        "吴中博物馆": "吴文化博物馆",
        "宝带桥南站": "宝带桥南",
    }
    for target_name, source_name in aliases.items():
        target = rows_by_name.get(target_name)
        source = rows_by_name.get(source_name)
        if target and source and not target.get("lon"):
            copy_coord(target, source, "derived_coord", f"沿用相关地名坐标：{source_name}")

    local_anchor = rows_by_name.get("宝带桥")
    for name in ["运河", "大运河", "京杭大运河", "江南运河", "苏南运河", "古运河"]:
        target = rows_by_name.get(name)
        if target and local_anchor and local_anchor.get("lon"):
            copy_coord(target, local_anchor, "local_anchor_coord", "长线性水系以宝带桥附近作为社区内本地锚点")

    scenic_names = ["宝带桥·澹台湖景区", "宝带桥·澹台湖核心展示园", "大运河国家文化公园"]
    scenic_sources = [rows_by_name.get("宝带桥", {}), rows_by_name.get("澹台湖", {})]
    avg = average_coord([src for src in scenic_sources if src])
    if avg:
        for name in scenic_names:
            target = rows_by_name.get(name)
            if target and not target.get("lon"):
                target.update(
                    {
                        "lon": avg[0],
                        "lat": avg[1],
                        "coord_source": "synthetic_centroid",
                        "coord_status": "derived_coord",
                        "coord_crs": "GCJ-02",
                        "coord_note": "以宝带桥与澹台湖坐标均值作为景区临时中心点，需人工复核",
                    }
                )


def apply_amap_coords(rows: list[dict[str, Any]], key: str, scope: str, sleep_s: float) -> int:
    count = 0
    for row in rows:
        if row.get("lon"):
            continue
        if scope == "curated" and row.get("in_curated_checklist") != "1":
            continue
        name = row["gazetteer_name"]
        try:
            result = amap_place_search(name, key)
        except Exception as exc:
            row["coord_note"] = f"高德请求失败：{exc}"
            continue
        if result:
            row.update(result)
            count += 1
        time.sleep(sleep_s)
    return count


def feature_from_row(row: dict[str, Any]) -> dict[str, Any] | None:
    if not row.get("lon") or not row.get("lat"):
        return None
    props = {key: value for key, value in row.items() if key not in {"lon", "lat"}}
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [float(row["lon"]), float(row["lat"])]},
        "properties": props,
    }


def write_geojson(path: Path, rows: list[dict[str, Any]]) -> int:
    features = [feature for row in rows if (feature := feature_from_row(row))]
    payload = {
        "type": "FeatureCollection",
        "name": path.stem,
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": features,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(features)


def merge_place_rows() -> list[dict[str, Any]]:
    full_rows = read_csv(FULL_PLACES_CSV)
    curated = {row["gazetteer_name"]: row for row in read_csv(CURATED_PLACES_CSV)}
    text = normalize_text(TEXT_PATH.read_text(encoding="utf-8", errors="ignore"))
    rows: list[dict[str, Any]] = []
    for row in full_rows:
        name = row["gazetteer_name"]
        curated_row = curated.get(name, {})
        temporal = temporal_context_for_place(text, name)
        merged = {
            **row,
            "gaode_map_item": curated_row.get("gaode_map_item", row.get("gaode_map_item", name)),
            "match_status": curated_row.get("match_status", row.get("match_status", "")),
            "visual_priority": curated_row.get("visual_priority", row.get("visual_priority", "")),
            "gaode_check_action": curated_row.get("gaode_check_action", row.get("gaode_check_action", "")),
            "in_curated_checklist": "1" if name in curated else "0",
            **temporal,
            "lon": "",
            "lat": "",
            "coord_source": "",
            "coord_status": "missing",
            "coord_crs": "",
            "coord_note": "",
        }
        rows.append(merged)
    rows.sort(key=time_sort_key)
    return rows


def build_milestone_points(place_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows_by_name = {row["gazetteer_name"]: row for row in place_rows}
    milestones = read_csv(MILESTONES_CSV)
    output: list[dict[str, Any]] = []
    for item in milestones:
        place = item.get("gazetteer_place", "")
        source = rows_by_name.get(place)
        if source is None and "澹台湖" in place:
            source = rows_by_name.get("宝带桥·澹台湖景区") or rows_by_name.get("澹台湖")
        if source is None and "宝带桥" in place:
            source = rows_by_name.get("宝带桥")
        if source is None and "吴中博物馆" in place:
            source = rows_by_name.get("吴文化博物馆")
        row = dict(item)
        significance = MILESTONE_SIGNIFICANCE.get(item.get("event_id", ""), item.get("narration", ""))
        row["gazetteer_name"] = place
        row["time_type"] = time_type_for_year(item.get("start_year", ""))
        row["milestone_significance"] = significance
        row["significance_short"] = short_significance(significance)
        row["map_label"] = f"{item.get('start_year', '')} {item.get('title', '')}"
        row["story_label"] = f"{item.get('start_year', '')}｜{place}｜{short_significance(significance, 30)}"
        row["milestone_popup"] = (
            f"{item.get('title', '')}\n"
            f"地点：{place}\n"
            f"意义：{significance}\n"
            f"志文：{item.get('source_text', '')}"
        )
        if source and source.get("lon"):
            row.update(
                {
                    "lon": source["lon"],
                    "lat": source["lat"],
                    "coord_source": source.get("coord_source", ""),
                    "coord_status": source.get("coord_status", ""),
                    "coord_crs": source.get("coord_crs", "GCJ-02"),
                    "coord_note": source.get("coord_note", ""),
                }
            )
        else:
            row.update({"lon": "", "lat": "", "coord_source": "", "coord_status": "missing", "coord_crs": "", "coord_note": ""})
        output.append(row)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Build temporal and Gaode-aligned place outputs for Baodaiqiao gazetteer.")
    parser.add_argument("--use-amap", action="store_true", help="Use AMap Web Service POI search for rows missing coordinates.")
    parser.add_argument("--amap-scope", choices=["curated", "full"], default="curated", help="Rows to geocode via AMap when --use-amap is set.")
    parser.add_argument("--sleep", type=float, default=0.2, help="Seconds between AMap requests.")
    args = parser.parse_args()

    place_rows = merge_place_rows()
    add_osm_fallback_coords(place_rows, load_osm_coord_index())

    key = amap_key()
    amap_count = 0
    if args.use_amap:
        if not key:
            print("AMap key not found. Set AMAP_KEY or GAODE_KEY to enable Gaode POI geocoding.")
        else:
            amap_count = apply_amap_coords(place_rows, key, args.amap_scope, args.sleep)
            add_osm_fallback_coords(place_rows, load_osm_coord_index())

    place_rows.sort(key=time_sort_key)
    fields = [
        "gazetteer_name",
        "gaode_map_item",
        "place_type",
        "match_status",
        "visual_priority",
        "occurrence_count",
        "in_curated_checklist",
        "primary_year",
        "earliest_year",
        "latest_year",
        "year_list",
        "year_count",
        "time_type",
        "year_source",
        "time_anchor_note",
        "lon",
        "lat",
        "coord_source",
        "coord_status",
        "coord_crs",
        "coord_note",
        "gaode_check_action",
        "first_context",
        "time_context",
        "notes",
    ]
    write_csv(OUT_SEQUENCE_CSV, place_rows, fields)
    curated_rows = [row for row in place_rows if row.get("in_curated_checklist") == "1"]
    mapped_rows = [row for row in place_rows if row.get("lon")]
    missing_rows = [row for row in place_rows if not row.get("lon")]
    curated_mapped_rows = [row for row in curated_rows if row.get("lon")]
    curated_missing_rows = [row for row in curated_rows if not row.get("lon")]
    write_csv(OUT_CURATED_SEQUENCE_CSV, curated_rows, fields)
    write_csv(OUT_MISSING_CSV, missing_rows, fields)
    write_csv(OUT_CURATED_MISSING_CSV, curated_missing_rows, fields)
    point_count = write_geojson(OUT_POINTS_GEOJSON, mapped_rows)
    curated_point_count = write_geojson(OUT_CURATED_POINTS_GEOJSON, curated_mapped_rows)

    milestone_rows = build_milestone_points(place_rows)
    milestone_point_count = write_geojson(OUT_MILESTONE_POINTS_GEOJSON, milestone_rows)

    summary = {
        "places_total": len(place_rows),
        "places_with_coords": len(mapped_rows),
        "places_missing_coords": len(missing_rows),
        "curated_total": len(curated_rows),
        "curated_with_coords": len(curated_mapped_rows),
        "curated_missing_coords": len(curated_missing_rows),
        "amap_geocoded": amap_count,
        "points_geojson_features": point_count,
        "curated_points_geojson_features": curated_point_count,
        "milestone_points_geojson_features": milestone_point_count,
        "time_type_counts": Counter(row["time_type"] for row in place_rows),
        "coord_status_counts": Counter(row["coord_status"] for row in place_rows),
    }
    serializable = json.loads(json.dumps(summary, ensure_ascii=False, default=dict))
    OUT_SUMMARY_JSON.write_text(json.dumps(serializable, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"places_total={summary['places_total']}")
    print(f"places_with_coords={summary['places_with_coords']}")
    print(f"curated_with_coords={summary['curated_with_coords']}/{summary['curated_total']}")
    print(f"curated_points={summary['curated_points_geojson_features']}")
    print(f"milestone_points={summary['milestone_points_geojson_features']}")
    print(f"amap_geocoded={summary['amap_geocoded']}")
    print("time_type_counts=" + json.dumps(dict(summary["time_type_counts"]), ensure_ascii=False))
    print("coord_status_counts=" + json.dumps(dict(summary["coord_status_counts"]), ensure_ascii=False))


if __name__ == "__main__":
    main()
