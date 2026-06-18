# 老地图坐标转换精度要求

老地图导入中最容易出错的是“像素坐标属于哪张图”。必须先确认 OCR/AI 输出的 `bbox_pixel` 来自哪一个像素空间，再选择对应的坐标转换方式。

## 原则

1. OCR 在原始旧图上运行，就必须使用原始旧图像素坐标对应的控制点。
2. OCR 在配准后 GeoTIFF 上运行，才可以使用配准后栅格的像素到地图坐标转换。
3. 不要把原始旧图的 OCR 框直接套到配准后重采样栅格上。
4. 不要只看图层能显示，必须看控制点残差。
5. 低置信度或高残差结果只能作为候选，不应直接进入正式图层。

## 推荐控制点

优先使用稳定、可复核的地物：

| 类型 | 说明 |
| --- | --- |
| 城门 | 十三城门是当前最强锚点 |
| 皇城/大内 | 轮廓和角点可做局部控制 |
| 御街 | 南北轴线适合约束城市骨架 |
| 西湖岸线 | 适合约束西侧，但旧图形变可能较大 |
| 钱塘江方向 | 适合约束南侧大方向 |
| 山体节点 | 凤凰山、宝石山等可作为外部参照 |

控制点应尽量覆盖整张地图，不要集中在一个角落。最少 3 个控制点可求仿射转换，建议 6 个以上，并检查残差。

## 残差阈值

当前导入脚本默认阈值：

| 指标 | 默认阈值 |
| --- | ---: |
| RMSE | 60 米 |
| 单点最大误差 | 120 米 |

如果超过阈值，`ocr_candidates_to_standard_places.py` 会停止导入。可以手动调整阈值，但不建议为了“跑通”而放宽。

## 转换文件格式

转换文件位于：

```text
data/maps/transforms/<map_id>_pixel_to_map.json
```

推荐使用控制点：

```json
{
  "map_id": "jingchengtu",
  "crs": "EPSG:3857",
  "method": "affine_pixel_to_map",
  "pixel_space": "ocr_image_pixels",
  "coefficients": {
    "x_origin": null,
    "pixel_width": null,
    "x_rotation": 0,
    "y_origin": null,
    "y_rotation": 0,
    "pixel_height": null
  },
  "control_points": [
    {
      "name": "余杭门",
      "pixel": [120, 340],
      "map": [13375474.9, 3538990.1]
    }
  ]
}
```

脚本会根据控制点求仿射转换，并输出 QA 报告：

```text
data/places/imports/<map_id>_transform_qa.json
```

## OCR 图像选择

推荐路线 A：OCR 原始旧图

```text
原始旧图
  -> OCR bbox_pixel
  -> 原始旧图控制点
  -> 仿射/后续更高阶转换
```

这条路线最容易保持像素空间一致。

路线 B：OCR 配准后栅格

```text
旧图配准为 GeoTIFF
  -> 对配准后 GeoTIFF 做 OCR
  -> 使用配准后栅格像素到地图坐标转换
```

这条路线适合快速接入 QGIS，但必须确认 OCR 的图片就是配准后的栅格，不是原始旧图。

## 后续增强

当前脚本实现的是仿射转换，适合小范围或形变较轻的地图。若旧图形变明显，后续应增加：

- 分区仿射
- Thin Plate Spline
- Polynomial 2/3 阶转换
- 控制点局部权重
- QGIS Georeferencer `.points` 文件解析
