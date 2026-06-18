# -*- coding: utf-8 -*-
"""Export an affine pixel-to-map transform for the selected georeferenced raster.

Select a north-up georeferenced raster layer in QGIS, then run this in the
Python Console. The output JSON can be used by
`scripts/tools/ocr_candidates_to_standard_places.py`.
"""

import json
import re
from pathlib import Path

from qgis.core import QgsMapLayerType, QgsProject


MAP_ID = ""


def slug(value):
    text = re.sub(r"[^0-9A-Za-z_\-]+", "_", value.strip())
    return text.strip("_") or "map"


def repo_root():
    home = QgsProject.instance().homePath()
    if home:
        return Path(home).resolve().parent
    return Path.cwd()


layer = iface.activeLayer()
if layer is None or layer.type() != QgsMapLayerType.RasterLayer:
    raise RuntimeError("请先在 QGIS 图层面板中选中一张已配准栅格图层")

map_id = MAP_ID or slug(layer.name())
extent = layer.extent()
width = layer.width()
height = layer.height()

if width <= 0 or height <= 0:
    raise RuntimeError("无法读取栅格宽高")

payload = {
    "map_id": map_id,
    "crs": layer.crs().authid(),
    "method": "affine_pixel_to_map",
    "pixel_space": "georeferenced_raster_pixels",
    "assumption": "north_up_extent_based_transform",
    "raster_layer": layer.name(),
    "raster_source": layer.source(),
    "raster_width": width,
    "raster_height": height,
    "extent": {
        "xmin": extent.xMinimum(),
        "ymin": extent.yMinimum(),
        "xmax": extent.xMaximum(),
        "ymax": extent.yMaximum(),
    },
    "coefficients": {
        "x_origin": extent.xMinimum(),
        "pixel_width": extent.width() / width,
        "x_rotation": 0,
        "y_origin": extent.yMaximum(),
        "y_rotation": 0,
        "pixel_height": -extent.height() / height,
    },
    "accuracy": {
        "rmse_m": 0,
        "max_error_m": 0,
        "control_point_count": 0,
        "accepted": True,
        "note": "仅表示栅格像素网格到地图坐标的数学转换；不代表原始旧图配准误差为 0。OCR 必须在同一张配准后栅格上运行。"
    },
    "control_points": [],
    "notes": "如果配准结果含旋转/非线性变换，请改用控制点或更高阶转换。",
}

output = repo_root() / "data" / "maps" / "transforms" / f"{map_id}_pixel_to_map.json"
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"已导出像素到地图坐标转换：{output}")
