# -*- coding: utf-8 -*-
"""Load Nan Song Lin'an OCR boxes after pixel-to-OSM registration.

Run this in the QGIS Python console after generating:
  data/ocr/osm_space/nansong_linan_map_rapidocr_osm_boxes.geojson
  data/ocr/osm_space/nansong_linan_map_rapidocr_osm_points.geojson
"""

from pathlib import Path

from qgis.PyQt.QtGui import QColor, QFont
from qgis.core import (
    QgsCategorizedSymbolRenderer,
    QgsCoordinateReferenceSystem,
    QgsFillSymbol,
    QgsMarkerSymbol,
    QgsPalLayerSettings,
    QgsProject,
    QgsRasterLayer,
    QgsRendererCategory,
    QgsTextBufferSettings,
    QgsTextFormat,
    QgsVectorLayer,
    QgsVectorLayerSimpleLabeling,
)


GROUP_NAME = "\u5357\u5b8b\u4e34\u5b89\u56fe_OSM\u914d\u51c6OCR"
BOXES_RELATIVE = Path("data/ocr/osm_space/nansong_linan_map_rapidocr_osm_boxes.geojson")
POINTS_RELATIVE = Path("data/ocr/osm_space/nansong_linan_map_rapidocr_osm_points.geojson")
GEOREF_IMAGE_RELATIVE = Path("qgis/georef/nansong_linan_map_osm_affine.jpg")
CUSTOM_PROPERTY = "linan_nansong_linan_map_osm_registered"


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


def style_box_layer(layer):
    categories = [
        QgsRendererCategory(
            "ocr_\u8857\u5df7\u9053\u8def",
            make_fill("255,190,0,65", "220,90,0,230"),
            "\u8857\u5df7\u9053\u8def",
        ),
        QgsRendererCategory(
            "ocr_\u57ce\u9632\u5b98\u7f72",
            make_fill("210,120,255,65", "120,35,190,230"),
            "\u57ce\u9632\u5b98\u7f72",
        ),
        QgsRendererCategory(
            "ocr_\u5bfa\u89c2",
            make_fill("80,220,120,65", "10,135,45,230"),
            "\u5bfa\u89c2",
        ),
        QgsRendererCategory(
            "ocr_\u5c71\u4f53",
            make_fill("160,120,75,65", "95,60,20,230"),
            "\u5c71\u4f53",
        ),
        QgsRendererCategory(
            "ocr_\u6c34\u7cfb",
            make_fill("60,170,255,65", "0,95,220,230"),
            "\u6c34\u7cfb",
        ),
        QgsRendererCategory(
            "ocr_\u6587\u5b57",
            make_fill("255,255,255,45", "65,65,65,220"),
            "\u5176\u4ed6\u6587\u5b57",
        ),
    ]
    layer.setRenderer(QgsCategorizedSymbolRenderer("category", categories))

    label_settings = QgsPalLayerSettings()
    label_settings.fieldName = "text"
    label_settings.enabled = True
    text_format = QgsTextFormat()
    text_format.setFont(QFont("Microsoft YaHei"))
    text_format.setSize(8)
    text_format.setColor(QColor(25, 25, 25))
    buffer = QgsTextBufferSettings()
    buffer.setEnabled(True)
    buffer.setSize(0.9)
    buffer.setColor(QColor(255, 255, 255, 235))
    text_format.setBuffer(buffer)
    label_settings.setFormat(text_format)
    layer.setLabelsEnabled(True)
    layer.setLabeling(QgsVectorLayerSimpleLabeling(label_settings))


def style_point_layer(layer):
    symbol = QgsMarkerSymbol.createSimple(
        {
            "name": "circle",
            "color": "255,70,40,180",
            "outline_color": "255,255,255,230",
            "outline_width": "0.5",
            "size": "2.2",
        }
    )
    layer.renderer().setSymbol(symbol)


def remove_existing(project):
    for layer in list(project.mapLayers().values()):
        if layer.customProperty(CUSTOM_PROPERTY) == "true":
            project.removeMapLayer(layer.id())
    group = project.layerTreeRoot().findGroup(GROUP_NAME)
    if group is not None:
        project.layerTreeRoot().removeChildNode(group)


project = QgsProject.instance()
root = repo_root()
boxes_path = root / BOXES_RELATIVE
points_path = root / POINTS_RELATIVE
georef_image_path = root / GEOREF_IMAGE_RELATIVE

if not boxes_path.exists() or not points_path.exists():
    raise RuntimeError(
        "Missing OSM-registered OCR GeoJSON. First fit an accepted transform with "
        "scripts/tools/fit_pixel_to_map_transform.py, then run "
        "scripts/tools/project_ocr_to_osm_geojson.py."
    )

remove_existing(project)
group = project.layerTreeRoot().insertGroup(0, GROUP_NAME)

if georef_image_path.exists():
    raster = QgsRasterLayer(str(georef_image_path), "\u5357\u5b8b\u4e34\u5b89\u56fe_\u539f\u56fe_OSM\u4eff\u5c04\u914d\u51c6")
    if raster.isValid():
        raster.setCrs(QgsCoordinateReferenceSystem("EPSG:3857"))
        raster.setCustomProperty(CUSTOM_PROPERTY, "true")
        project.addMapLayer(raster, False)
        group.addLayer(raster)

boxes = QgsVectorLayer(str(boxes_path), "\u5357\u5b8b\u4e34\u5b89\u56fe_RapidOCR\u6587\u5b57\u6846_OSM", "ogr")
if not boxes.isValid():
    raise RuntimeError(f"Cannot load OCR boxes: {boxes_path}")
boxes.setCrs(QgsCoordinateReferenceSystem("EPSG:3857"))
boxes.setCustomProperty(CUSTOM_PROPERTY, "true")
style_box_layer(boxes)
project.addMapLayer(boxes, False)
group.addLayer(boxes)

points = QgsVectorLayer(str(points_path), "\u5357\u5b8b\u4e34\u5b89\u56fe_RapidOCR\u4e2d\u5fc3\u70b9_OSM", "ogr")
if not points.isValid():
    raise RuntimeError(f"Cannot load OCR points: {points_path}")
points.setCrs(QgsCoordinateReferenceSystem("EPSG:3857"))
points.setCustomProperty(CUSTOM_PROPERTY, "true")
style_point_layer(points)
project.addMapLayer(points, False)
group.addLayer(points)

iface.setActiveLayer(boxes)
iface.zoomToActiveLayer()
print(f"loaded {boxes.featureCount()} OSM-registered OCR boxes and {points.featureCount()} center points")
