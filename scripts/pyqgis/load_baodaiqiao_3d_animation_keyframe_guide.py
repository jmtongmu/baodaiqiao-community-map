from pathlib import Path

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsLineSymbol,
    QgsMarkerSymbol,
    QgsPalLayerSettings,
    QgsProject,
    QgsTextBufferSettings,
    QgsTextFormat,
    QgsVectorLayer,
    QgsVectorLayerSimpleLabeling,
)
from qgis.PyQt.QtGui import QColor, QFont


PROJECT_ROOT = Path(r"F:\AIGC\baodaiqiao-community-map")
DATA_DIR = PROJECT_ROOT / "data" / "baodaiqiao"
GROUP_NAME = "宝带桥社区志_3D动画关键帧导引"

TARGETS = DATA_DIR / "baodaiqiao_3d_animation_keyframe_targets_3857.geojson"
PATH = DATA_DIR / "baodaiqiao_3d_animation_camera_path_3857.geojson"
CSV = DATA_DIR / "baodaiqiao_3d_animation_keyframes.csv"


def remove_existing_group() -> None:
    project = QgsProject.instance()
    root = project.layerTreeRoot()
    old = root.findGroup(GROUP_NAME)
    if old:
        layer_ids = [node.layerId() for node in old.findLayers()]
        project.removeMapLayers(layer_ids)
        root.removeChildNode(old)


def load_layer(path: Path, name: str, group) -> QgsVectorLayer:
    layer = QgsVectorLayer(str(path), name, "ogr")
    if not layer.isValid():
        raise RuntimeError(f"图层加载失败：{path}")
    layer.setCrs(QgsCoordinateReferenceSystem("EPSG:3857"))
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


def apply_labels(layer: QgsVectorLayer, field: str, size: float) -> None:
    settings = QgsPalLayerSettings()
    settings.fieldName = field
    settings.enabled = True
    text_format = QgsTextFormat()
    text_format.setFont(QFont("Microsoft YaHei", 9))
    text_format.setSize(size)
    text_format.setColor(QColor("#111111"))
    buffer = QgsTextBufferSettings()
    buffer.setEnabled(True)
    buffer.setColor(QColor(255, 255, 255, 230))
    buffer.setSize(1.2)
    text_format.setBuffer(buffer)
    settings.setFormat(text_format)
    layer.setLabelsEnabled(True)
    layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
    layer.triggerRepaint()


def style_targets(layer: QgsVectorLayer) -> None:
    symbol = QgsMarkerSymbol.createSimple(
        {
            "name": "diamond",
            "color": "255,230,90,230",
            "outline_color": "30,30,30,210",
            "outline_width": "0.7",
            "size": "5.2",
        }
    )
    layer.renderer().setSymbol(symbol)
    layer.triggerRepaint()


def style_path(layer: QgsVectorLayer) -> None:
    symbol = QgsLineSymbol.createSimple({"color": "255,210,40,210", "width": "0.9", "line_style": "dash"})
    layer.renderer().setSymbol(symbol)
    layer.triggerRepaint()


remove_existing_group()
root = QgsProject.instance().layerTreeRoot()
group = root.addGroup(GROUP_NAME)

targets = load_layer(TARGETS, "动画关键帧目标点_K0-K6", group)
path = load_layer(PATH, "动画镜头目标路径_20秒", group)
table = load_table(CSV, "动画关键帧参数表", group)

style_targets(targets)
style_path(path)
apply_labels(targets, "label", 9.0)

try:
    iface.mapCanvas().setExtent(targets.extent())
    iface.mapCanvas().refresh()
except NameError:
    pass

print(f"已加载：{GROUP_NAME}")
print("K0-K6 已作为 3D 镜头目标点加载。")
print("在 3D Map View 中依次把视角对准 K0-K6，点击动画面板的 Add Keyframe，按表格 time_s 设置时间。")
print("关键帧参数表字段：time_s、camera_distance_m、pitch_deg、heading_deg、visible_focus、narration。")
