# -*- coding: utf-8 -*-
"""Load 1937 OCR boxes after pixel-to-OSM registration."""

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


GROUP_NAME = "1937地图_OSM配准OCR"
BOXES_RELATIVE = Path("data/ocr/osm_space/1937_rapidocr_osm_boxes.geojson")
POINTS_RELATIVE = Path("data/ocr/osm_space/1937_rapidocr_osm_points.geojson")
GEOREF_IMAGE_RELATIVE = Path("qgis/georef/1937_osm_affine.jpg")


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
        QgsRendererCategory("ocr_街巷道路", make_fill("255,190,0,65", "220,90,0,230"), "街巷道路"),
        QgsRendererCategory("ocr_水系", make_fill("60,170,255,65", "0,95,220,230"), "水系"),
        QgsRendererCategory("ocr_城防官署", make_fill("210,120,255,65", "120,35,190,230"), "城防官署"),
        QgsRendererCategory("ocr_寺观", make_fill("80,220,120,65", "10,135,45,230"), "寺观"),
        QgsRendererCategory("ocr_山体", make_fill("160,120,75,65", "95,60,20,230"), "山体"),
        QgsRendererCategory("ocr_文字", make_fill("255,255,255,45", "65,65,65,220"), "其他文字"),
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
        if layer.customProperty("linan_1937_osm_registered") == "true":
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
        "缺少 OSM 配准 OCR GeoJSON。请先填写控制点并运行 fit_pixel_to_map_transform.py "
        "和 project_ocr_to_osm_geojson.py。"
    )

remove_existing(project)
group = project.layerTreeRoot().insertGroup(0, GROUP_NAME)

if georef_image_path.exists():
    raster = QgsRasterLayer(str(georef_image_path), "1937原图_OSM仿射配准")
    if raster.isValid():
        raster.setCrs(QgsCoordinateReferenceSystem("EPSG:3857"))
        raster.setCustomProperty("linan_1937_osm_registered", "true")
        project.addMapLayer(raster, False)
        group.addLayer(raster)

boxes = QgsVectorLayer(str(boxes_path), "1937_RapidOCR文字框_OSM", "ogr")
if not boxes.isValid():
    raise RuntimeError(f"无法加载 OCR 框：{boxes_path}")
boxes.setCrs(QgsCoordinateReferenceSystem("EPSG:3857"))
boxes.setCustomProperty("linan_1937_osm_registered", "true")
style_box_layer(boxes)
project.addMapLayer(boxes, False)
group.addLayer(boxes)

points = QgsVectorLayer(str(points_path), "1937_RapidOCR中心点_OSM", "ogr")
if not points.isValid():
    raise RuntimeError(f"无法加载 OCR 点：{points_path}")
points.setCrs(QgsCoordinateReferenceSystem("EPSG:3857"))
points.setCustomProperty("linan_1937_osm_registered", "true")
style_point_layer(points)
project.addMapLayer(points, False)
group.addLayer(points)

iface.setActiveLayer(boxes)
iface.zoomToActiveLayer()
print(f"已加载 {boxes.featureCount()} 个 OSM 配准 OCR 框和 {points.featureCount()} 个中心点")
