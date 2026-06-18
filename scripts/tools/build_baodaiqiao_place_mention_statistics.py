from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "baodaiqiao"
TEXT_PATH = ROOT / "data" / "sources" / "baodaiqiao_community_gazetteer_clean.txt"
FULL_SEQUENCE = DATA_DIR / "baodaiqiao_places_temporal_sequence.csv"
CURATED_SEQUENCE = DATA_DIR / "baodaiqiao_places_temporal_sequence_curated.csv"

OUT_STATS = DATA_DIR / "baodaiqiao_place_mention_statistics.csv"
OUT_CURATED_STATS = DATA_DIR / "baodaiqiao_place_mention_statistics_curated.csv"
OUT_TOP_MAPPED = DATA_DIR / "baodaiqiao_place_mention_top_mapped_gcj02.geojson"
OUT_TOP_MISSING = DATA_DIR / "baodaiqiao_place_mention_top_missing_coords.csv"
OUT_REPORT = DATA_DIR / "baodaiqiao_place_mention_statistics_report.md"
OUT_SUMMARY = DATA_DIR / "baodaiqiao_place_mention_statistics_summary.json"


TOP_LIMIT_FOR_MAP = 80
TOP_LIMIT_FOR_REPORT = 30


THEME_KEYWORDS = {
    "遗产文化": ["文物", "保护", "世界遗产", "大运河", "景区", "博物馆", "文化", "修缮", "重建", "题咏", "公园"],
    "基层治理": ["社区", "居委会", "党委", "街道", "大队", "公社", "村", "隶属", "划归", "成立", "撤销"],
    "开发建设": ["开发", "建设", "规划", "竣工", "改造", "迁移", "动迁", "道路", "桥梁", "小区", "花园"],
    "交通水系": ["运河", "河道", "桥", "道路", "地铁", "轨交", "站", "湖", "港", "浜"],
    "农业工业": ["农业", "水稻", "农田", "生产", "工业", "企业", "工厂", "厂", "加工", "织布"],
    "教育民生": ["小学", "中学", "幼儿园", "卫生", "医院", "活动中心", "服务", "居民", "生活"],
}


TYPE_LABELS = {
    "heritage_bridge": "古桥遗产",
    "bridge": "桥梁",
    "community": "社区",
    "historic_settlement": "历史自然村",
    "historic_admin": "历史行政/集体组织",
    "residential": "居住小区",
    "water": "湖泊水面",
    "waterway": "运河河道",
    "road": "道路",
    "transport": "交通节点",
    "culture_facility": "文化设施",
    "education": "教育设施",
    "scenic_area": "景区",
    "park": "公园",
    "industry": "产业设施",
    "admin_context": "行政背景",
    "religious_site": "宗教遗址",
    "service_facility": "社区服务设施",
    "medical": "医疗设施",
    "place": "地方简称",
}


CUSTOM_REASON = {
    "宝带桥": "它是社区志的核心命名地标，也是运河交通、古桥营造、历代修缮、文物保护和大运河申遗叙事的中心对象。",
    "宝带桥社区": "它是志书叙事主体，前言、建置沿革、组织治理、社区建设和新时代发展章节都会反复出现。",
    "澹台湖": "它与宝带桥共同构成社区最重要的自然和景观空间，贯穿地名来源、湖桥关系、景区建设和文旅更新。",
    "宝尹花园": "它代表旧村改造和居民安置后的现代居住空间，在社区管理、人口居住和小区治理内容中频繁出现。",
    "钱家新村": "它是动迁安置和居民生活小区的重要空间，常与旧村改造、搬迁、居民生活管理相关。",
    "下田": "它既是历史自然村名称，又常出现在下田村、西下田、学校和村庄建置叙述中，是基层地名网络中的高频节点。",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", "", text.replace("\ufeff", ""))


def positions(text: str, name: str, limit: int = 160) -> list[int]:
    result = []
    start = 0
    while len(result) < limit:
        idx = text.find(name, start)
        if idx < 0:
            break
        result.append(idx)
        start = idx + max(1, len(name))
    return result


def contexts_for(text: str, name: str, radius: int = 64, limit: int = 12) -> list[str]:
    contexts = []
    for idx in positions(text, name, limit=limit):
        start = max(0, idx - radius)
        end = min(len(text), idx + len(name) + radius)
        contexts.append(text[start:end])
    return contexts


def count_themes(contexts: list[str]) -> Counter:
    counts: Counter = Counter()
    joined = "\n".join(contexts)
    for theme, keywords in THEME_KEYWORDS.items():
        for keyword in keywords:
            counts[theme] += joined.count(keyword)
    return counts


def reason_for(row: dict[str, Any], contexts: list[str], themes: Counter) -> str:
    name = row["gazetteer_name"]
    if name in CUSTOM_REASON:
        return CUSTOM_REASON[name]
    place_type = TYPE_LABELS.get(row.get("place_type", ""), row.get("place_type", "地名"))
    top_themes = [theme for theme, count in themes.most_common(2) if count > 0]
    theme_text = "、".join(top_themes) if top_themes else "志书叙事"
    count = row.get("canonical_mention_count", row.get("occurrence_count", ""))
    if row.get("primary_year"):
        time_text = f"主要时间锚点为{row['primary_year']}年"
    else:
        time_text = "未提取到明确时间锚点"
    return f"该地名属于{place_type}，在志书中约出现{count}次，主要关联{theme_text}；{time_text}。"


def surface_count(text: str, name: str) -> int:
    return text.count(name)


def coordinate_quality(row: dict[str, str]) -> str:
    status = row.get("coord_status", "")
    match = row.get("match_status", "")
    if status in {"fallback_coord", "local_anchor_coord"} and match == "matched":
        return "已匹配坐标"
    if status in {"fallback_coord", "local_anchor_coord"}:
        return "可用坐标_需复核"
    if status == "derived_coord":
        return "推导坐标_需复核"
    if row.get("lon") and row.get("lat"):
        return "有坐标_需复核"
    return "缺坐标"


def feature_from_row(row: dict[str, Any]) -> dict[str, Any] | None:
    if not row.get("lon") or not row.get("lat"):
        return None
    props = {key: value for key, value in row.items() if key not in {"lon", "lat", "context_examples"}}
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


def build_stats() -> list[dict[str, Any]]:
    text = normalize_text(TEXT_PATH.read_text(encoding="utf-8", errors="ignore"))
    full_rows = read_csv(FULL_SEQUENCE)
    curated_names = {row["gazetteer_name"] for row in read_csv(CURATED_SEQUENCE)}
    stats = []
    for row in full_rows:
        name = row["gazetteer_name"]
        contexts = contexts_for(text, name)
        themes = count_themes(contexts)
        canonical_count = int(row.get("occurrence_count") or 0)
        raw_count = surface_count(text, name)
        mapped = bool(row.get("lon") and row.get("lat"))
        theme_top = themes.most_common(3)
        stat = {
            **row,
            "canonical_mention_count": canonical_count,
            "raw_surface_count": raw_count,
            "rank": 0,
            "top_themes": "；".join(f"{theme}:{count}" for theme, count in theme_top if count > 0),
            "reason": "",
            "context_examples": " || ".join(contexts[:3])[:900],
            "is_curated": "1" if name in curated_names else "0",
            "has_coord": "1" if mapped else "0",
            "coordinate_quality": coordinate_quality(row),
        }
        stat["reason"] = reason_for(stat, contexts, themes)
        stats.append(stat)
    stats.sort(key=lambda r: (-int(r["canonical_mention_count"]), r["gazetteer_name"]))
    for idx, row in enumerate(stats, start=1):
        row["rank"] = idx
        row["rank_label"] = f"{idx}. {row['gazetteer_name']}（{row['canonical_mention_count']}次）"
        count = int(row["canonical_mention_count"])
        if count >= 200:
            row["mention_level"] = "极高频"
        elif count >= 80:
            row["mention_level"] = "高频"
        elif count >= 30:
            row["mention_level"] = "中高频"
        elif count >= 10:
            row["mention_level"] = "中频"
        else:
            row["mention_level"] = "低频"
    return stats


def write_report(stats: list[dict[str, Any]], curated_stats: list[dict[str, Any]]) -> None:
    mapped = [row for row in curated_stats if row["has_coord"] == "1"]
    missing_top = [row for row in curated_stats if row["has_coord"] != "1"][:30]
    lines = [
        "# 宝带桥社区志地名提及统计报告",
        "",
        "## 统计口径",
        "",
        "- `canonical_mention_count`：沿用地名抽取流程的归并后出现次数，适合回答“哪些地名在志书中最常被作为空间对象提到”。",
        "- `raw_surface_count`：地名字符串在全文中的直接出现次数，可能包含嵌套词，例如“宝带桥”会被“宝带桥社区”包含。",
        "- 最终报告和地图标注使用精选地名清单，避免把“田村”等截断候选误作独立地名。",
        "- 地图标注优先使用 `canonical_mention_count` 排名。",
        "",
        "## 高频地名 Top 30",
        "",
        "| 排名 | 地名 | 类型 | 归并次数 | 全文字符串次数 | 坐标状态 | 为什么高频 |",
        "|---:|---|---|---:|---:|---|---|",
    ]
    for row in curated_stats[:TOP_LIMIT_FOR_REPORT]:
        display_rank = row.get("curated_rank") or row.get("rank")
        lines.append(
            f"| {display_rank} | {row['gazetteer_name']} | {TYPE_LABELS.get(row['place_type'], row['place_type'])} | "
            f"{row['canonical_mention_count']} | {row['raw_surface_count']} | {row['coordinate_quality']} | {row['reason']} |"
        )
    lines.extend(["", "## 已有坐标的高频地名", ""])
    for row in mapped[:30]:
        lines.append(
            f"- {row['rank_label']}：{row['coordinate_quality']}，坐标 {row.get('lon','')}, {row.get('lat','')}；{row['reason']}"
        )
    lines.extend(["", "## 高频但缺坐标，建议优先人工校准", ""])
    for row in missing_top:
        lines.append(f"- {row['rank_label']}：{TYPE_LABELS.get(row['place_type'], row['place_type'])}；{row['reason']}")
    OUT_REPORT.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    stats = build_stats()
    curated_stats = [row for row in stats if row["is_curated"] == "1"]
    curated_stats.sort(key=lambda r: (-int(r["canonical_mention_count"]), r["gazetteer_name"]))
    for idx, row in enumerate(curated_stats, start=1):
        row["curated_rank"] = idx
        row["rank_label"] = f"{idx}. {row['gazetteer_name']}（{row['canonical_mention_count']}次）"
    fields = [
        "rank",
        "curated_rank",
        "gazetteer_name",
        "gaode_map_item",
        "place_type",
        "mention_level",
        "canonical_mention_count",
        "raw_surface_count",
        "top_themes",
        "reason",
        "has_coord",
        "coordinate_quality",
        "lon",
        "lat",
        "coord_source",
        "coord_status",
        "coord_crs",
        "match_status",
        "visual_priority",
        "primary_year",
        "time_type",
        "year_list",
        "year_count",
        "rank_label",
        "context_examples",
        "first_context",
        "notes",
    ]
    write_csv(OUT_STATS, stats, fields)
    write_csv(OUT_CURATED_STATS, curated_stats, fields)
    top = curated_stats[:TOP_LIMIT_FOR_MAP]
    top_mapped = [row for row in top if row["has_coord"] == "1"]
    top_missing = [row for row in top if row["has_coord"] != "1"]
    write_csv(OUT_TOP_MISSING, top_missing, fields)
    mapped_count = write_geojson(OUT_TOP_MAPPED, top_mapped)
    write_report(stats, curated_stats)
    summary = {
        "total_places": len(stats),
        "curated_places": len(curated_stats),
        "top_limit_for_map": TOP_LIMIT_FOR_MAP,
        "top_mapped": mapped_count,
        "top_missing": len(top_missing),
        "top_10": [
            {
                "rank": row.get("curated_rank", row["rank"]),
                "name": row["gazetteer_name"],
                "count": row["canonical_mention_count"],
                "raw_surface_count": row["raw_surface_count"],
                "coordinate_quality": row["coordinate_quality"],
            }
            for row in curated_stats[:10]
        ],
    }
    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
