from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TEXT_PATH = ROOT / "data" / "sources" / "baodaiqiao_community_gazetteer_clean.txt"
OUT_DIR = ROOT / "data" / "baodaiqiao"
PREVIOUS_CHECKLIST = OUT_DIR / "baodaiqiao_gaode_place_checklist_manual_seed.csv"


SUFFIX_TYPE_RULES = [
    ("社区服务中心", "service_facility"),
    ("党群服务中心", "service_facility"),
    ("活动中心", "service_facility"),
    ("核心展示园", "scenic_area"),
    ("国家文化公园", "scenic_area"),
    ("经济技术开发区", "admin_context"),
    ("经济开发区", "admin_context"),
    ("高新技术产业开发区", "admin_context"),
    ("高新区", "admin_context"),
    ("街道办事处", "admin_context"),
    ("居民委员会", "community_admin"),
    ("村民委员会", "historic_admin"),
    ("居委会", "community_admin"),
    ("博物馆", "culture_facility"),
    ("幼儿园", "education"),
    ("卫生院", "medical"),
    ("卫生室", "medical"),
    ("医院", "medical"),
    ("派出所", "public_service"),
    ("工业坊", "industry"),
    ("大厦", "commercial"),
    ("别墅区", "residential"),
    ("自然村", "historic_settlement"),
    ("行政村", "historic_settlement"),
    ("新村", "residential"),
    ("花园", "residential"),
    ("小区", "residential"),
    ("社区", "community"),
    ("街道", "admin_context"),
    ("公社", "historic_admin"),
    ("大队", "historic_admin"),
    ("小学", "education"),
    ("中学", "education"),
    ("学校", "education"),
    ("大学", "education"),
    ("景区", "scenic_area"),
    ("公园", "park"),
    ("运河", "waterway"),
    ("公路", "road"),
    ("铁路", "railway"),
    ("大道", "road"),
    ("道路", "road"),
    ("站", "transport"),
    ("桥", "bridge"),
    ("路", "road"),
    ("河", "waterway"),
    ("港", "waterway"),
    ("浜", "waterway"),
    ("湖", "water"),
    ("荡", "water"),
    ("泾", "waterway"),
    ("寺", "religious_site"),
    ("庙", "religious_site"),
    ("庵", "religious_site"),
    ("塔", "heritage"),
    ("亭", "heritage"),
    ("厂", "industry"),
    ("村", "historic_settlement"),
]


SEED_PLACES = {
    "宝带桥社区": "community",
    "宝带桥": "heritage_bridge",
    "澹台湖": "water",
    "宝带桥·澹台湖景区": "scenic_area",
    "宝带桥·澹台湖核心展示园": "scenic_area",
    "大运河国家文化公园": "scenic_area",
    "吴中博物馆": "culture_facility",
    "吴文化博物馆": "culture_facility",
    "大运河": "waterway",
    "京杭大运河": "waterway",
    "江南运河": "waterway",
    "苏南运河": "waterway",
    "迎春南路": "road",
    "石湖东路": "road",
    "东吴南路": "road",
    "天灵路": "road",
    "澄湖中路": "road",
    "澄湖东路": "road",
    "宝通路": "road",
    "宝丰路": "road",
    "宝带桥南": "transport",
    "宝带桥南站": "transport",
    "碧波中学": "education",
    "碧波实验小学": "education",
    "宝带桥公园": "park",
    "宝带桥商业大厦": "commercial",
    "宝信工业坊": "industry",
    "党群服务中心": "service_facility",
    "钱家新村": "residential",
    "宝尹花园": "residential",
    "西下田": "historic_settlement",
    "下田": "historic_settlement",
    "小村": "historic_settlement",
    "金家村": "historic_settlement",
    "钱家村": "historic_settlement",
    "朱塔浜": "historic_settlement",
    "沉家浜": "historic_settlement",
    "沈家浜": "historic_settlement",
    "泥河田": "historic_settlement",
    "王家浜": "historic_settlement",
    "港南浜": "historic_settlement",
    "吴家角": "historic_settlement",
    "牛桩浜": "historic_settlement",
    "古塘河": "waterway",
    "宝南中心河": "waterway",
    "泥河田港": "waterway",
    "跃进河": "waterway",
    "钱家村河": "waterway",
    "金家村河": "waterway",
    "金家河": "waterway",
    "金星内河": "waterway",
    "新华内河": "waterway",
    "黄家浜": "waterway",
    "兴隆河": "waterway",
    "牛桩浜东港": "waterway",
    "澹台湖北运河": "waterway",
    "马桶港": "waterway",
    "古塘河桥": "bridge",
    "下塔里桥": "bridge",
    "石湖东路公路桥": "bridge",
    "钱家桥": "bridge",
    "金家桥": "bridge",
    "新家桥": "bridge",
    "田度里小区公园": "park",
    "老年活动中心": "service_facility",
    "红庄社区": "admin_context",
    "新江社区": "admin_context",
    "龙南社区": "admin_context",
    "郭巷街道": "admin_context",
    "城南街道": "admin_context",
    "吴中区": "admin_context",
    "吴县": "admin_context",
    "吴县市": "admin_context",
    "长洲县": "admin_context",
    "元和县": "admin_context",
    "吴江区": "admin_context",
    "长桥乡": "historic_admin",
    "宝带乡": "historic_admin",
    "尹山乡": "historic_admin",
    "尹西乡": "historic_admin",
    "郭巷乡": "historic_admin",
    "长桥镇": "historic_admin",
    "长桥人民公社": "historic_admin",
    "郭巷人民公社": "historic_admin",
    "吴县经济技术开发区": "admin_context",
    "苏州吴中经济开发区": "admin_context",
    "宝尹村": "historic_admin",
    "宝南村": "historic_admin",
    "新华大队": "historic_admin",
    "金星大队": "historic_admin",
    "金星24社": "historic_admin",
    "金星25社": "historic_admin",
    "碧波小学": "education",
    "碧波幼儿园": "education",
    "宝南小学": "education",
    "宝尹小学": "education",
    "金星小学": "education",
    "庙桥小学": "education",
    "钱家小学": "education",
    "泥河田公立小学": "education",
    "红庄中学": "education",
    "龙桥中学": "education",
    "宝庆寺": "religious_site",
    "兴福庵": "religious_site",
    "宝尹工业小区": "industry",
    "宝南花园": "residential",
    "威尼斯花园": "residential",
    "钱家花园": "residential",
    "东湖": "water",
    "太湖": "water",
    "石湖": "water",
    "金鸡湖": "water",
    "黄天荡": "water",
}


SEED_PLACES.update(
    {
        "澹台湖大桥": "bridge",
        "澹台湖公园": "park",
        "迎春路": "road",
        "澹台子祠": "religious_site",
        "太太庙": "religious_site",
        "古运河": "waterway",
        "宝尹新村": "residential",
        "吴中经济开发区": "admin_context",
        "宝带桥村": "historic_settlement",
        "宝南大队": "historic_admin",
        "宝尹大队": "historic_admin",
        "长桥公社": "historic_admin",
        "郭巷公社": "historic_admin",
        "长桥大队": "historic_admin",
    }
)


MANUAL_GAODE_STATUS = {
    "宝带桥社区": ("matched", "high", "在高德底图确认社区标签或以社区中心点标注"),
    "宝带桥": ("matched", "high", "核对高德底图桥名位置"),
    "澹台湖": ("matched", "high", "核对高德底图湖面与景区标签"),
    "吴文化博物馆": ("matched", "high", "核对高德底图博物馆点位"),
    "吴中博物馆": ("review", "high", "与吴文化博物馆合并核对"),
    "大运河": ("matched", "high", "核对高德底图河道标签"),
    "京杭大运河": ("matched", "high", "核对高德底图河道标签"),
    "江南运河": ("review", "medium", "若高德无江南运河标签则以大运河线表达"),
    "苏南运河": ("review", "medium", "若高德无苏南运河标签则以大运河线表达"),
    "迎春南路": ("matched", "high", "核对高德道路标签"),
    "石湖东路": ("matched", "high", "核对高德道路标签"),
    "东吴南路": ("matched", "medium", "核对高德道路标签"),
    "天灵路": ("matched", "medium", "核对高德道路标签"),
    "澄湖中路": ("matched", "medium", "核对高德道路标签"),
    "澄湖东路": ("matched", "medium", "核对高德道路标签"),
    "宝通路": ("matched", "medium", "核对高德道路标签"),
    "宝丰路": ("matched", "medium", "核对高德道路标签"),
    "宝带桥南": ("matched", "high", "核对高德地铁站标签"),
    "宝带桥南站": ("review", "high", "与宝带桥南合并表达"),
    "碧波中学": ("matched", "medium", "核对高德学校标签"),
    "碧波实验小学": ("review", "medium", "在高德底图人工确认点位"),
    "宝带桥公园": ("matched", "medium", "核对高德公园标签"),
    "钱家新村": ("review", "high", "在高德底图人工确认小区标签"),
    "宝尹花园": ("review", "high", "在高德底图人工确认小区标签"),
    "西下田": ("review", "high", "在高德底图人工确认小区或片区标签"),
}


VISIBLE_TYPES = {
    "community",
    "community_admin",
    "scenic_area",
    "culture_facility",
    "road",
    "transport",
    "bridge",
    "education",
    "park",
    "commercial",
    "industry",
    "service_facility",
    "medical",
    "public_service",
    "residential",
    "water",
    "waterway",
    "heritage",
    "heritage_bridge",
    "religious_site",
}


PREFIX_RE = re.compile(
    r"^(?:"
    r"境内|境域|全境|本区|本社区|社区|当地|该地|其中|时|是年|是月|翌年|同年|随后|后|前|"
    r"位于|坐落在|东依|南接|西连|北临|北靠|隶属|归属|划归|改称|更名为|成立|撤销|"
    r"建立|建成|开办|新建|投资|修复|重建|至|由|从|在|于|对|把|将|与|和|及|并|为|"
    r"中共|江苏省|苏州市|吴中区|城南街道|吴县|长桥乡|郭巷乡"
    r")+"
)


BAD_SUBSTRINGS = [
    "工作人员",
    "人民政府",
    "领导小组",
    "代表大会",
    "平方米",
    "平方千米",
    "文物保护单位",
    "先进单位",
    "称号",
    "资料",
    "志书",
    "居民生活",
    "群众文化",
    "自然环境",
    "行政组织",
    "医疗保险",
    "合作医疗",
    "管理委员会",
    "中国的",
    "中外",
    "一个",
    "几个",
    "多少个",
    "这座",
    "此桥",
    "全桥",
    "主桥",
    "石拱桥",
    "木桥",
    "古桥",
    "名桥",
    "建桥",
    "修桥",
    "全境",
]


SPLIT_MARKERS = [
    "更名为",
    "改称",
    "并入",
    "迁至",
    "搬至",
    "划归",
    "归属",
    "隶属",
    "位于",
    "坐落在",
    "即今",
    "俗称",
    "又名",
    "称为",
    "名为",
    "开办",
    "创办",
    "建起",
    "建成",
    "新建",
    "构筑了",
    "构筑",
    "修缮",
    "修筑",
    "重建",
    "保护",
    "授予",
    "任",
    "当选",
    "兼任",
    "代理",
    "主持",
    "负责",
    "利用",
    "视察",
    "介绍",
    "经过",
    "游览",
    "谈起",
    "看到",
    "听到",
    "走",
    "沿",
    "至",
    "于",
    "在",
    "有",
    "为",
    "由",
    "向",
    "的",
]


BAD_PREFIX_WORDS = [
    "不",
    "且",
    "也",
    "但",
    "使",
    "以",
    "了",
    "其",
    "该",
    "此",
    "各",
    "全",
    "今天",
    "人们",
    "严重",
    "交通",
    "居民",
    "群众",
    "干部",
    "工作人员",
    "中共",
    "中国",
    "中外",
    "个",
    "一个",
    "几个",
]


LOCAL_TOKENS = [
    "宝带",
    "澹台",
    "吴中",
    "吴文化",
    "吴县",
    "长洲",
    "元和",
    "长桥",
    "宝尹",
    "宝南",
    "新华",
    "金星",
    "钱家",
    "金家",
    "朱塔",
    "沉家",
    "沈家",
    "下田",
    "西下田",
    "小村",
    "泥河田",
    "王家浜",
    "港南",
    "吴家角",
    "牛桩",
    "古塘",
    "石湖",
    "东吴",
    "迎春",
    "天灵",
    "澄湖",
    "宝通",
    "宝丰",
    "碧波",
    "宝庆",
    "兴福",
    "庙桥",
    "田度里",
    "宝信",
    "威尼斯",
    "大运河",
    "京杭",
    "江南运河",
    "苏南运河",
    "郭巷",
    "城南",
    "红庄",
    "新江",
    "龙南",
]


NOISY_VISUAL_PATTERNS = [
    "一个",
    "两个",
    "几个",
    "多少",
    "五十三",
    "50多",
    "53个",
    "什么",
    "此",
    "这个",
    "那",
    "古代",
    "昔日",
    "保护",
    "修缮",
    "重修",
    "介绍",
    "视察",
    "经过",
    "看",
    "听",
    "说",
    "评说",
    "赋诗",
    "照片",
    "上桥",
    "撞桥",
    "塌桥",
]


CURATED_REJECT_SUBSTRINGS = [
    "先后",
    "成立",
    "当选",
    "加入",
    "名称",
    "析分",
    "必须",
    "绕过",
    "来到",
    "授予",
    "停办",
    "转制",
    "迁移",
    "扩容",
    "家里",
    "办起",
    "分别",
    "担负",
    "大学生",
    "已是大学",
    "高年级",
    "学生",
    "冀云",
    "咕天",
    "其一",
    "横塘朝南",
    "湾环",
    "宝带一长桥",
    "宝带环桥",
    "飞作吴中第一桥",
    "王仲舒捐宝带造桥",
    "石湖上方山行春桥",
    "又询问",
    "我突发去",
    "进了",
    "建设休闲公园",
    "等5个",
    "5个居民",
    "别墅区",
    "境域公路",
    "主干路",
    "一路",
    "设置交通",
    "粪检站",
    "碧波飘荡",
    "碧波荡漾",
    "入运河",
    "隔着运河",
    "面对",
    "填埋",
    "根据",
    "进一步",
    "规范",
    "共青团",
    "大队大队",
    "隔河",
]


CURATED_REJECT_PREFIXES = [
    "入",
    "底",
    "田中段里",
    "新华2所",
    "龙南等村",
    "苏州邮电局",
    "尹山乡",
    "枫桥区",
    "车坊区",
    "·",
    "北连",
    "北接",
    "南进入",
    "东过",
    "南北",
    "因",
    "米",
    "西接",
    "属",
]


def has_curated_noise(name: str) -> bool:
    return any(name.startswith(prefix) for prefix in CURATED_REJECT_PREFIXES) or any(
        marker in name for marker in CURATED_REJECT_SUBSTRINGS
    )


def normalize_text(text: str) -> str:
    text = text.replace("\ufeff", "")
    text = re.sub(r"[ \t\r\f\v]+", "", text)
    return text


def place_type_for(name: str) -> str:
    if name in SEED_PLACES:
        return SEED_PLACES[name]
    for suffix, place_type in SUFFIX_TYPE_RULES:
        if name.endswith(suffix):
            return place_type
    return "place"


def cleanup_candidate(raw: str) -> str:
    name = raw.strip("，。、；：：“”‘’《》【】（）()[] \n\t")
    name = re.sub(r"^[0-9一二三四五六七八九十百千万年月日号前后上下旬第届]+", "", name)
    last = None
    while last != name:
        last = name
        name = PREFIX_RE.sub("", name)
        for marker in SPLIT_MARKERS:
            if marker in name:
                tail = name.split(marker)[-1]
                if len(tail) >= 2:
                    name = tail
    if name.endswith(("居民委员会", "居委会", "村民委员会")):
        if "宝带桥" in name:
            return "宝带桥社区"
        if "宝尹" in name:
            return "宝尹"
        if "宝南" in name:
            return "宝南"
    if name.endswith("社区") and "街道" in name:
        name = name.split("街道")[-1]
    if name.endswith(("小学", "中学", "幼儿园")) and "的" in name:
        name = name.split("的")[-1]
    return name.strip("，。、；：：“”‘’《》【】（）()[]")


def compatible_seed_type(seed_type: str, place_type: str) -> bool:
    if seed_type == place_type:
        return True
    if seed_type == "heritage_bridge" and place_type == "bridge":
        return True
    if seed_type in {"water", "waterway"} and place_type in {"water", "waterway"}:
        return True
    return False


def reduce_to_known_name(name: str, place_type: str) -> str:
    candidates = [
        seed
        for seed, seed_type in SEED_PLACES.items()
        if seed != name
        and seed in name
        and (
            compatible_seed_type(seed_type, place_type)
            or (seed_type == "historic_settlement" and place_type == "waterway" and len(seed) >= 3 and name.endswith(seed))
        )
    ]
    if candidates:
        return max(candidates, key=len)
    if "宝带桥" in name and place_type == "bridge":
        return "宝带桥"
    return name


def is_valid_name(name: str, place_type: str) -> bool:
    if len(name) < 2 or len(name) > 18:
        return False
    if name in {"自然村", "行政村", "居民小区", "社区", "景区", "公园", "道路", "桥梁", "河道"}:
        return False
    if re.fullmatch(r"[0-9一二三四五六七八九十百千万年月日号前后上下旬第届]+", name):
        return False
    if any(name.startswith(prefix) for prefix in BAD_PREFIX_WORDS):
        return False
    if any(bad in name for bad in BAD_SUBSTRINGS):
        return False
    if place_type == "bridge" and name not in SEED_PLACES:
        if len(name) > 8:
            return False
        if name in {"长桥", "古桥", "木桥", "石桥", "大桥", "小桥", "主桥", "名桥", "全桥", "此桥", "拱桥", "吊桥", "索桥"}:
            return False
    if place_type in {"water", "waterway"} and name not in SEED_PLACES:
        if len(name) > 8:
            return False
        if name in {"此湖", "这个湖", "其他湖", "湖", "河", "港", "浜"}:
            return False
    if place_type == "residential" and name not in SEED_PLACES:
        if len(name) > 10:
            return False
    return True


def first_context(text: str, name: str, radius: int = 48) -> str:
    idx = text.find(name)
    if idx < 0:
        return ""
    start = max(0, idx - radius)
    end = min(len(text), idx + len(name) + radius)
    return re.sub(r"\s+", "", text[start:end])


def gaode_status(name: str, place_type: str, previous: dict[str, dict]) -> tuple[str, str, str]:
    if name in MANUAL_GAODE_STATUS:
        return MANUAL_GAODE_STATUS[name]
    if name in previous:
        row = previous[name]
        return row.get("match_status", "review"), row.get("visual_priority", "medium"), row.get("gaode_check_action", "")
    if place_type == "admin_context":
        return "context", "low", "作为边界/方位参照，不一定在辖区内单独标注"
    if place_type in {"historic_settlement", "historic_admin"}:
        return "manual", "medium", "高德底图未必有历史地名标签，需人工补点或补面"
    if place_type in VISIBLE_TYPES:
        return "review", "medium", "在高德矢量底图逐项核对同名或近名标签"
    return "review", "low", "人工判断是否作为空间标注"


def load_previous_checklist() -> dict[str, dict]:
    if not PREVIOUS_CHECKLIST.exists():
        return {}
    with PREVIOUS_CHECKLIST.open("r", encoding="utf-8-sig", newline="") as f:
        return {row["gazetteer_name"]: row for row in csv.DictReader(f)}


def extract_candidates(text: str) -> dict[str, dict]:
    suffix_re = "|".join(re.escape(suffix) for suffix, _ in SUFFIX_TYPE_RULES)
    pattern = re.compile(r"([\u4e00-\u9fffA-Za-z0-9·（）()]{1,24}(?:" + suffix_re + r"))")
    raw_names = []
    for match in pattern.finditer(text):
        name = cleanup_candidate(match.group(1))
        place_type = place_type_for(name)
        name = reduce_to_known_name(name, place_type)
        place_type = place_type_for(name)
        if is_valid_name(name, place_type):
            raw_names.append(name)
    for name in SEED_PLACES:
        if name in text:
            raw_names.append(name)

    counts = Counter(raw_names)
    places = {}
    for name, count in counts.items():
        places[name] = {
            "gazetteer_name": name,
            "place_type": place_type_for(name),
            "occurrence_count": count,
            "first_context": first_context(text, name),
        }
    return places


def write_outputs(places: dict[str, dict], previous: dict[str, dict]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for name, row in places.items():
        status, priority, action = gaode_status(name, row["place_type"], previous)
        rows.append(
            {
                "gazetteer_name": name,
                "gaode_map_item": previous.get(name, {}).get("gaode_map_item", name),
                "place_type": row["place_type"],
                "match_status": status,
                "visual_priority": priority,
                "occurrence_count": row["occurrence_count"],
                "gaode_check_action": action,
                "first_context": row["first_context"],
                "notes": previous.get(name, {}).get("notes", ""),
            }
        )
    rows.sort(key=lambda r: (priority_rank(r["visual_priority"]), status_rank(r["match_status"]), r["place_type"], r["gazetteer_name"]))

    fields = [
        "gazetteer_name",
        "gaode_map_item",
        "place_type",
        "match_status",
        "visual_priority",
        "occurrence_count",
        "gaode_check_action",
        "first_context",
        "notes",
    ]
    full_csv = OUT_DIR / "baodaiqiao_gazetteer_places_full.csv"
    checklist_full_csv = OUT_DIR / "baodaiqiao_gaode_place_checklist_full.csv"
    curated_csv = OUT_DIR / "baodaiqiao_gaode_place_checklist.csv"
    curated_rows = [row for row in rows if is_curated_for_visual(row)]
    for path, output_rows in [(full_csv, rows), (checklist_full_csv, rows), (curated_csv, curated_rows)]:
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(output_rows)

    by_type = defaultdict(list)
    for row in curated_rows:
        by_type[row["place_type"]].append(row)
    md_lines = ["# 宝带桥社区志地名索引", ""]
    md_lines.append(f"全文候选 {len(rows)} 条；可视化精选核对 {len(curated_rows)} 条。")
    for place_type in sorted(by_type):
        md_lines.append("")
        md_lines.append(f"## {place_type}")
        for row in by_type[place_type][:80]:
            md_lines.append(f"- {row['gazetteer_name']}（{row['match_status']}，{row['occurrence_count']}次）")
    (OUT_DIR / "baodaiqiao_gazetteer_places_full.md").write_text("\n".join(md_lines), encoding="utf-8")


def is_curated_for_visual(row: dict) -> bool:
    name = row["gazetteer_name"]
    place_type = row["place_type"]
    count = int(row["occurrence_count"])
    if name in SEED_PLACES:
        return True
    if has_curated_noise(name):
        return False
    if any(pattern in name for pattern in NOISY_VISUAL_PATTERNS):
        return False
    if not any(token in name for token in LOCAL_TOKENS):
        return False
    if place_type == "bridge" and "长桥" in name:
        return False
    if place_type == "education" and len(name) > 9:
        return False
    if place_type == "industry" and len(name) > 10:
        return False
    if place_type in {"admin_context", "transport"} and len(name) > 12:
        return False
    if place_type in {"historic_settlement", "historic_admin"}:
        return False
    if place_type in {"bridge", "water", "waterway", "road", "residential", "historic_settlement", "historic_admin"}:
        return len(name) <= 10
    if place_type in {"education", "industry", "religious_site", "park", "service_facility", "medical", "transport", "community", "community_admin", "scenic_area", "culture_facility", "admin_context"}:
        return count >= 1
    return count >= 2


def priority_rank(value: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(value, 3)


def status_rank(value: str) -> int:
    return {"matched": 0, "review": 1, "manual": 2, "context": 3, "unmatched": 4}.get(value, 5)


def main() -> None:
    text = normalize_text(TEXT_PATH.read_text(encoding="utf-8", errors="ignore"))
    previous = load_previous_checklist()
    places = extract_candidates(text)
    write_outputs(places, previous)
    print(f"places={len(places)}")
    counts = Counter(row["place_type"] for row in places.values())
    for key, value in sorted(counts.items()):
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
