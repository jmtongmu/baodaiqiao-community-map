# 1937 地图配准到 OSM 标准坐标流程

目标：把 `assets/maps/1937.jpg` 上的 OCR 文字框从原图像素坐标转换到 OSM / EPSG:3857 坐标。

## 关键原则

1. 控制点的 `pixel_x/pixel_y` 必须来自 `1937.jpg` 原图像素坐标。
2. 控制点的 `map_x/map_y` 必须来自 QGIS OSM 底图里的 EPSG:3857 坐标。
3. 至少启用 3 个控制点才能求仿射转换，建议 6-10 个，且覆盖西湖侧、北城、东城、南部/钱塘江侧。
4. 第一轮优先选稳定地物：城门、山体、医院/寺庙、大水系、桥、城墙角点。不要用 OCR 可疑街巷做强锚。
5. RMSE 或单点最大残差超阈值时，不要导入正式层。先删除高残差控制点或增加覆盖更均匀的控制点。

## 文件

控制点模板：

```text
data/maps/control_points/1937_to_osm_control_points.csv
```

拟合结果：

```text
data/maps/transforms/1937_pixel_to_osm.json
```

投影后的 OCR 图层：

```text
data/ocr/osm_space/1937_rapidocr_osm_boxes.geojson
data/ocr/osm_space/1937_rapidocr_osm_points.geojson
```

## 操作步骤

1. 打开 `data/maps/control_points/1937_to_osm_control_points.csv`。
2. 对每个确认可用的控制点：
   - 保留或填写 `pixel_x/pixel_y`
   - 从 QGIS OSM 底图获取对应位置的 EPSG:3857 坐标，填入 `map_x/map_y`
   - 把 `enabled` 改为 `true`
3. 运行拟合：

```powershell
C:\Python313\python.exe .\scripts\tools\fit_pixel_to_map_transform.py `
  --map-id 1937 `
  --control-points .\data\maps\control_points\1937_to_osm_control_points.csv `
  --output .\data\maps\transforms\1937_pixel_to_osm.json `
  --image .\assets\maps\1937.jpg
```

4. 如果输出显示 `accepted: True`，投影 OCR：

```powershell
C:\Python313\python.exe .\scripts\tools\project_ocr_to_osm_geojson.py `
  --candidates .\data\ocr\1937_rapidocr_text_candidates.json `
  --transform .\data\maps\transforms\1937_pixel_to_osm.json
```

5. 在 QGIS Python Console 加载 OSM 配准结果：

```python
from pathlib import Path
from qgis.core import QgsProject

script = Path(QgsProject.instance().homePath()) / ".." / "scripts" / "pyqgis" / "load_1937_osm_registered_ocr.py"
exec(script.read_text(encoding="utf-8"))
```

## 残差判断

默认阈值：

```text
RMSE <= 60 m
max point error <= 120 m
```

1937 图本身可能存在局部形变。若仿射转换整体合理但局部仍错位，下一步应切换到分区仿射或 Thin Plate Spline，而不是简单放宽阈值。
