from pathlib import Path

from qgis.core import (
    QgsCategorizedSymbolRenderer,
    QgsCoordinateReferenceSystem,
    QgsFillSymbol,
    QgsLineSymbol,
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
GROUP_NAME = "宝带桥社区志_3D沙盘实践"

STAGE = DATA_DIR / "baodaiqiao_3d_scene_stage_3857.geojson"
BLOCKS = DATA_DIR / "baodaiqiao_3d_scene_place_blocks_3857.geojson"
COLUMNS = DATA_DIR / "baodaiqiao_3d_scene_milestone_columns_3857.geojson"
PATH = DATA_DIR / "baodaiqiao_3d_scene_milestone_path_3857.geojson"

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
    "milestone": "#7b4ab8",
}

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


def rgba(hex_color: str, alpha: int) -> str:
    color = QColor(hex_color)
    return f"{color.red()},{color.green()},{color.blue()},{alpha}"


def fill_symbol(hex_color: str, alpha: int = 150, outline: str = "70,70,70,120", width: str = "0.25") -> QgsFillSymbol:
    return QgsFillSymbol.createSimple(
        {
            "color": rgba(hex_color, alpha),
            "outline_color": outline,
            "outline_width": width,
        }
    )


def style_stage(layer: QgsVectorLayer) -> None:
    symbol = fill_symbol(CLASS_COLORS["stage"], 110, "120,100,70,150", "0.35")
    layer.renderer().setSymbol(symbol)
    layer.triggerRepaint()


def style_by_scene_class(layer: QgsVectorLayer) -> None:
    categories = []
    for scene_class, color in CLASS_COLORS.items():
        categories.append(QgsRendererCategory(scene_class, fill_symbol(color, 150), scene_class))
    layer.setRenderer(QgsCategorizedSymbolRenderer("scene_class", categories))
    layer.triggerRepaint()


def style_by_time(layer: QgsVectorLayer) -> None:
    categories = []
    for time_type, color in TIME_COLORS.items():
        categories.append(QgsRendererCategory(time_type, fill_symbol(color, 185, "255,255,255,180", "0.35"), time_type))
    layer.setRenderer(QgsCategorizedSymbolRenderer("time_type", categories))
    layer.triggerRepaint()


def style_path(layer: QgsVectorLayer) -> None:
    symbol = QgsLineSymbol.createSimple({"color": "30,30,30,190", "width": "0.8", "line_style": "dash"})
    layer.renderer().setSymbol(symbol)
    layer.triggerRepaint()


def apply_labels(layer: QgsVectorLayer, field: str, size: float, enabled: bool = True) -> None:
    settings = QgsPalLayerSettings()
    settings.fieldName = field
    settings.enabled = enabled
    text_format = QgsTextFormat()
    text_format.setFont(QFont("Microsoft YaHei", 9))
    text_format.setSize(size)
    text_format.setColor(QColor("#222222"))
    buffer = QgsTextBufferSettings()
    buffer.setEnabled(True)
    buffer.setSize(1.0)
    buffer.setColor(QColor(255, 255, 255, 220))
    text_format.setBuffer(buffer)
    settings.setFormat(text_format)
    layer.setLabelsEnabled(enabled)
    layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
    layer.triggerRepaint()


def try_apply_3d_extrusion(layer: QgsVectorLayer, height: float, color: str) -> bool:
    try:
        from qgis._3d import QgsPhongMaterialSettings, QgsPolygon3DSymbol, QgsVectorLayer3DRenderer

        material = QgsPhongMaterialSettings()
        if hasattr(material, "setDiffuse"):
            material.setDiffuse(QColor(color))
        elif hasattr(material, "setDiffuseColor"):
            material.setDiffuseColor(QColor(color))

        symbol = QgsPolygon3DSymbol()
        if hasattr(symbol, "setMaterialSettings"):
            symbol.setMaterialSettings(material)
        elif hasattr(symbol, "setMaterial"):
            symbol.setMaterial(material)
        else:
            print(f"3D材质接口不匹配：{layer.name()}，继续尝试只设置拉伸高度。")

        symbol.setExtrusionHeight(height)
        try:
            renderer = QgsVectorLayer3DRenderer(symbol)
        except TypeError:
            renderer = QgsVectorLayer3DRenderer()
            renderer.setSymbol(symbol)
        layer.setRenderer3D(renderer)
        if hasattr(layer, "trigger3DUpdate"):
            layer.trigger3DUpdate()
        return True
    except Exception as exc:
        print(f"未自动启用3D拉伸：{layer.name()}；原因：{exc}")
        return False


remove_existing_group()
root = QgsProject.instance().layerTreeRoot()
group = root.addGroup(GROUP_NAME)

stage = load_layer(STAGE, "3D_社区叙事底座_面", group)
blocks = load_layer(BLOCKS, "3D_地名块体_面", group)
columns = load_layer(COLUMNS, "3D_里程碑意义光柱_面", group)
path = load_layer(PATH, "3D_里程碑时间路径_线", group)

style_stage(stage)
style_by_scene_class(blocks)
style_by_time(columns)
style_path(path)

apply_labels(stage, "label", 9.0, False)
apply_labels(blocks, "name", 8.0, True)
apply_labels(columns, "label", 8.2, True)

stage_3d = try_apply_3d_extrusion(stage, 0.2, CLASS_COLORS["stage"])
blocks_3d = try_apply_3d_extrusion(blocks, 16, CLASS_COLORS["heritage"])
columns_3d = try_apply_3d_extrusion(columns, 95, "#7b4ab8")

try:
    iface.mapCanvas().setExtent(stage.extent())
    iface.mapCanvas().refresh()
except NameError:
    pass

print(f"已加载：{GROUP_NAME}")
print(f"底座 {stage.featureCount()} 个；地名块体 {blocks.featureCount()} 个；里程碑光柱 {columns.featureCount()} 个；时间路径 {path.featureCount()} 条。")
print("实践步骤：打开 视图 > 新建3D地图视图，然后把相机俯仰调到约45度。")
print("本版已改用 EPSG:3857 米制图层，3D高度单位按米处理。")
print("若自动3D拉伸仍未生效：在图层属性 > 3D视图 中启用3D渲染，块体/光柱使用字段 height_m 作为拉伸高度。")
print(f"自动3D状态：底座={stage_3d}，块体={blocks_3d}，光柱={columns_3d}")
