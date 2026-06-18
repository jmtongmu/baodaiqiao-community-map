# -*- coding: utf-8 -*-
"""Sync standardized Lin'an places into a GeoPackage and the current QGIS project.

Usage in QGIS Python Console after opening `qgis/nansong_linan6.2.qgz`:

from pathlib import Path
from qgis.core import QgsProject

script = Path(QgsProject.instance().homePath()) / ".." / "scripts" / "pyqgis" / "sync_standard_places_to_gpkg.py"
exec(script.read_text(encoding="utf-8"))
"""

import csv
import math
from pathlib import Path

from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QColor, QFont
from qgis.core import (
    QgsFeature,
    QgsField,
    QgsFillSymbol,
    QgsGeometry,
    QgsLineSymbol,
    QgsMarkerSymbol,
    QgsPalLayerSettings,
    QgsPointXY,
    QgsProject,
    QgsSingleSymbolRenderer,
    QgsTextBufferSettings,
    QgsTextFormat,
    QgsVectorFileWriter,
    QgsVectorLayer,
    QgsVectorLayerSimpleLabeling,
)


STANDARD_PLACES_CANDIDATES = [
    Path("data/places/linan_places_master.csv"),
    Path("data/places/linan_places_standard_v1.csv"),
]
LAYER_RULES = Path("data/config/layer_rules.csv")
OUTPUT_GPKG = Path("qgis/linan_places.gpkg")
LAYER_GROUP_NAME = "临安_标准地点图层"
SAVE_PROJECT_AFTER_SYNC = True

FIELDS = [
    ("place_id", QVariant.String),
    ("name", QVariant.String),
    ("category", QVariant.String),
    ("target_layer", QVariant.String),
    ("display_layer", QVariant.String),
    ("qgis_geometry", QVariant.String),
    ("semantic_geometry", QVariant.String),
    ("geometry_level", QVariant.String),
    ("x", QVariant.Double),
    ("y", QVariant.Double),
    ("confidence", QVariant.String),
    ("version", QVariant.String),
    ("source_map", QVariant.String),
    ("source_stage", QVariant.String),
    ("reference_logic", QVariant.String),
    ("notes", QVariant.String),
]


def repo_root():
    home = QgsProject.instance().homePath()
    if home:
        return Path(home).resolve().parent
    return Path.cwd()


def read_csv(path):
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def standard_places_path(root):
    for relative_path in STANDARD_PLACES_CANDIDATES:
        path = root / relative_path
        if path.exists():
            return path
    raise FileNotFoundError("No standard place table found")


def parse_bool(value):
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def parse_color(value):
    parts = [int(part.strip()) for part in value.split(",")]
    while len(parts) < 4:
        parts.append(255)
    return QColor(*parts[:4])


def make_rect(x, y, width, height):
    hw, hh = width / 2.0, height / 2.0
    points = [
        QgsPointXY(x - hw, y - hh),
        QgsPointXY(x + hw, y - hh),
        QgsPointXY(x + hw, y + hh),
        QgsPointXY(x - hw, y + hh),
        QgsPointXY(x - hw, y - hh),
    ]
    return QgsGeometry.fromPolygonXY([points])


def make_circle(x, y, radius, segments):
    points = []
    for index in range(segments + 1):
        angle = 2 * math.pi * index / segments
        points.append(QgsPointXY(x + radius * math.cos(angle), y + radius * math.sin(angle)))
    return QgsGeometry.fromPolygonXY([points])


def make_line(x, y, width):
    half_width = width / 2.0
    return QgsGeometry.fromPolylineXY([QgsPointXY(x - half_width, y), QgsPointXY(x + half_width, y)])


def geometry_for_place(place, rule):
    x, y = float(place["x"]), float(place["y"])
    geometry_type = rule["qgis_geometry"]
    shape = rule.get("shape", "rect")

    if geometry_type == "Point":
        return QgsGeometry.fromPointXY(QgsPointXY(x, y))
    if geometry_type in {"Line", "LineString"}:
        return make_line(x, y, float(rule.get("width_m") or 80))
    if shape == "circle":
        return make_circle(x, y, float(rule.get("radius_m") or 45), int(rule.get("segments") or 24))
    return make_rect(x, y, float(rule.get("width_m") or 60), float(rule.get("height_m") or 60))


def memory_layer_for_rule(rule):
    layer = QgsVectorLayer(f"{rule['qgis_geometry']}?crs=EPSG:3857", rule["display_name"], "memory")
    provider = layer.dataProvider()
    provider.addAttributes([QgsField(name, field_type) for name, field_type in FIELDS])
    layer.updateFields()
    return layer


def add_feature(layer, place, rule):
    feature = QgsFeature(layer.fields())
    feature.setGeometry(geometry_for_place(place, rule))
    feature.setAttributes(
        [
            place.get("place_id", ""),
            place.get("name", ""),
            place.get("category", ""),
            place.get("target_layer", ""),
            place.get("display_layer", ""),
            place.get("qgis_geometry", ""),
            place.get("semantic_geometry", ""),
            place.get("geometry_level", ""),
            float(place["x"]),
            float(place["y"]),
            place.get("confidence", ""),
            place.get("version", ""),
            place.get("source_map", ""),
            place.get("source_stage", ""),
            place.get("reference_logic", ""),
            place.get("notes", ""),
        ]
    )
    layer.dataProvider().addFeature(feature)


def style_layer(layer, rule):
    color = parse_color(rule["color_rgba"])
    geometry_type = rule["qgis_geometry"]
    if geometry_type == "Point":
        symbol = QgsMarkerSymbol.createSimple({"color": color.name(), "size": "4"})
        symbol.setColor(color)
    elif geometry_type in {"Line", "LineString"}:
        symbol = QgsLineSymbol.createSimple({"color": color.name(), "width": "0.8"})
        symbol.setColor(color)
    else:
        symbol = QgsFillSymbol.createSimple({"outline_color": "50,50,50,180", "outline_width": "0.25"})
        symbol.setColor(color)
    layer.setRenderer(QgsSingleSymbolRenderer(symbol))

    label_settings = QgsPalLayerSettings()
    label_settings.fieldName = "name"
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


def write_layer(layer, gpkg_path, layer_name, first_write):
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "GPKG"
    options.layerName = layer_name
    options.fileEncoding = "UTF-8"
    if first_write and not gpkg_path.exists():
        options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile
    else:
        options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer

    result = QgsVectorFileWriter.writeAsVectorFormatV3(
        layer,
        str(gpkg_path),
        QgsProject.instance().transformContext(),
        options,
    )
    error_code = result[0] if isinstance(result, tuple) else result
    if error_code != QgsVectorFileWriter.NoError:
        raise RuntimeError(f"Failed to write {layer_name} to {gpkg_path}: {result}")


def remove_existing_managed_layers(project, display_names):
    for layer in list(project.mapLayers().values()):
        if layer.name() in display_names and layer.customProperty("linan_places_managed") == "true":
            project.removeMapLayer(layer.id())


def ensure_group(project):
    root = project.layerTreeRoot()
    group = root.findGroup(LAYER_GROUP_NAME)
    if group is None:
        group = root.insertGroup(0, LAYER_GROUP_NAME)
    return group


def load_written_layer(project, group, gpkg_path, rule):
    source = f"{gpkg_path.as_posix()}|layername={rule['target_layer']}"
    layer = QgsVectorLayer(source, rule["display_name"], "ogr")
    if not layer.isValid():
        raise RuntimeError(f"Could not load written layer: {source}")
    style_layer(layer, rule)
    layer.setCustomProperty("linan_places_managed", "true")
    project.addMapLayer(layer, False)
    group.addLayer(layer)
    tree_layer = group.findLayer(layer.id())
    if tree_layer is not None:
        tree_layer.setItemVisibilityChecked(parse_bool(rule.get("default_visible", "true")))
    return layer


def main():
    root = repo_root()
    places_path = standard_places_path(root)
    rules_path = root / LAYER_RULES
    gpkg_path = root / OUTPUT_GPKG
    gpkg_path.parent.mkdir(parents=True, exist_ok=True)

    rules = read_csv(rules_path)
    rules_by_layer = {rule["target_layer"]: rule for rule in rules}
    places = read_csv(places_path)

    layers = {}
    for rule in rules:
        layer = memory_layer_for_rule(rule)
        style_layer(layer, rule)
        layers[rule["target_layer"]] = layer

    for place in places:
        rule = rules_by_layer.get(place["target_layer"])
        if rule is None:
            raise ValueError(f"No layer rule for target_layer={place['target_layer']!r}")
        add_feature(layers[place["target_layer"]], place, rule)

    first_write = True
    for rule in rules:
        layer = layers[rule["target_layer"]]
        layer.updateExtents()
        write_layer(layer, gpkg_path, rule["target_layer"], first_write)
        first_write = False

    project = QgsProject.instance()
    remove_existing_managed_layers(project, {rule["display_name"] for rule in rules})
    group = ensure_group(project)

    loaded_count = 0
    for rule in rules:
        if layers[rule["target_layer"]].featureCount() == 0:
            continue
        load_written_layer(project, group, gpkg_path, rule)
        loaded_count += 1

    if SAVE_PROJECT_AFTER_SYNC:
        project.write()

    print(f"读取地点表：{places_path}")
    print(f"已同步 {len(places)} 个地点到 {gpkg_path}")
    print(f"已加载 {loaded_count} 个分类图层到当前 QGIS 工程")


main()
