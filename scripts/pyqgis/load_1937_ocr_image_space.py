# -*- coding: utf-8 -*-
"""Load 1937 map OCR boxes in source-image pixel coordinates.

Run this in the QGIS Python console. It loads the original 1937 image and the
RapidOCR text boxes without georeferencing them to modern map coordinates.
"""

from pathlib import Path

from qgis.PyQt.QtGui import QColor, QFont
from qgis.core import (
    QgsCategorizedSymbolRenderer,
    QgsCoordinateReferenceSystem,
    QgsFillSymbol,
    QgsPalLayerSettings,
    QgsProject,
    QgsRasterLayer,
    QgsRendererCategory,
    QgsTextBufferSettings,
    QgsTextFormat,
    QgsVectorLayer,
    QgsVectorLayerSimpleLabeling,
)


IMAGE_RELATIVE = Path("assets/maps/1937.jpg")
GEOJSON_RELATIVE = Path("data/ocr/image_space/1937_rapidocr_ocr_image_space.geojson")
GROUP_NAME = "1937地图_RapidOCR原图排布"
OLD_GROUP_NAMES = ["京城图_OCR原图排布", GROUP_NAME]


def repo_root():
    home = QgsProject.instance().homePath()
    if home:
        return Path(home).resolve().parent
    return Path.cwd()


def make_fill(color, outline):
    return QgsFillSymbol.createSimple(
        {
            "color": color,
            "outline_color": outline,
            "outline_width": "0.35",
        }
    )


def style_ocr_layer(layer):
    categories = [
        QgsRendererCategory(
            "ocr_街巷道路",
            make_fill("255,210,60,65", "220,95,0,220"),
            "街巷道路",
        ),
        QgsRendererCategory(
            "ocr_水系",
            make_fill("80,180,255,60", "0,105,210,220"),
            "水系",
        ),
        QgsRendererCategory(
            "ocr_城防官署",
            make_fill("205,120,255,60", "125,35,190,220"),
            "城防官署",
        ),
        QgsRendererCategory(
            "ocr_寺观",
            make_fill("110,220,130,60", "20,135,50,220"),
            "寺观",
        ),
        QgsRendererCategory(
            "ocr_山体",
            make_fill("160,130,90,60", "100,70,35,220"),
            "山体",
        ),
        QgsRendererCategory(
            "ocr_文字",
            make_fill("255,255,255,45", "70,70,70,210"),
            "其他文字",
        ),
    ]
    layer.setRenderer(QgsCategorizedSymbolRenderer("category", categories))

    label_settings = QgsPalLayerSettings()
    label_settings.fieldName = "text"
    label_settings.enabled = True
    text_format = QgsTextFormat()
    text_format.setFont(QFont("Microsoft YaHei"))
    text_format.setSize(7)
    text_format.setColor(QColor(30, 30, 30))
    buffer = QgsTextBufferSettings()
    buffer.setEnabled(True)
    buffer.setSize(0.8)
    buffer.setColor(QColor(255, 255, 255, 235))
    text_format.setBuffer(buffer)
    label_settings.setFormat(text_format)
    layer.setLabelsEnabled(True)
    layer.setLabeling(QgsVectorLayerSimpleLabeling(label_settings))


def remove_existing(project):
    for layer in list(project.mapLayers().values()):
        if (
            layer.customProperty("linan_ocr_image_space") == "true"
            or layer.customProperty("linan_1937_ocr_image_space") == "true"
        ):
            project.removeMapLayer(layer.id())

    tree_root = project.layerTreeRoot()
    for group_name in OLD_GROUP_NAMES:
        group = tree_root.findGroup(group_name)
        if group is not None:
            tree_root.removeChildNode(group)


project = QgsProject.instance()
root = repo_root()
image_path = root / IMAGE_RELATIVE
geojson_path = root / GEOJSON_RELATIVE

remove_existing(project)

tree_root = project.layerTreeRoot()
group = tree_root.insertGroup(0, GROUP_NAME)

raster = QgsRasterLayer(str(image_path), "1937原图_像素坐标")
if not raster.isValid():
    raise RuntimeError(f"无法加载原图：{image_path}")
raster.setCrs(QgsCoordinateReferenceSystem("EPSG:3857"))
raster.setCustomProperty("linan_1937_ocr_image_space", "true")
project.addMapLayer(raster, False)
group.addLayer(raster)

ocr_layer = QgsVectorLayer(str(geojson_path), "1937_RapidOCR文字框_原图坐标", "ogr")
if not ocr_layer.isValid():
    raise RuntimeError(f"无法加载 OCR GeoJSON：{geojson_path}")
ocr_layer.setCrs(QgsCoordinateReferenceSystem("EPSG:3857"))
ocr_layer.setCustomProperty("linan_1937_ocr_image_space", "true")
style_ocr_layer(ocr_layer)
project.addMapLayer(ocr_layer, False)
group.addLayer(ocr_layer)

iface.setActiveLayer(ocr_layer)
iface.zoomToActiveLayer()
print(f"已加载 1937 原图与 {ocr_layer.featureCount()} 个 RapidOCR 原图坐标文字框")
