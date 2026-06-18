# -*- coding: utf-8 -*-
"""Load the Nan Song Lin'an georeference control-point workbench.

This loads:
  1. source image and OCR boxes in image-pixel space,
  2. editable image control points,
  3. editable OSM/EPSG:3857 reference control points.

Edit/save the GeoJSON control layers in QGIS, then run:
  scripts/powershell/sync_nansong_linan_control_points_from_qgis.ps1
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


GROUP_NAME = "\u5357\u5b8b\u4e34\u5b89\u56fe_\u914d\u51c6\u63a7\u5236\u70b9\u5de5\u4f5c\u53f0"
IMAGE_RELATIVE = Path("assets/maps/nansong_linan_map.jpg")
OCR_RELATIVE = Path("data/ocr/image_space/nansong_linan_map_rapidocr_ocr_image_space.geojson")
IMAGE_CP_RELATIVE = Path("data/maps/control_points/nansong_linan_map_image_control_points.geojson")
OSM_CP_RELATIVE = Path("data/maps/control_points/nansong_linan_map_osm_control_points.geojson")
CUSTOM_PROPERTY = "linan_nansong_linan_georef_workbench"


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
        QgsRendererCategory("ocr_\u8857\u5df7\u9053\u8def", make_fill("255,210,60,50", "220,95,0,200"), "\u8857\u5df7\u9053\u8def"),
        QgsRendererCategory("ocr_\u57ce\u9632\u5b98\u7f72", make_fill("205,120,255,50", "125,35,190,200"), "\u57ce\u9632\u5b98\u7f72"),
        QgsRendererCategory("ocr_\u5bfa\u89c2", make_fill("110,220,130,50", "20,135,50,200"), "\u5bfa\u89c2"),
        QgsRendererCategory("ocr_\u5c71\u4f53", make_fill("160,130,90,50", "100,70,35,200"), "\u5c71\u4f53"),
        QgsRendererCategory("ocr_\u6c34\u7cfb", make_fill("80,180,255,50", "0,105,210,200"), "\u6c34\u7cfb"),
        QgsRendererCategory("ocr_\u6587\u5b57", make_fill("255,255,255,35", "70,70,70,180"), "\u5176\u4ed6\u6587\u5b57"),
    ]
    layer.setRenderer(QgsCategorizedSymbolRenderer("category", categories))


def style_control_points(layer, color):
    symbol = QgsMarkerSymbol.createSimple(
        {
            "name": "circle",
            "color": color,
            "outline_color": "255,255,255,235",
            "outline_width": "0.7",
            "size": "3.2",
        }
    )
    layer.renderer().setSymbol(symbol)

    label_settings = QgsPalLayerSettings()
    label_settings.fieldName = "matched_standard_name"
    label_settings.enabled = True
    text_format = QgsTextFormat()
    text_format.setFont(QFont("Microsoft YaHei"))
    text_format.setSize(9)
    text_format.setColor(QColor(20, 20, 20))
    buffer = QgsTextBufferSettings()
    buffer.setEnabled(True)
    buffer.setSize(1.0)
    buffer.setColor(QColor(255, 255, 255, 240))
    text_format.setBuffer(buffer)
    label_settings.setFormat(text_format)
    layer.setLabelsEnabled(True)
    layer.setLabeling(QgsVectorLayerSimpleLabeling(label_settings))


def remove_existing(project):
    for layer in list(project.mapLayers().values()):
        if layer.customProperty(CUSTOM_PROPERTY) == "true":
            project.removeMapLayer(layer.id())
    group = project.layerTreeRoot().findGroup(GROUP_NAME)
    if group is not None:
        project.layerTreeRoot().removeChildNode(group)


def add_layer(project, group, layer):
    layer.setCustomProperty(CUSTOM_PROPERTY, "true")
    project.addMapLayer(layer, False)
    group.addLayer(layer)


project = QgsProject.instance()
root = repo_root()
remove_existing(project)
group = project.layerTreeRoot().insertGroup(0, GROUP_NAME)

image_path = root / IMAGE_RELATIVE
ocr_path = root / OCR_RELATIVE
image_cp_path = root / IMAGE_CP_RELATIVE
osm_cp_path = root / OSM_CP_RELATIVE

if not image_cp_path.exists() or not osm_cp_path.exists():
    raise RuntimeError(
        "Missing editable control-point GeoJSON. Run "
        "scripts/powershell/prepare_nansong_linan_georef_workbench.ps1 first."
    )

raster = QgsRasterLayer(str(image_path), "\u539f\u56fe_\u50cf\u7d20\u5750\u6807")
if not raster.isValid():
    raise RuntimeError(f"Cannot load source image: {image_path}")
raster.setCrs(QgsCoordinateReferenceSystem("EPSG:3857"))
add_layer(project, group, raster)

ocr = QgsVectorLayer(str(ocr_path), "\u539f\u56fe_RapidOCR\u6587\u5b57\u6846", "ogr")
if not ocr.isValid():
    raise RuntimeError(f"Cannot load OCR image-space GeoJSON: {ocr_path}")
ocr.setCrs(QgsCoordinateReferenceSystem("EPSG:3857"))
style_ocr_layer(ocr)
add_layer(project, group, ocr)

image_controls = QgsVectorLayer(str(image_cp_path), "\u8001\u56fe\u63a7\u5236\u70b9_\u53ef\u7f16\u8f91_\u50cf\u7d20\u5750\u6807", "ogr")
if not image_controls.isValid():
    raise RuntimeError(f"Cannot load image control points: {image_cp_path}")
image_controls.setCrs(QgsCoordinateReferenceSystem("EPSG:3857"))
style_control_points(image_controls, "255,60,40,210")
add_layer(project, group, image_controls)

osm_controls = QgsVectorLayer(str(osm_cp_path), "OSM\u53c2\u7167\u63a7\u5236\u70b9_\u53ef\u7f16\u8f91_EPSG3857", "ogr")
if not osm_controls.isValid():
    raise RuntimeError(f"Cannot load OSM control points: {osm_cp_path}")
osm_controls.setCrs(QgsCoordinateReferenceSystem("EPSG:3857"))
style_control_points(osm_controls, "40,110,255,210")
add_layer(project, group, osm_controls)

iface.setActiveLayer(image_controls)
iface.zoomToActiveLayer()
print(
    "loaded georef workbench: "
    f"{image_controls.featureCount()} image controls, "
    f"{osm_controls.featureCount()} OSM controls. "
    "Edit/save GeoJSON layers, sync back to CSV, then run georef_nansong_linan_map.ps1."
)
