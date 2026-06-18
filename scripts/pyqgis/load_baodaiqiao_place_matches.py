from pathlib import Path

from qgis.core import (
    QgsCategorizedSymbolRenderer,
    QgsPalLayerSettings,
    QgsProject,
    QgsRendererCategory,
    QgsSimpleMarkerSymbolLayer,
    QgsSymbol,
    QgsTextFormat,
    QgsVectorLayer,
    QgsVectorLayerSimpleLabeling,
)
from qgis.PyQt.QtGui import QColor, QFont


PROJECT_ROOT = Path(r"F:\AIGC\baodaiqiao-community-map")
DATA_DIR = PROJECT_ROOT / "data" / "baodaiqiao"


def add_geojson_layer(path: Path, name: str, label_field: str) -> QgsVectorLayer:
    layer = QgsVectorLayer(str(path), name, "ogr")
    if not layer.isValid():
        raise RuntimeError(f"图层加载失败：{path}")
    QgsProject.instance().addMapLayer(layer)
    settings = QgsPalLayerSettings()
    settings.fieldName = label_field
    settings.enabled = True
    text_format = QgsTextFormat()
    text_format.setFont(QFont("Microsoft YaHei", 9))
    text_format.setSize(9)
    text_format.setColor(QColor("#222222"))
    settings.setFormat(text_format)
    layer.setLabelsEnabled(True)
    layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
    layer.triggerRepaint()
    return layer


def style_match_layer(layer: QgsVectorLayer) -> None:
    categories = []
    style_defs = [
        ("matched", "#12a05c", "可靠匹配"),
        ("review", "#f08a24", "待人工校对"),
    ]
    for value, color, label in style_defs:
        symbol = QgsSymbol.defaultSymbol(layer.geometryType())
        symbol.deleteSymbolLayer(0)
        marker = QgsSimpleMarkerSymbolLayer()
        marker.setShape(QgsSimpleMarkerSymbolLayer.Circle)
        marker.setColor(QColor(color))
        marker.setStrokeColor(QColor("#ffffff"))
        marker.setStrokeWidth(0.8)
        marker.setSize(4.2)
        symbol.appendSymbolLayer(marker)
        categories.append(QgsRendererCategory(value, symbol, label))
    layer.setRenderer(QgsCategorizedSymbolRenderer("match_status", categories))
    layer.triggerRepaint()


def style_osm_layer(layer: QgsVectorLayer) -> None:
    symbol = QgsSymbol.defaultSymbol(layer.geometryType())
    symbol.deleteSymbolLayer(0)
    marker = QgsSimpleMarkerSymbolLayer()
    marker.setShape(QgsSimpleMarkerSymbolLayer.Circle)
    marker.setColor(QColor("#777777"))
    marker.setStrokeColor(QColor("#ffffff"))
    marker.setStrokeWidth(0.4)
    marker.setSize(2.2)
    symbol.appendSymbolLayer(marker)
    layer.renderer().setSymbol(symbol)
    layer.triggerRepaint()


matched = add_geojson_layer(
    DATA_DIR / "baodaiqiao_place_osm_matches.geojson",
    "宝带桥社区志地名_匹配与待校对",
    "gazetteer_name",
)
style_match_layer(matched)

osm = add_geojson_layer(
    DATA_DIR / "baodaiqiao_osm_named_features.geojson",
    "宝带桥范围_OSM命名要素",
    "osm_name",
)
style_osm_layer(osm)
osm.setScaleBasedVisibility(True)
osm.setMinimumScale(8000)
osm.setMaximumScale(1)

checklist_path = DATA_DIR / "baodaiqiao_gaode_place_checklist.csv"
checklist = QgsVectorLayer(str(checklist_path), "社区志地名_高德底图核对清单", "ogr")
if checklist.isValid():
    QgsProject.instance().addMapLayer(checklist)

print("已加载宝带桥社区志地名匹配图层。")
print("绿色为可靠匹配，橙色为待人工校对。建议先筛选 match_status = 'matched'。")
print("已加载无几何核对清单：社区志地名_高德底图核对清单。")
