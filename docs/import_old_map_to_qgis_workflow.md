# 旧南宋都城地图导入到 QGIS 的自动分层标注流程

目标：导入一张旧地图后，让地图上的文字标注能够进入正确位置、正确图层，并在 QGIS 工程中显示。

## 总流程

```text
旧地图图片
  -> 地图配准
  -> AI/OCR 识别文字框
  -> 像素坐标转 EPSG:3857 坐标
  -> 标准地点表
  -> 图层规则分发
  -> GeoPackage 多图层
  -> QGIS 工程显示标注
```

## 1. 放入旧地图

把图片放到：

```text
assets/maps/
```

同时在 `data/maps/maps.csv` 里登记一行。建议字段：

```text
map_id,title,file_path,map_type,crs,status,notes
```

`status` 可以用：

| 状态 | 含义 |
| --- | --- |
| `raw` | 原始图片，未配准 |
| `georeferenced` | 已配准 |
| `ready` | 已进入 QGIS 工程基线 |

## 2. 配准旧地图

在 QGIS 使用 Georeferencer：

1. 打开旧地图图片。
2. 选择控制点，例如十三城门、皇城角点、御街轴线、西湖岸线、钱塘江方向、凤凰山等。
3. 控制点目标坐标使用工程中的 EPSG:3857。
4. 输出到：

```text
qgis/georef/
```

例如：

```text
qgis/georef/jingchengtu_georef.tif
```

配准完成后，旧图的像素坐标才能稳定转换到地图坐标。

注意：如果 OCR/AI 是在原始旧图上识别的，`bbox_pixel` 属于原始旧图像素空间，不能直接使用配准后 GeoTIFF 的像素转换。详见 `docs/coordinate_accuracy.md`。

## 3. AI/OCR 输出文字候选

AI/OCR 不直接改 QGIS 工程，而是输出结构化候选数据。

建议 JSON 格式：

```json
[
  {
    "text": "余杭门",
    "category": "城门",
    "bbox_pixel": [120, 340, 180, 390],
    "orientation": "vertical",
    "confidence": "high",
    "source_map": "jingchengtu",
    "reference_logic": "位于北城墙西段，邻近艮山门西侧"
  }
]
```

建议保存到：

```text
data/ocr/
```

## 4. 转成标准地点表

当前 POC 已经有标准地点表：

```text
data/places/linan_places_standard_v1.csv
```

它包含这些关键字段：

| 字段 | 用途 |
| --- | --- |
| `place_id` | 稳定编号 |
| `name` | 地名 |
| `category` | 历史对象类别 |
| `target_layer` | QGIS 目标图层 |
| `qgis_geometry` | QGIS 实际几何类型 |
| `semantic_geometry` | 历史语义几何类型 |
| `geometry_level` | symbolic/estimated_area/footprint |
| `x` / `y` | EPSG:3857 坐标 |
| `confidence` | high/medium/low |
| `source_map` | 来源地图 |
| `reference_logic` | 定位逻辑 |

当前可以用这个脚本从旧 POC CSV 生成标准表：

```bash
python scripts/tools/standardize_places.py
```

后续若从 AI/OCR 结果生成坐标，也应该输出到同一个标准表结构。

从 AI/OCR 候选 JSON 转标准表：

```bash
python scripts/tools/ocr_candidates_to_standard_places.py --candidates data/ocr/<map_id>_text_candidates.json --update-master
```

如果是大图全量候选，先自动抽样：

```bash
python scripts/tools/select_ocr_review_sample.py --candidates data/ocr/<map_id>_text_candidates.json --sample-size 12
```

样本通过后再全量导入。完整闸门流程见 `docs/full_map_import_gate.md`。

脚本会自动寻找：

```text
data/maps/transforms/<map_id>_pixel_to_map.json
```

并生成：

```text
data/places/imports/<map_id>_places_standard.csv
data/places/imports/<map_id>_transform_qa.json
data/places/linan_places_master.csv
```

默认残差阈值为 RMSE 60 米、单点最大误差 120 米。超过阈值会停止导入。

## 5. 图层规则

图层分配由这个文件控制：

```text
data/config/layer_rules.csv
```

例如：

| 类别 | 目标图层 | 显示名 |
| --- | --- | --- |
| 城门 | `places_city_gate` | 临安_城门 |
| 宫城 | `places_palace` | 临安_宫城 |
| 衙署 | `places_office` | 临安_衙署 |
| 坊巷 | `places_block` | 临安_坊巷 |
| 寺观 | `places_temple` | 临安_寺观 |
| 道路 | `places_road` | 临安_道路 |

如果以后新增类别，只需要改规则表和标准地点表，不需要重写 QGIS 工程。

## 6. 写入 GeoPackage 并加载 QGIS 工程

打开：

```text
qgis/nansong_linan6.2.qgz
```

在 QGIS Python Console 运行：

```python
from pathlib import Path
from qgis.core import QgsProject

script = Path(QgsProject.instance().homePath()) / ".." / "scripts" / "pyqgis" / "sync_standard_places_to_gpkg.py"
exec(script.read_text(encoding="utf-8"))
```

脚本会生成：

```text
qgis/linan_places.gpkg
```

并把有数据的分类图层加载到工程的图层组：

```text
临安_标准地点图层
```

脚本还会设置：

- 中文图层名
- 中文地名标注
- 分类颜色
- 图层显隐
- `name` 字段标注
- `reference_logic` 等字段供点击查看

## 7. 打开工程后的效果

运行同步脚本并保存工程后，下次打开 QGIS 工程应能看到：

```text
临安_标准地点图层
  临安_城门
  临安_宫城
  临安_衙署
  临安_坊巷
  临安_桥梁
  临安_寺观
  临安_市场
  临安_水体
  临安_道路
  ...
```

每个图层都来自同一个 GeoPackage：

```text
qgis/linan_places.gpkg
```

## 8. 关键原则

1. AI/OCR 只产出候选和证据，不直接写死到 QGIS 工程。
2. 位置统一使用 EPSG:3857。
3. 分层逻辑统一放在 `layer_rules.csv`。
4. QGIS 工程只读取稳定数据源，例如 GeoPackage。
5. 进入 3D 前，必须区分 `symbolic`、`estimated_area`、`footprint`。
6. OCR 像素坐标必须和转换控制点来自同一张图。
7. 每次导入都必须查看 `*_transform_qa.json` 的 RMSE 和最大误差。
