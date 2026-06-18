from pathlib import Path

from qgis.core import (
    QgsCategorizedSymbolRenderer,
    QgsCoordinateReferenceSystem,
    QgsFillSymbol,
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


PROJECT_ROOT = Path(r"F:\AIGC\baodaiqiao-community-map")
DATA_DIR = PROJECT_ROOT / "data" / "baodaiqiao"
GROUP_NAME = "宝带桥社区志_高频地名柱形统计"

COLUMNS = DATA_DIR / "baodaiqiao_place_mention_columns_3857.geojson"
LABELS = DATA_DIR / "baodaiqiao_place_mention_column_labels_3857.geojson"
STATS = DATA_DIR / "baodaiqiao_place_mention_statistics_curated.csv"
MISSING = DATA_DIR / "baodaiqiao_place_mention_top_missing_coords.csv"

LEVEL_STYLE = {
    "极高频": ("#d83b2d", 210),
    "高频": ("#e57f2a", 195),
    "中高频": ("#f0c34a", 185),
    "中频": ("#5aa469", 175),
    "低频": ("#6d8fb8", 165),
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


def rgba(hex_color: str, alpha: int) -> str:
    color = QColor(hex_color)
    return f"{color.red()},{color.green()},{color.blue()},{alpha}"


def fill_symbol(hex_color: str, alpha: int) -> QgsFillSymbol:
    return QgsFillSymbol.createSimple(
        {
            "color": rgba(hex_color, alpha),
            "outline_color": "255,255,255,220",
            "outline_width": "0.35",
        }
    )


def point_symbol(hex_color: str, size: float = 2.4) -> QgsMarkerSymbol:
    return QgsMarkerSymbol.createSimple(
        {
            "name": "circle",
            "color": rgba(hex_color, 230),
            "outline_color": "30,30,30,180",
            "outline_width": "0.35",
            "size": str(size),
        }
    )


def style_columns(layer: QgsVectorLayer) -> None:
    categories = []
    for level, (color, alpha) in LEVEL_STYLE.items():
        categories.append(QgsRendererCategory(level, fill_symbol(color, alpha), level))
    layer.setRenderer(QgsCategorizedSymbolRenderer("mention_level", categories))
    layer.triggerRepaint()


def style_label_points(layer: QgsVectorLayer) -> None:
    symbol = point_symbol("#111111", 1.8)
    layer.renderer().setSymbol(symbol)
    layer.triggerRepaint()


def apply_labels(layer: QgsVectorLayer, field: str = "label", size: float = 8.0) -> None:
    settings = QgsPalLayerSettings()
    settings.fieldName = field
    settings.enabled = True
    text_format = QgsTextFormat()
    text_format.setFont(QFont("Microsoft YaHei", 9))
    text_format.setSize(size)
    text_format.setColor(QColor("#111111"))
    buffer = QgsTextBufferSettings()
    buffer.setEnabled(True)
    buffer.setColor(QColor(255, 255, 255, 235))
    buffer.setSize(1.0)
    text_format.setBuffer(buffer)
    settings.setFormat(text_format)
    layer.setLabelsEnabled(True)
    layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
    layer.triggerRepaint()


def property_key_for_extrusion():
    try:
        from qgis._3d import QgsAbstract3DSymbol

        containers = [QgsAbstract3DSymbol]
        if hasattr(QgsAbstract3DSymbol, "Property"):
            containers.append(QgsAbstract3DSymbol.Property)
        names = [
            "PropertyExtrusionHeight",
            "ExtrusionHeight",
            "PropertyHeight",
            "Height",
            "Extrusion",
        ]
        for container in containers:
            for name in names:
                if hasattr(container, name):
                    return getattr(container, name)
    except Exception:
        return None
    return None


def try_apply_3d_columns(layer: QgsVectorLayer) -> bool:
    try:
        from qgis._3d import QgsPhongMaterialSettings, QgsPolygon3DSymbol, QgsVectorLayer3DRenderer
        from qgis.core import QgsProperty

        material = QgsPhongMaterialSettings()
        if hasattr(material, "setDiffuse"):
            material.setDiffuse(QColor("#d83b2d"))
        elif hasattr(material, "setDiffuseColor"):
            material.setDiffuseColor(QColor("#d83b2d"))

        symbol = QgsPolygon3DSymbol()
        if hasattr(symbol, "setMaterialSettings"):
            symbol.setMaterialSettings(material)
        elif hasattr(symbol, "setMaterial"):
            symbol.setMaterial(material)

        # Give a useful fallback, then try to bind per-feature height_m.
        if hasattr(symbol, "setExtrusionHeight"):
            symbol.setExtrusionHeight(60)

        prop_key = property_key_for_extrusion()
        if prop_key is not None and hasattr(symbol, "dataDefinedProperties") and hasattr(symbol, "setDataDefinedProperties"):
            props = symbol.dataDefinedProperties()
            props.setProperty(prop_key, QgsProperty.fromField("height_m"))
            symbol.setDataDefinedProperties(props)
            print("已尝试将3D柱高绑定到 height_m 字段。")
        else:
            print("当前QGIS Python 3D接口未暴露字段拉伸属性；已设置统一默认高度，仍可手动选择 height_m。")

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
        print(f"未自动启用柱形3D拉伸：{exc}")
        return False


def apply_map_tips(layer: QgsVectorLayer) -> None:
    template = """
    <div style="font-family:'Microsoft YaHei'; width: 360px;">
      <h3 style="margin:0 0 6px 0;">[% "label" %]</h3>
      <div><b>柱高：</b>[% "height_m" %] m　<b>柱底半径：</b>[% "radius_m" %] m</div>
      <div><b>频次级别：</b>[% "mention_level" %]　<b>坐标状态：</b>[% "coordinate_quality" %]</div>
      <div style="margin-top:6px;"><b>为什么高频：</b>[% "reason" %]</div>
      <div style="margin-top:6px;color:#555;"><b>主题线索：</b>[% "top_themes" %]</div>
    </div>
    """
    if hasattr(layer, "setMapTipTemplate"):
        layer.setMapTipTemplate(template)


def apply_label_map_tips(layer: QgsVectorLayer) -> None:
    template = """
    <div style="font-family:'Microsoft YaHei'; width: 360px;">
      <h3 style="margin:0 0 6px 0;">[% "rank_label" %]</h3>
      <div><b>提及次数：</b>[% "canonical_mention_count" %] 次</div>
      <div><b>柱高：</b>[% "height_m" %] m　<b>柱底半径：</b>[% "radius_m" %] m</div>
      <div><b>坐标质量：</b>[% "coordinate_quality" %]</div>
      <div style="margin-top:6px;"><b>为什么高频：</b>[% "reason" %]</div>
    </div>
    """
    if hasattr(layer, "setMapTipTemplate"):
        layer.setMapTipTemplate(template)


remove_existing_group()
root = QgsProject.instance().layerTreeRoot()
group = root.addGroup(GROUP_NAME)

columns = load_vector(COLUMNS, "高频地名_提及次数柱形图_3857", group)
style_columns(columns)
apply_labels(columns)
apply_map_tips(columns)
columns.setDisplayExpression('"label"')

labels = load_vector(LABELS, "高频地名_柱顶数值标签_全部", group)
style_label_points(labels)
apply_labels(labels, "label_display", 8.2)
apply_label_map_tips(labels)
labels.setDisplayExpression('"label_display"')

labels_top10 = load_vector(LABELS, "高频地名_柱顶数值标签_Top10", group)
labels_top10.setSubsetString('"rank_num" <= 10')
style_label_points(labels_top10)
apply_labels(labels_top10, "label_detail", 8.6)
apply_label_map_tips(labels_top10)
labels_top10.setDisplayExpression('"label_detail"')

stats = load_table(STATS, "精选地名_提及统计总表", group)
missing = load_table(MISSING, "高频地名_缺坐标_待补点", group)

auto_3d = try_apply_3d_columns(columns)

try:
    iface.mapCanvas().setExtent(columns.extent())
    iface.mapCanvas().refresh()
except NameError:
    pass

print(f"已加载：{GROUP_NAME}")
print(f"柱形图：{columns.featureCount()} 根；柱顶标签：{labels.featureCount()} 个；统计总表：{stats.featureCount()} 条；待补点：{missing.featureCount()} 条。")
print("柱高字段：height_m；频次字段：canonical_mention_count；标签字段：label。")
print("3D数值显示：默认可开“柱顶数值标签_Top10”；需要全部数值时打开“柱顶数值标签_全部”。")
print("在 3D Map View 中查看柱形。如果柱高没有按频次变化，请在图层属性 > 3D视图 中把拉伸高度字段手动设为 height_m。")
print(f"自动3D状态：{auto_3d}")
