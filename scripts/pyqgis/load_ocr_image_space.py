# -*- coding: utf-8 -*-
"""Load original-map OCR boxes in image-space coordinates.

This displays OCR boxes on top of the original image, preserving the layout of
the source map. It is intentionally separate from modern-map georeferencing.
"""

from pathlib import Path

from qgis.PyQt.QtGui import QColor, QFont
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsFillSymbol,
    QgsPalLayerSettings,
    QgsProject,
    QgsRasterLayer,
    QgsSingleSymbolRenderer,
    QgsTextBufferSettings,
    QgsTextFormat,
    QgsVectorLayer,
    QgsVectorLayerSimpleLabeling,
)


MAP_ID = "jingchengtu_windows_ocr"
IMAGE_RELATIVE = Path("assets/maps/京城图.png")
GEOJSON_RELATIVE = Path("data/ocr/image_space/jingchengtu_windows_ocr_ocr_image_space.geojson")
GROUP_NAME = "京城图_OCR原图排布"


def repo_root():
    home = QgsProject.instance().homePath()
    if home:
        return Path(home).resolve().parent
    return Path.cwd()


def style_ocr_layer(layer):
    symbol = QgsFillSymbol.createSimple(
        {
            "color": "255,255,0,60",
            "outline_color": "220,30,30,210",
            "outline_width": "0.35",
        }
    )
    layer.setRenderer(QgsSingleSymbolRenderer(symbol))

    label_settings = QgsPalLayerSettings()
    label_settings.fieldName = "text"
    label_settings.enabled = True
    text_format = QgsTextFormat()
    text_format.setFont(QFont("Microsoft YaHei"))
    text_format.setSize(8)
    buffer = QgsTextBufferSettings()
    buffer.setEnabled(True)
    buffer.setSize(1.0)
    buffer.setColor(QColor(255, 255, 255, 230))
    text_format.setBuffer(buffer)
    label_settings.setFormat(text_format)
    layer.setLabelsEnabled(True)
    layer.setLabeling(QgsVectorLayerSimpleLabeling(label_settings))


def remove_existing(project):
    for layer in list(project.mapLayers().values()):
        if layer.customProperty("linan_ocr_image_space") == "true":
            project.removeMapLayer(layer.id())


project = QgsProject.instance()
root = repo_root()
image_path = root / IMAGE_RELATIVE
geojson_path = root / GEOJSON_RELATIVE

remove_existing(project)

tree_root = project.layerTreeRoot()
group = tree_root.findGroup(GROUP_NAME)
if group is None:
    group = tree_root.insertGroup(0, GROUP_NAME)

raster = QgsRasterLayer(str(image_path), "京城图_原图")
if not raster.isValid():
    raise RuntimeError(f"无法加载原图：{image_path}")
raster.setCrs(QgsCoordinateReferenceSystem("EPSG:3857"))
raster.setCustomProperty("linan_ocr_image_space", "true")
project.addMapLayer(raster, False)
group.addLayer(raster)

ocr_layer = QgsVectorLayer(str(geojson_path), "京城图_OCR文字框_原图坐标", "ogr")
if not ocr_layer.isValid():
    raise RuntimeError(f"无法加载 OCR GeoJSON：{geojson_path}")
ocr_layer.setCrs(QgsCoordinateReferenceSystem("EPSG:3857"))
ocr_layer.setCustomProperty("linan_ocr_image_space", "true")
style_ocr_layer(ocr_layer)
project.addMapLayer(ocr_layer, False)
group.addLayer(ocr_layer)

iface.setActiveLayer(ocr_layer)
iface.zoomToActiveLayer()
print(f"已加载 {ocr_layer.featureCount()} 个 OCR 原图坐标文字框")
