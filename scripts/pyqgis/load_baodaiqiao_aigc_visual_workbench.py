from pathlib import Path

from qgis.core import QgsProject, QgsRasterLayer


PROJECT_ROOT = Path(r"F:\AIGC\baodaiqiao-community-map")
PYQGIS_DIR = PROJECT_ROOT / "scripts" / "pyqgis"

WORKBENCH_GROUP = "宝带桥社区志_AIGC可视化工作台"


BASEMAPS = [
    (
        "高德纯地图_AIGC底图",
        "type=xyz&url=https://webrd01.is.autonavi.com/appmaptile?x%3D%7Bx%7D%26y%3D%7By%7D%26z%3D%7Bz%7D%26lang%3Dzh_cn%26size%3D1%26scl%3D1%26style%3D8&zmax=18&zmin=0",
    ),
    (
        "高德卫星_AIGC底图",
        "type=xyz&url=https://webst01.is.autonavi.com/appmaptile?style%3D6%26x%3D%7Bx%7D%26y%3D%7By%7D%26z%3D%7Bz%7D&zmax=18&zmin=0",
    ),
]


WORKBENCH_SCRIPTS = [
    ("地名提及统计互动层", PYQGIS_DIR / "load_baodaiqiao_place_mention_statistics.py"),
    ("高频地名柱形统计", PYQGIS_DIR / "load_baodaiqiao_place_mention_columns.py"),
    ("时间地名和里程碑", PYQGIS_DIR / "load_baodaiqiao_temporal_places.py"),
    ("3D沙盘实践层", PYQGIS_DIR / "load_baodaiqiao_3d_scene_practice.py"),
    ("3D动画关键帧导引", PYQGIS_DIR / "load_baodaiqiao_3d_animation_keyframe_guide.py"),
]


def layer_exists(name: str) -> bool:
    return bool(QgsProject.instance().mapLayersByName(name))


def add_basemap(name: str, source: str):
    if layer_exists(name):
        print(f"底图已存在，跳过：{name}")
        return
    layer = QgsRasterLayer(source, name, "wms")
    if layer.isValid():
        QgsProject.instance().addMapLayer(layer)
        print(f"已加载底图：{name}")
    else:
        print(f"底图加载失败：{name}")


def run_script(label: str, path: Path):
    if not path.exists():
        print(f"脚本不存在，跳过：{label} -> {path}")
        return False
    try:
        print(f"\n--- 加载 {label} ---")
        exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), globals(), globals())
        print(f"完成：{label}")
        return True
    except Exception as exc:
        print(f"失败：{label}；原因：{exc}")
        return False


print("开始加载：宝带桥社区志 AIGC 可视化工作台")
print(f"项目根目录：{PROJECT_ROOT}")

for basemap_name, basemap_source in BASEMAPS:
    add_basemap(basemap_name, basemap_source)

results = []
for label, script_path in WORKBENCH_SCRIPTS:
    results.append((label, run_script(label, script_path)))

try:
    iface.mapCanvas().refresh()
except NameError:
    pass

print("\nAIGC 工作台加载结果：")
for label, ok in results:
    print(f"- {label}: {'OK' if ok else 'FAILED'}")

print("\n建议打开这些图层组合：")
print("1. 高德纯地图_AIGC底图 或 高德卫星_AIGC底图")
print("2. 宝带桥社区志_地名提及统计互动层 / 高频地名_统计标注_可点击")
print("3. 宝带桥社区志_高频地名柱形统计 / 高频地名_提及次数柱形图_3857")
print("4. 宝带桥社区志_时间地名 / 20秒里程碑_时间点_GCJ02")
print("5. 宝带桥社区志_3D沙盘实践，用于 3D Map View")
print("\n使用 Identify Features 或地图提示点击地名/柱体，可查看出现次数、为什么高频、地方志上下文和坐标质量。")
