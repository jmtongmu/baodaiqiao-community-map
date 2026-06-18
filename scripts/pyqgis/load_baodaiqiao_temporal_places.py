from pathlib import Path

from qgis.core import (
    QgsCategorizedSymbolRenderer,
    QgsCoordinateReferenceSystem,
    QgsMarkerSymbol,
    QgsPalLayerSettings,
    QgsProject,
    QgsRendererCategory,
    QgsTextBufferSettings,
    QgsTextFormat,
    QgsVectorLayer,
    QgsVectorLayerSimpleLabeling,
)
from qgis.PyQt.QtGui import QColor, QFont


PROJECT_ROOT = Path(r"\\10.100.66.31\tongmu_file\2025\AIwork\地方志\社区志")
DATA_DIR = PROJECT_ROOT / "data" / "baodaiqiao"
GROUP_NAME = "宝带桥社区志_时间地名"

CURATED_POINTS = DATA_DIR / "baodaiqiao_places_temporal_points_curated_gaode_gcj02.geojson"
ALL_POINTS = DATA_DIR / "baodaiqiao_places_temporal_points_gaode_gcj02.geojson"
MILESTONE_POINTS = DATA_DIR / "baodaiqiao_timeline_milestone_points_gaode_gcj02.geojson"
CURATED_SEQUENCE = DATA_DIR / "baodaiqiao_places_temporal_sequence_curated.csv"
FULL_SEQUENCE = DATA_DIR / "baodaiqiao_places_temporal_sequence.csv"
MISSING_CURATED = DATA_DIR / "baodaiqiao_places_temporal_missing_coords_curated.csv"

TIME_STYLE = [
    ("古代-清末", "#8b5e34", "古代-清末"),
    ("民国时期", "#5b7f95", "民国时期"),
    ("集体化与农业建设", "#4f8a54", "集体化与农业建设"),
    ("改革开放初期", "#b9822e", "改革开放初期"),
    ("开发区建设", "#d45b43", "开发区建设"),
    ("社区成立与城市更新", "#3867b7", "社区成立与城市更新"),
    ("运河文旅更新", "#7b4ab8", "运河文旅更新"),
    ("无明确时间", "#8b8b8b", "无明确时间"),
]


def remove_existing_group() -> None:
    project = QgsProject.instance()
    root = project.layerTreeRoot()
    old = root.findGroup(GROUP_NAME)
    if old:
        layer_ids = [node.layerId() for node in old.findLayers()]
        project.removeMapLayers(layer_ids)
        root.removeChildNode(old)


def add_layer_to_group(layer: QgsVectorLayer, group):
    QgsProject.instance().addMapLayer(layer, False)
    group.addLayer(layer)
    return layer


def load_vector(path: Path, name: str, group) -> QgsVectorLayer:
    layer = QgsVectorLayer(str(path), name, "ogr")
    if not layer.isValid():
        raise RuntimeError(f"图层加载失败：{path}")
    layer.setCrs(QgsCoordinateReferenceSystem("EPSG:4326"))
    return add_layer_to_group(layer, group)


def load_table(path: Path, name: str, group) -> QgsVectorLayer:
    layer = QgsVectorLayer(str(path), name, "ogr")
    if not layer.isValid():
        raise RuntimeError(f"表格加载失败：{path}")
    return add_layer_to_group(layer, group)


def apply_labels(layer: QgsVectorLayer, label_field: str, size: float = 8.5) -> None:
    settings = QgsPalLayerSettings()
    settings.fieldName = label_field
    settings.enabled = True
    text_format = QgsTextFormat()
    text_format.setFont(QFont("Microsoft YaHei", 9))
    text_format.setSize(size)
    text_format.setColor(QColor("#222222"))
    buffer = QgsTextBufferSettings()
    buffer.setEnabled(True)
    buffer.setColor(QColor("#ffffff"))
    buffer.setSize(0.9)
    text_format.setBuffer(buffer)
    settings.setFormat(text_format)
    layer.setLabelsEnabled(True)
    layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
    layer.triggerRepaint()


def marker_symbol(color: str, size: float, stroke: str = "#ffffff", stroke_width: float = 0.75) -> QgsMarkerSymbol:
    return QgsMarkerSymbol.createSimple(
        {
            "name": "circle",
            "color": color,
            "outline_color": stroke,
            "outline_width": str(stroke_width),
            "size": str(size),
        }
    )


def style_by_time(layer: QgsVectorLayer, size: float = 4.2) -> None:
    categories = [QgsRendererCategory(value, marker_symbol(color, size), label) for value, color, label in TIME_STYLE]
    layer.setRenderer(QgsCategorizedSymbolRenderer("time_type", categories))
    layer.triggerRepaint()


def add_time_subset_layers(path: Path, parent_group, source_name: str) -> None:
    subset_group = parent_group.addGroup(f"{source_name}_按时间类型")
    for time_type, color, _ in TIME_STYLE:
        layer = QgsVectorLayer(str(path), f"{source_name}_{time_type}", "ogr")
        if not layer.isValid():
            continue
        layer.setCrs(QgsCoordinateReferenceSystem("EPSG:4326"))
        escaped = time_type.replace("'", "''")
        layer.setSubsetString(f"\"time_type\" = '{escaped}'")
        if layer.featureCount() == 0:
            continue
        QgsProject.instance().addMapLayer(layer, False)
        subset_group.addLayer(layer)
        layer.renderer().setSymbol(marker_symbol(color, 4.0))
        apply_labels(layer, "gazetteer_name", 8.0)


remove_existing_group()
root = QgsProject.instance().layerTreeRoot()
group = root.addGroup(GROUP_NAME)

curated = load_vector(CURATED_POINTS, "社区志地名_精选时间点_GCJ02", group)
style_by_time(curated, 4.8)
apply_labels(curated, "gazetteer_name", 8.5)

milestones = load_vector(MILESTONE_POINTS, "20秒里程碑_时间点_GCJ02", group)
style_by_time(milestones, 6.4)
apply_labels(milestones, "story_label", 9.0)

all_points = load_vector(ALL_POINTS, "社区志地名_全量可定位点_GCJ02", group)
style_by_time(all_points, 3.2)
all_points.setScaleBasedVisibility(True)
all_points.setMinimumScale(8000)
all_points.setMaximumScale(1)

add_time_subset_layers(CURATED_POINTS, group, "精选地名")

load_table(CURATED_SEQUENCE, "精选地名_时间序列表", group)
load_table(FULL_SEQUENCE, "全文地名_时间序列表", group)
load_table(MISSING_CURATED, "精选地名_待补高德坐标", group)

try:
    iface.mapCanvas().setExtent(curated.extent())
    iface.mapCanvas().refresh()
except NameError:
    pass

print(f"已加载：{GROUP_NAME}")
print(f"精选时间点：{curated.featureCount()} 个；20秒里程碑：{milestones.featureCount()} 个；全量可定位点：{all_points.featureCount()} 个")
print("点位坐标为 GCJ-02 经纬度，图层声明 EPSG:4326，用于贴合高德 XYZ 矢量底图。")
print("20秒里程碑层已使用 story_label 标注年份、地点和里程碑意义；完整意义见 milestone_significance 字段。")
print("未自动定位的精选地名已放入表：精选地名_待补高德坐标。")
