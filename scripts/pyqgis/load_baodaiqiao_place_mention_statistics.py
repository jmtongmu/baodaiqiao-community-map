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
GROUP_NAME = "宝带桥社区志_地名提及统计互动层"

TOP_MAPPED = DATA_DIR / "baodaiqiao_place_mention_top_mapped_gcj02.geojson"
TOP_MISSING = DATA_DIR / "baodaiqiao_place_mention_top_missing_coords.csv"
STATS = DATA_DIR / "baodaiqiao_place_mention_statistics_curated.csv"


LEVEL_STYLE = {
    "极高频": ("#d83b2d", 8.2),
    "高频": ("#e57f2a", 6.8),
    "中高频": ("#f0c34a", 5.8),
    "中频": ("#5aa469", 4.8),
    "低频": ("#6d8fb8", 3.8),
}


def remove_existing_group() -> None:
    project = QgsProject.instance()
    root = project.layerTreeRoot()
    old = root.findGroup(GROUP_NAME)
    if old:
        layer_ids = [node.layerId() for node in old.findLayers()]
        project.removeMapLayers(layer_ids)
        root.removeChildNode(old)


def load_vector(path: Path, name: str, group) -> QgsVectorLayer:
    layer = QgsVectorLayer(str(path), name, "ogr")
    if not layer.isValid():
        raise RuntimeError(f"图层加载失败：{path}")
    layer.setCrs(QgsCoordinateReferenceSystem("EPSG:4326"))
    QgsProject.instance().addMapLayer(layer, False)
    group.addLayer(layer)
    return layer


def load_table(path: Path, name: str, group) -> QgsVectorLayer:
    layer = QgsVectorLayer(str(path), name, "ogr")
    if not layer.isValid():
        raise RuntimeError(f"表格加载失败：{path}")
    QgsProject.instance().addMapLayer(layer, False)
    group.addLayer(layer)
    return layer


def marker(color: str, size: float) -> QgsMarkerSymbol:
    return QgsMarkerSymbol.createSimple(
        {
            "name": "circle",
            "color": color,
            "outline_color": "255,255,255,230",
            "outline_width": "0.85",
            "size": str(size),
        }
    )


def style_mentions(layer: QgsVectorLayer) -> None:
    categories = []
    for level, (color, size) in LEVEL_STYLE.items():
        categories.append(QgsRendererCategory(level, marker(color, size), level))
    layer.setRenderer(QgsCategorizedSymbolRenderer("mention_level", categories))
    layer.triggerRepaint()


def apply_labels(layer: QgsVectorLayer) -> None:
    settings = QgsPalLayerSettings()
    settings.fieldName = "rank_label"
    settings.enabled = True
    text_format = QgsTextFormat()
    text_format.setFont(QFont("Microsoft YaHei", 9))
    text_format.setSize(8.5)
    text_format.setColor(QColor("#171717"))
    buffer = QgsTextBufferSettings()
    buffer.setEnabled(True)
    buffer.setColor(QColor(255, 255, 255, 235))
    buffer.setSize(1.1)
    text_format.setBuffer(buffer)
    settings.setFormat(text_format)
    layer.setLabelsEnabled(True)
    layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
    layer.triggerRepaint()


def apply_map_tips(layer: QgsVectorLayer) -> None:
    template = """
    <div style="font-family:'Microsoft YaHei'; width: 360px;">
      <h3 style="margin:0 0 6px 0;">[% "rank_label" %]</h3>
      <div><b>类型：</b>[% "place_type" %]　<b>频次级别：</b>[% "mention_level" %]</div>
      <div><b>归并次数：</b>[% "canonical_mention_count" %]　<b>全文字符串次数：</b>[% "raw_surface_count" %]</div>
      <div><b>坐标状态：</b>[% "coordinate_quality" %]</div>
      <div style="margin-top:6px;"><b>为什么高频：</b>[% "reason" %]</div>
      <div style="margin-top:6px;color:#555;"><b>主题线索：</b>[% "top_themes" %]</div>
    </div>
    """
    if hasattr(layer, "setMapTipTemplate"):
        layer.setMapTipTemplate(template)


def add_selection_helper_fields(layer: QgsVectorLayer) -> None:
    layer.setDisplayExpression('"rank_label"')
    apply_map_tips(layer)


remove_existing_group()
root = QgsProject.instance().layerTreeRoot()
group = root.addGroup(GROUP_NAME)

mapped = load_vector(TOP_MAPPED, "高频地名_统计标注_可点击", group)
style_mentions(mapped)
apply_labels(mapped)
add_selection_helper_fields(mapped)

missing = load_table(TOP_MISSING, "高频地名_缺坐标_待对高德卫星图补点", group)
stats = load_table(STATS, "精选地名_提及统计总表", group)

try:
    iface.mapCanvas().setExtent(mapped.extent())
    iface.mapCanvas().refresh()
except NameError:
    pass

print(f"已加载：{GROUP_NAME}")
print(f"可点击高频标注：{mapped.featureCount()} 个；缺坐标高频地名：{missing.featureCount()} 个；精选统计总表：{stats.featureCount()} 条。")
print("使用方法：打开地图提示/Identify Features，点击高频地名点，可查看出现次数、为什么高频、主题线索和坐标质量。")
print("高德卫星图是瓦片底图，不能直接查询其中的文字；交互标注来自本图层，叠加在高德卫星图上使用。")
