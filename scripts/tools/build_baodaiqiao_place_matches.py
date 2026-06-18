from __future__ import annotations

import csv
import difflib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OSM_RAW = ROOT / "data" / "osm_baodaiqiao_named_raw.json"
YEARS_TEXT = ROOT / "data" / "timeline" / "baodaiqiao_year_candidates.txt"
OUT_DIR = ROOT / "data" / "baodaiqiao"


SEED_PLACES = [
    ("宝带桥社区", "community"),
    ("宝带桥", "heritage"),
    ("澹台湖", "water"),
    ("宝带桥·澹台湖景区", "scenic"),
    ("宝带桥·澹台湖核心展示园", "scenic"),
    ("大运河国家文化公园", "scenic"),
    ("吴中博物馆", "culture"),
    ("吴文化博物馆", "culture"),
    ("大运河", "waterway"),
    ("京杭大运河", "waterway"),
    ("苏南运河", "waterway"),
    ("江南运河", "waterway"),
    ("东吴南路", "road"),
    ("石湖东路", "road"),
    ("天灵路", "road"),
    ("澄湖中路", "road"),
    ("澄湖东路", "road"),
    ("迎春南路", "road"),
    ("宝通路", "road"),
    ("宝丰路", "road"),
    ("古塘河桥", "bridge"),
    ("下塔里桥", "bridge"),
    ("石湖东路公路桥", "bridge"),
    ("石湖东路桥", "bridge"),
    ("钱家桥", "bridge"),
    ("金家桥", "bridge"),
    ("新家桥", "bridge"),
    ("钱家村河", "waterway"),
    ("黄家浜", "waterway"),
    ("兴隆河", "waterway"),
    ("金家村河", "waterway"),
    ("跃进河", "waterway"),
    ("澹台湖北运河", "waterway"),
    ("牛桩浜东港", "waterway"),
    ("金家河", "waterway"),
    ("金星内河", "waterway"),
    ("新华内河", "waterway"),
    ("古塘河", "waterway"),
    ("宝南中心河", "waterway"),
    ("泥河田港", "waterway"),
    ("马桶港", "waterway"),
    ("钱家新村", "residential"),
    ("宝尹花园", "residential"),
    ("西下田", "settlement"),
    ("下田", "settlement"),
    ("小村", "settlement"),
    ("金家村", "settlement"),
    ("钱家村", "settlement"),
    ("朱塔浜", "settlement"),
    ("沉家浜", "settlement"),
    ("泥河田", "settlement"),
    ("王家浜", "settlement"),
    ("港南浜", "settlement"),
    ("吴家角", "settlement"),
    ("牛桩浜", "settlement"),
    ("宝尹", "historic_admin"),
    ("宝南", "historic_admin"),
    ("碧波实验小学", "education"),
    ("碧波中学", "education"),
    ("宝带桥公园", "park"),
    ("宝带桥商业大厦", "commercial"),
    ("宝信工业坊", "industrial"),
    ("田度里小区公园", "park"),
    ("老年活动中心", "service"),
    ("宝带桥南站", "transport"),
    ("宝带桥南", "transport"),
    ("党群服务中心", "service"),
]


SUFFIX_RE = re.compile(
    r"([\u4e00-\u9fffA-Za-z0-9·（）()]{2,18}(?:社区|景区|展示园|博物馆|小学|中学|幼儿园|公园|大厦|工业坊|活动中心|服务中心|"
    r"村|浜|河|港|湖|运河|路|桥|站|花园|新村))"
)


def norm(name: str) -> str:
    return (
        name.replace("（", "")
        .replace("）", "")
        .replace("(", "")
        .replace(")", "")
        .replace("·", "")
        .replace(" ", "")
        .lower()
    )


def load_osm_features() -> list[dict]:
    data = json.loads(OSM_RAW.read_text(encoding="utf-8"))
    features = []
    for el in data.get("elements", []):
        tags = el.get("tags", {})
        name = tags.get("name") or tags.get("name:zh")
        if not name:
            continue
        lon = el.get("lon") or el.get("center", {}).get("lon")
        lat = el.get("lat") or el.get("center", {}).get("lat")
        if lon is None or lat is None:
            continue
        features.append(
            {
                "osm_type": el.get("type"),
                "osm_id": el.get("id"),
                "osm_name": name,
                "osm_class": classify_osm(tags),
                "lon": float(lon),
                "lat": float(lat),
                "tags": tags,
            }
        )
    return features


def classify_osm(tags: dict) -> str:
    for key in ["historic", "tourism", "amenity", "leisure", "highway", "waterway", "railway", "landuse", "natural"]:
        if key in tags:
            return f"{key}:{tags[key]}"
    return "named"


def load_gazetteer_places() -> list[dict]:
    seen = {}
    for name, kind in SEED_PLACES:
        seen[name] = {"gazetteer_name": name, "place_type": kind, "source": "seed"}

    text = YEARS_TEXT.read_text(encoding="utf-8", errors="ignore")
    for match in SUFFIX_RE.finditer(text):
        name = cleanup_candidate(match.group(1))
        if not valid_candidate(name):
            continue
        if name not in seen:
            seen[name] = {"gazetteer_name": name, "place_type": guess_type(name), "source": "regex"}
    return list(seen.values())


def cleanup_candidate(name: str) -> str:
    name = re.sub(r"^[年月日是月旬至翌后前第\d一二三四五六七八九十百余多]+", "", name)
    name = re.sub(r"^[，。、；：与和及在对把由为至从按将]+", "", name)
    return name.strip("，。、；：；“”‘’")


def valid_candidate(name: str) -> bool:
    if len(name) < 2 or len(name) > 18:
        return False
    bad = ["平方米", "千米", "委员会", "人民政府", "工作委员会", "领导小组", "医疗保险"]
    return not any(x in name for x in bad)


def guess_type(name: str) -> str:
    rules = [
        ("社区", "community"),
        ("景区", "scenic"),
        ("展示园", "scenic"),
        ("博物馆", "culture"),
        ("小学", "education"),
        ("中学", "education"),
        ("公园", "park"),
        ("大厦", "commercial"),
        ("工业坊", "industrial"),
        ("活动中心", "service"),
        ("服务中心", "service"),
        ("新村", "residential"),
        ("花园", "residential"),
        ("村", "settlement"),
        ("浜", "waterway"),
        ("河", "waterway"),
        ("港", "waterway"),
        ("湖", "water"),
        ("运河", "waterway"),
        ("路", "road"),
        ("桥", "bridge"),
        ("站", "transport"),
    ]
    for suffix, kind in rules:
        if name.endswith(suffix):
            return kind
    return "place"


def match_places(places: list[dict], osm_features: list[dict]) -> list[dict]:
    matches = []
    for place in places:
        pn = norm(place["gazetteer_name"])
        best = None
        for osm in osm_features:
            on = norm(osm["osm_name"])
            compatible = is_compatible(place["place_type"], osm["osm_class"])
            if pn == on:
                score, method = 1.0, "exact"
            elif compatible and (pn in on or on in pn):
                score, method = min(len(pn), len(on)) / max(len(pn), len(on)), "contains"
            else:
                score = difflib.SequenceMatcher(None, pn, on).ratio()
                method = "fuzzy"
            rank = score + (0.08 if compatible else 0) + (0.04 if osm["osm_type"] == "way" else 0)
            if best is None or rank > best["_rank"]:
                best = {
                    **place,
                    **osm,
                    "match_score": round(score, 3),
                    "match_method": method,
                    "_rank": rank,
                    "_compatible": compatible,
                }
        if best and best["match_method"] in ("exact", "contains") and best["_compatible"]:
            best["match_status"] = "matched"
            best.pop("_rank", None)
            best.pop("_compatible", None)
            matches.append(best)
        elif best and best["match_score"] >= 0.72:
            best["match_status"] = "review"
            best.pop("_rank", None)
            best.pop("_compatible", None)
            matches.append(best)
        else:
            matches.append({**place, "match_status": "unmatched", "match_score": 0, "match_method": ""})
    return matches


def is_compatible(place_type: str, osm_class: str) -> bool:
    if place_type in {"community", "settlement", "historic_admin", "residential"}:
        return any(x in osm_class for x in ["place", "landuse:residential", "named", "boundary", "highway:bus_stop"])
    if place_type in {"heritage", "scenic", "culture"}:
        return any(x in osm_class for x in ["historic", "tourism", "leisure", "amenity", "named"])
    if place_type in {"water", "waterway"}:
        return any(x in osm_class for x in ["waterway", "natural:water", "natural:bay", "named"])
    if place_type == "road":
        return "highway:" in osm_class
    if place_type == "bridge":
        return "bridge" in osm_class or "highway:" in osm_class or "railway:" in osm_class
    if place_type == "education":
        return "amenity:school" in osm_class or "amenity:kindergarten" in osm_class
    if place_type == "park":
        return "leisure:park" in osm_class or "leisure:garden" in osm_class
    if place_type == "transport":
        return "railway:" in osm_class or "highway:bus_stop" in osm_class
    if place_type in {"commercial", "industrial"}:
        return any(x in osm_class for x in ["building", "landuse", "office", "shop", "amenity", "named"])
    if place_type == "service":
        return any(x in osm_class for x in ["amenity", "office", "building", "named"])
    return True


def write_outputs(matches: list[dict], osm_features: list[dict]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fields = [
        "gazetteer_name",
        "place_type",
        "source",
        "match_status",
        "match_method",
        "match_score",
        "osm_name",
        "osm_type",
        "osm_id",
        "osm_class",
        "lon",
        "lat",
    ]
    with (OUT_DIR / "baodaiqiao_place_osm_matches.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in matches:
            writer.writerow({k: row.get(k, "") for k in fields})

    geojson_features = []
    for row in matches:
        if row.get("match_status") not in {"matched", "review"}:
            continue
        props = {k: row.get(k, "") for k in fields if k not in ("lon", "lat")}
        geojson_features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [row["lon"], row["lat"]]},
                "properties": props,
            }
        )
    (OUT_DIR / "baodaiqiao_place_osm_matches.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": geojson_features}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    osm_geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [f["lon"], f["lat"]]},
                "properties": {
                    "osm_name": f["osm_name"],
                    "osm_type": f["osm_type"],
                    "osm_id": f["osm_id"],
                    "osm_class": f["osm_class"],
                },
            }
            for f in osm_features
        ],
    }
    (OUT_DIR / "baodaiqiao_osm_named_features.geojson").write_text(
        json.dumps(osm_geojson, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main() -> None:
    osm_features = load_osm_features()
    places = load_gazetteer_places()
    matches = match_places(places, osm_features)
    write_outputs(matches, osm_features)
    print(f"osm_features={len(osm_features)}")
    print(f"gazetteer_places={len(places)}")
    print(f"matched={sum(1 for m in matches if m.get('match_status') == 'matched')}")


if __name__ == "__main__":
    main()
