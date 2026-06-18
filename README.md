# 南宋临安历史城市复原

这个项目用于把老地图、地方志和现代地图坐标系连接起来，逐步复原南宋临安的 2D/3D 历史城市空间。

## 当前新增成果：宝带桥社区志互动地图

当前仓库已包含基于《宝带桥社区志》的互动网页地图成果：

- 稳定版网页地图：`web/baodaiqiao_aigc_map`
- 网页游戏 3D 引擎实验分支：`web/baodaiqiao_game3d_map_lab`
- 宝带桥地名、时间线、里程碑和高频地名柱形数据：`data/baodaiqiao`
- QGIS 自动加载与 3D 实践脚本：`scripts/pyqgis/load_baodaiqiao_*.py`
- 数据生成脚本：`scripts/tools/build_baodaiqiao_*.py`

稳定版网页地图运行方式：

```powershell
cd web/baodaiqiao_aigc_map
python -m http.server 8282 --bind 127.0.0.1
```

然后打开：

```text
http://127.0.0.1:8282/
```

也可以直接双击 `web/baodaiqiao_aigc_map/一键启动_宝带桥AIGC地图.bat`。

当前 POC 的核心流程是：

```text
老地图/历史图像
  -> AI 理解空间关系和地名关系
  -> PyQGIS 生成复原图层
  -> QGIS 校对、制图和 Web 地图输出
  -> 3D 城市复原
  -> 志书事件时间轴
```

## 当前基线

- QGIS 工程：`qgis/nansong_linan6.2.qgz`
- QGIS 外部依赖：`qgis/linan_data.gpkg`、`qgis/linan_nansong_modified.tif`
- 原始/参考地图：`assets/maps/京城图.png`、`assets/maps/临安.png`
- 原始 PyQGIS POC 脚本：`scripts/pyqgis/create_linan_places_polygons_embedded_v4_osm_yfix.py`
- CSV 驱动的 PyQGIS 入口：`scripts/pyqgis/create_linan_places_from_csv.py`
- GeoPackage 多图层同步脚本：`scripts/pyqgis/sync_standard_places_to_gpkg.py`
- 已抽取地点数据：`data/places/linan_places_v4_osm_yfix.csv`
- 已抽取面状数据：`data/places/linan_places_v4_osm_yfix.geojson`
- 标准地点表：`data/places/linan_places_standard_v1.csv`
- 图层规则表：`data/config/layer_rules.csv`

当前脚本内嵌了 73 个空间对象，包括城门、宫城、衙署、坊巷、寺观、桥梁、水体、山体等类别。抽取后的 CSV/GeoJSON 保留了坐标、置信度和定位逻辑，后续应优先修改结构化数据，再由脚本或 QGIS 重新生成图层。

## 目录

```text
assets/maps/      老地图、参考图、AI 生成或修复的视觉材料
data/places/      地名、地点、面状表达和后续空间数据
docs/             项目路线、POC 审计、数据模型
qgis/             QGIS 工程和工程依赖数据
scripts/pyqgis/   QGIS 控制台/插件可运行脚本
scripts/tools/    项目辅助脚本
```

## 重新抽取地点数据

```bash
python scripts/tools/extract_embedded_places.py
```

默认会从当前 PyQGIS POC 脚本中读取 `CATEGORY_SIZES` 和 `places`，生成：

- `data/places/linan_places_v4_osm_yfix.csv`
- `data/places/linan_places_v4_osm_yfix.geojson`

GeoJSON 使用 EPSG:3857，几何形状沿用当前 POC 的矩形/圆形符号化规则。

## 从 CSV 重新生成 QGIS 图层

打开 `qgis/nansong_linan6.2.qgz` 后，在 QGIS Python Console 运行：

```python
from pathlib import Path
from qgis.core import QgsProject

script = Path(QgsProject.instance().homePath()) / ".." / "scripts" / "pyqgis" / "create_linan_places_from_csv.py"
exec(script.read_text(encoding="utf-8"))
```

该脚本会读取 `../data/places/linan_places_v4_osm_yfix.csv`，生成带分类样式和中文标注的 memory layer。

## 同步为 GeoPackage 多图层

推荐后续使用这个方式。先生成标准地点表：

```bash
python scripts/tools/standardize_places.py
```

然后打开 `qgis/nansong_linan6.2.qgz`，在 QGIS Python Console 运行：

```python
from pathlib import Path
from qgis.core import QgsProject

script = Path(QgsProject.instance().homePath()) / ".." / "scripts" / "pyqgis" / "sync_standard_places_to_gpkg.py"
exec(script.read_text(encoding="utf-8"))
```

该脚本会：

1. 优先读取 `data/places/linan_places_master.csv`，不存在时读取 `data/places/linan_places_standard_v1.csv`。
2. 按 `data/config/layer_rules.csv` 自动分到城门、宫城、衙署、坊巷等图层。
3. 写入 `qgis/linan_places.gpkg`。
4. 加载到当前 QGIS 工程，设置中文标注和分类样式。
5. 保存当前 QGIS 工程。

## 建议工作方式

1. 用 AI 从老地图和志书中提出空间判断，写成结构化字段。
2. 把高置信度对象作为锚点，中低置信度对象作为待校对对象。
3. 在 QGIS 中叠加 OSM、老地图栅格、城墙/皇城/御街等基准图层校对。
4. 将校对后的数据固化到 GeoPackage/GeoJSON，而不是只保存在 memory layer。
5. 进入 3D 前，先区分“符号面”“历史推定范围”“真实建筑轮廓”三种几何等级。

## 导入新旧地图 OCR 候选

登记新地图并生成候选/转换模板：

```bash
python scripts/tools/register_old_map.py --map-id jingchengtu_new --title 新京城图 --source assets/maps/京城图.png
```

把 AI/OCR 结果填入：

```text
data/ocr/jingchengtu_new_text_candidates.json
```

把同一张 OCR 图的控制点填入：

```text
data/maps/transforms/jingchengtu_new_pixel_to_map.json
```

转换并更新 master：

```bash
python scripts/tools/ocr_candidates_to_standard_places.py --candidates data/ocr/jingchengtu_new_text_candidates.json --update-master
```

然后在 QGIS Python Console 重新运行：

```python
from pathlib import Path
from qgis.core import QgsProject

script = Path(QgsProject.instance().homePath()) / ".." / "scripts" / "pyqgis" / "sync_standard_places_to_gpkg.py"
exec(script.read_text(encoding="utf-8"))
```

坐标转换默认带 QA 阈值保护：RMSE 60 米、单点最大误差 120 米。详细要求见：

```text
docs/coordinate_accuracy.md
```

真实大图全量标注时，先走自动抽样闸门：

```bash
python scripts/tools/select_ocr_review_sample.py --candidates data/ocr/<map_id>_text_candidates.json --sample-size 12
```

样本通过 QGIS 检查后再导入全量。详见：

```text
docs/full_map_import_gate.md
```

## OCR 引擎与原图排布

Windows OCR 已验证不适合 `assets/maps/京城图.png`：繁体、竖排、密集小字识别质量较差。正式 OCR 建议改用 PaddleOCR PP-OCRv5 server 模型，详见：

```text
docs/ocr_engine_upgrade.md
```

OCR 结果必须先在原图坐标中检查，不应直接落到现代地图。原图排布流程：

```bash
python scripts/tools/create_image_world_file.py --image assets/maps/京城图.png
python scripts/tools/ocr_candidates_to_image_space_geojson.py --candidates data/ocr/<map_id>_text_candidates.json
```

然后在 QGIS Python Console 运行：

```python
from pathlib import Path
from qgis.core import QgsProject

script = Path(QgsProject.instance().homePath()) / ".." / "scripts" / "pyqgis" / "load_ocr_image_space.py"
exec(script.read_text(encoding="utf-8"))
```

历史记录：`assets/maps/京城图.png` 曾通过 Windows OCR 分块放大流程生成候选：

```text
data/ocr/jingchengtu_windows_ocr_text_candidates.json
data/places/imports/jingchengtu_windows_ocr_places_standard.csv
data/places/imports/jingchengtu_windows_ocr_transform_qa.json
```

该结果已判定质量不足，不作为正式 OCR 资产使用。
