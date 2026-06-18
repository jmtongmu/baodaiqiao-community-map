# 数据模型草案

这个草案用于把“老地图空间理解”“QGIS 制图”“3D 建模”和“志书时间轴”连接起来。

## places

历史地点和空间对象主表。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `place_id` | text | 稳定编号 |
| `name` | text | 历史名称 |
| `category` | text | 城门、宫城、衙署、坊巷等 |
| `x` | number | EPSG:3857 X |
| `y` | number | EPSG:3857 Y |
| `confidence` | text | high/medium/low |
| `geometry_level` | text | symbolic/estimated_area/footprint |
| `version` | text | 数据版本 |
| `reference_logic` | text | 当前定位逻辑说明 |

## geometries

同一地点可以有多个几何版本。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `geometry_id` | text | 几何编号 |
| `place_id` | text | 关联地点 |
| `geometry_type` | text | point/line/polygon |
| `crs` | text | 坐标系 |
| `source_version` | text | 来源版本 |
| `confidence` | text | 几何置信度 |
| `notes` | text | 说明 |

## control_points

配准和校对用的强锚点。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `control_id` | text | 控制点编号 |
| `name` | text | 名称 |
| `kind` | text | 城门、桥、山体、河道节点等 |
| `x` / `y` | number | EPSG:3857 坐标 |
| `modern_ref` | text | 现代参考 |
| `confidence` | text | 置信度 |
| `source_ref` | text | 来源 |

## evidence

记录每个空间判断的证据。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `evidence_id` | text | 证据编号 |
| `place_id` | text | 关联地点 |
| `source_type` | text | map/gazetteer/modern/osm/ai |
| `source_ref` | text | 文件、页码、章节或图名 |
| `quote` | text | 原文或图上文字 |
| `interpretation` | text | AI/人工解释 |
| `confidence` | text | 证据置信度 |

## spatial_relations

地点之间的相对空间关系。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `relation_id` | text | 关系编号 |
| `subject_place_id` | text | 主体地点 |
| `relation` | text | north_of/south_of/east_of/west_of/near/inside/along |
| `object_place_id` | text | 参照地点 |
| `distance_hint` | text | 距离或方位提示 |
| `source_ref` | text | 来源 |
| `confidence` | text | 置信度 |

## timeline_events

志书事件和历史叙事。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `event_id` | text | 事件编号 |
| `title` | text | 事件标题 |
| `start_year` | number | 起始年份 |
| `end_year` | number | 结束年份 |
| `dynasty` | text | 朝代 |
| `place_id` | text | 关联地点 |
| `people` | text | 相关人物 |
| `source_text` | text | 志书原文摘录 |
| `source_ref` | text | 来源页码或章节 |
| `confidence` | text | 置信度 |
