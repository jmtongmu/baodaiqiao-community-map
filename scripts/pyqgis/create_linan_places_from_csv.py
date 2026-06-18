# -*- coding: utf-8 -*-
"""Create the Lin'an place polygon layer from extracted CSV data.

Open `qgis/nansong_linan6.2.qgz` in QGIS, then run this script in the QGIS
Python console. The script reads `../data/places/linan_places_v4_osm_yfix.csv`
relative to the QGIS project directory and creates a styled memory layer.
"""

import csv
import math
from pathlib import Path

from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QColor, QFont
from qgis.core import (
    QgsCategorizedSymbolRenderer,
    QgsFeature,
    QgsField,
    QgsFillSymbol,
    QgsGeometry,
    QgsPalLayerSettings,
    QgsPointXY,
    QgsProject,
    QgsRendererCategory,
    QgsTextBufferSettings,
    QgsTextFormat,
    QgsVectorLayer,
    QgsVectorLayerSimpleLabeling,
)


CATEGORY_SIZES = {
    "城门": ("rect", 70, 70),
    "宫城": ("rect", 180, 140),
    "衙署": ("rect", 80, 80),
    "坊巷": ("rect", 140, 35),
    "桥梁": ("rect", 60, 20),
    "寺观": ("circle", 45, 24),
    "仓储": ("rect", 90, 70),
    "市场": ("rect", 100, 60),
    "水体": ("rect", 160, 50),
    "山体": ("circle", 80, 28),
    "园苑": ("rect", 120, 90),
    "军事": ("rect", 100, 80),
    "道路": ("rect", 160, 25),
    "其他": ("rect", 60, 60),
}

CATEGORY_COLORS = {
    "城门": QColor(190, 60, 45, 145),
    "宫城": QColor(210, 150, 40, 145),
    "衙署": QColor(85, 120, 190, 145),
    "坊巷": QColor(160, 120, 80, 130),
    "桥梁": QColor(90, 160, 190, 145),
    "寺观": QColor(120, 170, 90, 145),
    "仓储": QColor(140, 110, 70, 145),
    "市场": QColor(210, 120, 80, 145),
    "水体": QColor(70, 150, 210, 125),
    "山体": QColor(90, 140, 75, 145),
    "园苑": QColor(110, 175, 110, 135),
    "军事": QColor(120, 120, 120, 150),
    "道路": QColor(200, 110, 50, 135),
    "其他": QColor(160, 160, 160, 130),
}


def csv_path():
    project_home = QgsProject.instance().homePath()
    if project_home:
        return Path(project_home) / ".." / "data" / "places" / "linan_places_v4_osm_yfix.csv"
    return Path("data/places/linan_places_v4_osm_yfix.csv")


def make_rect(x, y, width, height):
    hw, hh = width / 2.0, height / 2.0
    pts = [
        QgsPointXY(x - hw, y - hh),
        QgsPointXY(x + hw, y - hh),
        QgsPointXY(x + hw, y + hh),
        QgsPointXY(x - hw, y + hh),
        QgsPointXY(x - hw, y - hh),
    ]
    return QgsGeometry.fromPolygonXY([pts])


def make_circle(x, y, radius, segments=24):
    pts = []
    for i in range(segments + 1):
        angle = 2 * math.pi * i / segments
        pts.append(QgsPointXY(x + radius * math.cos(angle), y + radius * math.sin(angle)))
    return QgsGeometry.fromPolygonXY([pts])


def geometry_for_place(place):
    cat = place.get("Category", "其他")
    x, y = float(place["X"]), float(place["Y"])
    spec = CATEGORY_SIZES.get(cat, CATEGORY_SIZES["其他"])
    if spec[0] == "circle":
        return make_circle(x, y, spec[1], spec[2])
    return make_rect(x, y, spec[1], spec[2])


def read_places(path):
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def build_layer(places, layer_name):
    layer = QgsVectorLayer("Polygon?crs=EPSG:3857", layer_name, "memory")
    provider = layer.dataProvider()
    provider.addAttributes(
        [
            QgsField("Name", QVariant.String),
            QgsField("Category", QVariant.String),
            QgsField("X", QVariant.Double),
            QgsField("Y", QVariant.Double),
            QgsField("Confidence", QVariant.String),
            QgsField("Reference_Logic", QVariant.String),
        ]
    )
    layer.updateFields()

    features = []
    for place in places:
        feature = QgsFeature(layer.fields())
        feature.setGeometry(geometry_for_place(place))
        feature.setAttributes(
            [
                place["Name"],
                place["Category"],
                float(place["X"]),
                float(place["Y"]),
                place["Confidence"],
                place["Reference_Logic"],
            ]
        )
        features.append(feature)

    provider.addFeatures(features)
    layer.updateExtents()

    categories = []
    for cat, color in CATEGORY_COLORS.items():
        symbol = QgsFillSymbol.createSimple(
            {"outline_color": "50,50,50,180", "outline_width": "0.25"}
        )
        symbol.setColor(color)
        categories.append(QgsRendererCategory(cat, symbol, cat))
    layer.setRenderer(QgsCategorizedSymbolRenderer("Category", categories))

    label_settings = QgsPalLayerSettings()
    label_settings.fieldName = "Name"
    label_settings.enabled = True

    text_format = QgsTextFormat()
    text_format.setFont(QFont("Microsoft YaHei"))
    text_format.setSize(10)

    buffer = QgsTextBufferSettings()
    buffer.setEnabled(True)
    buffer.setSize(1.2)
    buffer.setColor(QColor(255, 255, 255, 220))
    text_format.setBuffer(buffer)

    label_settings.setFormat(text_format)
    layer.setLabelsEnabled(True)
    layer.setLabeling(QgsVectorLayerSimpleLabeling(label_settings))

    QgsProject.instance().addMapLayer(layer)
    print(f"已生成 {layer_name}，要素数：{len(features)}")
    return layer


places = read_places(csv_path())
build_layer(places, "临安_提取地名_面状_V4_OSM_yfix_from_csv")
