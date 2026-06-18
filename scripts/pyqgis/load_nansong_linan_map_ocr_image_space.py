# -*- coding: utf-8 -*-
"""Load Nan Song Lin'an OCR boxes in source-image pixel coordinates.

Run this in the QGIS Python console after opening qgis/nansong_linan6.2.qgz.
This is an image-space review layer, not an OSM-georeferenced layer.
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


MAP_ID = "nansong_linan_map_rapidocr"
IMAGE_RELATIVE = Path("assets/maps/nansong_linan_map.jpg")
GEOJSON_RELATIVE = Path("data/ocr/image_space/nansong_linan_map_rapidocr_ocr_image_space.geojson")
GROUP_NAME = "\u5357\u5b8b\u4e34\u5b89\u56fe_RapidOCR\u539f\u56fe\u6392\u5e03"


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
            "ocr_\u8857\u5df7\u9053\u8def",
            make_fill("255,210,60,65", "220,95,0,220"),
            "\u8857\u5df7\u9053\u8def",
        ),
        QgsRendererCategory(
            "ocr_\u57ce\u9632\u5b98\u7f72",
            make_fill("205,120,255,60", "125,35,190,220"),
            "\u57ce\u9632\u5b98\u7f72",
        ),
        QgsRendererCategory(
            "ocr_\u5bfa\u89c2",
            make_fill("110,220,130,60", "20,135,50,220"),
            "\u5bfa\u89c2",
        ),
        QgsRendererCategory(
            "ocr_\u5c71\u4f53",
            make_fill("160,130,90,60", "100,70,35,220"),
            "\u5c71\u4f53",
        ),
        QgsRendererCategory(
            "ocr_\u6c34\u7cfb",
            make_fill("80,180,255,60", "0,105,210,220"),
            "\u6c34\u7cfb",
        ),
        QgsRendererCategory(
            "ocr_\u6587\u5b57",
            make_fill("255,255,255,45", "70,70,70,210"),
            "\u5176\u4ed6\u6587\u5b57",
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
        if layer.customProperty("linan_ocr_image_space") == "true":
            project.removeMapLayer(layer.id())

    tree_root = project.layerTreeRoot()
    group = tree_root.findGroup(GROUP_NAME)
    if group is not None:
        tree_root.removeChildNode(group)


project = QgsProject.instance()
root = repo_root()
image_path = root / IMAGE_RELATIVE
geojson_path = root / GEOJSON_RELATIVE

remove_existing(project)

tree_root = project.layerTreeRoot()
group = tree_root.insertGroup(0, GROUP_NAME)

raster = QgsRasterLayer(str(image_path), "\u5357\u5b8b\u4e34\u5b89\u56fe_\u539f\u56fe_\u50cf\u7d20\u5750\u6807")
if not raster.isValid():
    raise RuntimeError(f"Cannot load source image: {image_path}")
raster.setCrs(QgsCoordinateReferenceSystem("EPSG:3857"))
raster.setCustomProperty("linan_ocr_image_space", "true")
raster.setCustomProperty("linan_ocr_image_space_map_id", MAP_ID)
project.addMapLayer(raster, False)
group.addLayer(raster)

ocr_layer = QgsVectorLayer(str(geojson_path), "\u5357\u5b8b\u4e34\u5b89\u56fe_RapidOCR\u6587\u5b57\u6846_\u539f\u56fe\u5750\u6807", "ogr")
if not ocr_layer.isValid():
    raise RuntimeError(f"Cannot load OCR GeoJSON: {geojson_path}")
ocr_layer.setCrs(QgsCoordinateReferenceSystem("EPSG:3857"))
ocr_layer.setCustomProperty("linan_ocr_image_space", "true")
ocr_layer.setCustomProperty("linan_ocr_image_space_map_id", MAP_ID)
style_ocr_layer(ocr_layer)
project.addMapLayer(ocr_layer, False)
group.addLayer(ocr_layer)

iface.setActiveLayer(ocr_layer)
iface.zoomToActiveLayer()
print(f"loaded {ocr_layer.featureCount()} RapidOCR image-space text boxes for nansong_linan_map")
