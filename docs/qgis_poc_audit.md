# QGIS POC 审计

审计日期：2026-06-03

## 工程和资产

当前归档的 QGIS 工程为 `qgis/nansong_linan6.2.qgz`，工程 CRS 为 EPSG:3857。

工程外部依赖已经归档到同一目录：

| 文件 | 用途 |
| --- | --- |
| `qgis/linan_data.gpkg` | 城墙、皇城、御街等矢量基线 |
| `qgis/linan_nansong_modified.tif` | 南宋临安栅格参考底图 |

原始参考图像：

| 文件 | 用途 |
| --- | --- |
| `assets/maps/京城图.png` | 老地图空间关系与地名识别输入 |
| `assets/maps/临安.png` | 复原效果/视觉参考输入 |

## QGIS 图层概况

工程内解析到 12 个图层：

| 图层 | 类型 | CRS | 来源 |
| --- | --- | --- | --- |
| `OSM Standard` | raster | EPSG:3857 | OSM XYZ |
| `临安都城_HelloWorld` | Point | EPSG:4326 | memory |
| `临安_商贾市集` | Point | EPSG:3857 | memory |
| `临安_十三城门` | Point | EPSG:4326 | memory |
| `临安_提取地名_面状` | Polygon | EPSG:3857 | memory |
| `临安_提取地名_面状_V2` | Polygon | EPSG:3857 | memory |
| `临安_历史地名` | Point | EPSG:3857 | memory |
| `city_wall` | Line | EPSG:3857 | `linan_data.gpkg` |
| `imperial_palace` | Polygon | EPSG:3857 | `linan_data.gpkg` |
| `imperial_street` | Line | EPSG:4326 | `linan_data.gpkg` |
| `linan_nansong_modified` | raster | EPSG:3857 | `linan_nansong_modified.tif` |
| `linan_nansong_modified` | raster | EPSG:3857 | `linan_nansong_modified.tif` |

`linan_data.gpkg` 内有 3 个基线图层：

| 图层 | 要素数 | CRS |
| --- | ---: | --- |
| `city_wall` | 1 | EPSG:3857 |
| `imperial_palace` | 1 | EPSG:3857 |
| `imperial_street` | 1 | EPSG:4326 |

## 抽取地点数据

从 PyQGIS POC 脚本中抽取出 73 个地点/空间对象，已生成：

- `data/places/linan_places_v4_osm_yfix.csv`
- `data/places/linan_places_v4_osm_yfix.geojson`

类别分布：

| 类别 | 数量 |
| --- | ---: |
| 城门 | 13 |
| 寺观 | 12 |
| 坊巷 | 10 |
| 衙署 | 10 |
| 宫城 | 6 |
| 桥梁 | 5 |
| 市场 | 4 |
| 水体 | 3 |
| 道路 | 3 |
| 山体 | 3 |
| 军事 | 2 |
| 仓储 | 1 |
| 园苑 | 1 |

## 判断

当前 POC 已经建立了很好的基础：13 个城门作为强锚点，御街、城墙、皇城作为骨架，其余地名通过相对空间关系和置信度落位。这种方式适合继续用 AI 扩展。

需要优先收敛的风险：

1. `memory` 图层较多，应逐步转成 GeoPackage/GeoJSON，避免工程复制或重开后数据管理困难。
2. 工程主 CRS 是 EPSG:3857，但 `临安_十三城门` 和 `imperial_street` 使用 EPSG:4326；后续距离、偏移、3D 转换前需要统一。
3. 当前面状对象多为符号面，不等于真实建筑轮廓。进入 3D 前应增加 `geometry_level` 字段，区分符号、推定范围和可建模轮廓。
4. 定位逻辑已经写得很好，但最好拆成 `source`、`anchor`、`relation`、`confidence_reason`，方便校对和追溯。

## 建议下一步

1. 把 `临安_十三城门`、`city_wall`、`imperial_palace`、`imperial_street` 固化为统一 CRS 的基线 GeoPackage。
2. 建立 `control_points` 表，把城门、御街、皇城角点、河道节点作为控制点。
3. 建立 `places` 表，把当前 73 个对象作为 `v4_osm_yfix` 版本。
4. 建立 `evidence` 表，记录每个点位来自哪张图、哪段志书、哪条空间推理。
5. 在 QGIS 中做一轮人工校验后，再扩展志书事件时间轴。
