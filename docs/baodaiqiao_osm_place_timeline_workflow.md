# 宝带桥社区志地名与地图底图对照流程

## 目标

把《宝带桥社区志》中出现的地名，与 QGIS 工程 `F:\社区志\宝带桥\baodaiqiao.qgz` 的高德矢量图底图进行视觉对照，形成可标注、可校对、可接时间轴的空间数据。

当前工程中“高德矢量图”是 XYZ 瓦片图层，不是可查询的矢量要素层。底图上的中文标签不能直接被 QGIS 选择或读取。因此本流程采用：

1. 高德矢量图：作为中文视觉底图和人工校对参照。
2. OSM/Overpass 命名要素：作为可机器匹配的外部矢量参考。
3. 社区志地名图层：作为最终可编辑、可标注、可接时间轴的数据层。

## 当前产物

| 文件 | 用途 |
| --- | --- |
| `data/baodaiqiao/baodaiqiao_osm_named_features.geojson` | 宝带桥周边 OSM 命名要素，用于机器匹配参考 |
| `data/baodaiqiao/baodaiqiao_place_osm_matches.geojson` | 社区志地名匹配/待校对点，可叠加在高德底图上 |
| `data/baodaiqiao/baodaiqiao_place_osm_matches.csv` | 人工校对表，记录匹配状态、OSM ID、坐标 |
| `data/baodaiqiao/baodaiqiao_gaode_place_checklist.csv` | 社区志地名与高德底图对应项目核对清单 |
| `data/baodaiqiao/baodaiqiao_timeline_spatial_events.csv` | 时间轴空间事件初稿 |
| `scripts/pyqgis/load_baodaiqiao_place_matches.py` | QGIS 加载脚本 |
| `scripts/tools/build_baodaiqiao_place_matches.py` | 重新生成匹配数据的脚本 |

## QGIS 加载方式

打开 `F:\社区志\宝带桥\baodaiqiao.qgz`，在 QGIS Python Console 运行：

```python
from pathlib import Path
script = Path(r"\\10.100.66.31\tongmu_file\2025\AIwork\地方志\社区志\scripts\pyqgis\load_baodaiqiao_place_matches.py")
exec(script.read_text(encoding="utf-8"))
```

加载后会出现两个图层：

1. `宝带桥社区志地名_匹配与待校对`
2. `宝带桥范围_OSM命名要素`
3. `社区志地名_高德底图核对清单`

建议先在属性表中过滤：

```text
match_status = 'matched'
```

这部分可以先作为可靠标注。绿色点为 `matched`，橙色点为 `review`。`review` 是近似匹配，必须对照高德底图和社区志原文人工核对后再改为 `matched`。

## 高德底图核对清单

`baodaiqiao_gaode_place_checklist.csv` 是第一步可视化工作的主清单。字段含义：

| 字段 | 含义 |
| --- | --- |
| `gazetteer_name` | 社区志中出现的地名 |
| `gaode_map_item` | 在高德矢量图上应查找或对应的标签 |
| `place_type` | 空间类型 |
| `match_status` | matched/review/manual |
| `visual_priority` | 可视化优先级 |
| `gaode_check_action` | 在 QGIS 中的核对动作 |
| `notes` | 叙事或时间轴用途 |

其中 `manual` 表示高德底图未必显示独立标签，尤其是旧自然村、旧河浜、旧桥名。这类地名应人工补点或补线，不要强行匹配相似名称。

## 匹配状态

| 状态 | 含义 | 处理方式 |
| --- | --- | --- |
| `matched` | 名称与类型基本一致 | 可先上图标注 |
| `review` | 名称接近，但可能误配 | 在 QGIS 中逐项检查 |
| `unmatched` | OSM 当前未找到对应命名要素 | 需要手动定位、补点或补面 |

## 推荐图层结构

在 QGIS 中建议拆成三类图层：

1. `社区志_可靠地名`：筛选 `matched`。
2. `社区志_待校对地名`：筛选 `review`。
3. `社区志_历史地名待定位`：从 CSV 中筛选 `unmatched` 后手工补点。

历史自然村、旧河浜、小桥等地名很多不会出现在 OSM Standard 上，例如朱塔浜、沉家浜、泥河田、王家浜、牛桩浜、新华内河等。这类地名应保留为“志书历史地名”，不要强行匹配到相似 OSM 标签。

## 时间轴接入

`baodaiqiao_timeline_spatial_events.csv` 中的 `gazetteer_place` 字段用于关联地名图层。

建议的联动逻辑：

1. 播放到某个事件年份。
2. 用 `gazetteer_place` 找到同名空间对象。
3. 若对象为 `matched`，镜头飞到 OSM 坐标。
4. 若对象为 `review`，先人工确认。
5. 若对象为 `unmatched`，使用社区范围中心或手动补点，不直接自动飞行。

## 重新生成

如果更新了 OSM 原始数据或调整了地名规则，运行：

```powershell
python scripts\tools\build_baodaiqiao_place_matches.py
```

当前 OSM 数据来自宝带桥、澹台湖、吴文化博物馆周边工作范围内的命名要素。由于高德矢量图和 OSM Standard 在 QGIS 中都是瓦片底图，不能直接读取标签，必须通过外部矢量数据和人工校对共同完成匹配。
