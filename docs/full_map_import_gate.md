# 真实大图全量标注导入闸门

目标：即使输入是一张真实大图、目标是全量标注，也不要直接把全部 AI/OCR 候选写入 QGIS。先自动抽样验证坐标和图层，再全量导入。

## 文件角色

| 文件 | 作用 |
| --- | --- |
| `data/ocr/<map_id>_text_candidates.json` | 全量 AI/OCR 候选 |
| `data/ocr/samples/<map_id>_review_sample_<n>.json` | 自动抽出的审核样本 |
| `data/maps/transforms/<map_id>_pixel_to_map.json` | 同一张图的像素到地图坐标转换 |
| `data/places/imports/<map_id>_places_standard.csv` | 转换后的标准地点表 |
| `data/places/imports/<map_id>_transform_qa.json` | 控制点残差 QA 报告 |
| `data/places/linan_places_master.csv` | QGIS 同步脚本读取的主地点表 |

## 闸门流程

```text
全量 OCR 候选
  -> 自动抽样 review sample
  -> 样本导入 master
  -> QGIS 同步
  -> 人眼检查样本点位置
  -> 通过后全量候选导入 master
  -> QGIS 同步全量标注
```

## 1. 从全量候选自动抽样

```powershell
$root="F:\AIGC\baodaiqiao-community-map"

python "$root\scripts\tools\select_ocr_review_sample.py" `
  --candidates "$root\data\ocr\<map_id>_text_candidates.json" `
  --sample-size 12
```

脚本会优先选择关键类别，例如城门、宫城、道路、水体、山体、桥梁、寺观等，并尽量覆盖图面不同区域。

如有必须检查的锚点，可指定：

```powershell
python "$root\scripts\tools\select_ocr_review_sample.py" `
  --candidates "$root\data\ocr\<map_id>_text_candidates.json" `
  --sample-size 12 `
  --force-names "余杭门,艮山门,钱湖门,涌金门,大内"
```

## 2. 导入样本到 master

```powershell
python "$root\scripts\tools\ocr_candidates_to_standard_places.py" `
  --candidates "$root\data\ocr\samples\<map_id>_review_sample_12.json" `
  --transform "$root\data\maps\transforms\<map_id>_pixel_to_map.json" `
  --version "<map_id>_review_sample" `
  --update-master `
  --master "$root\data\places\linan_places_master.csv"
```

默认转换阈值：

| 指标 | 阈值 |
| --- | ---: |
| RMSE | 60 米 |
| 单点最大误差 | 120 米 |

超出阈值会停止导入。

## 3. 在 QGIS 同步并检查

在 QGIS Python Console 运行：

```python
from pathlib import Path
from qgis.core import QgsProject

script = Path(QgsProject.instance().homePath()) / ".." / "scripts" / "pyqgis" / "sync_standard_places_to_gpkg.py"
exec(script.read_text(encoding="utf-8"))
```

检查：

1. 控制台是否显示读取 `linan_places_master.csv`。
2. 点位是否在合理位置。
3. 标注是否进入正确分类图层。
4. `data/places/imports/<map_id>_transform_qa.json` 的 RMSE 和最大误差是否合格。

## 4. 样本通过后全量导入

```powershell
python "$root\scripts\tools\ocr_candidates_to_standard_places.py" `
  --candidates "$root\data\ocr\<map_id>_text_candidates.json" `
  --transform "$root\data\maps\transforms\<map_id>_pixel_to_map.json" `
  --version "<map_id>_full_import" `
  --update-master `
  --master "$root\data\places\linan_places_master.csv"
```

然后回到 QGIS 再运行同步脚本。由于同一个 `map_id` 会替换之前的样本记录，master 不会无限累积同一张图的 sample 和 full。

## 5. 不通过时怎么处理

如果样本位置明显偏移：

1. 不要全量导入。
2. 检查 OCR 的 `bbox_pixel` 是否来自同一张图。
3. 检查控制点 `pixel` 是否来自同一张图。
4. 增加或更换控制点，尤其补足边角和变形区域。
5. 重跑样本导入。

大图有明显局部形变时，不要强行放宽阈值，应考虑分区导入或更高阶配准。
