# OCR/AI 地图文字候选

这里保存从旧地图图片中识别出的文字候选。

推荐格式为 JSON：

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

这些候选后续应转换为 `data/places/linan_places_standard_v1.csv` 的标准字段。

如果候选使用 `bbox_pixel`，必须提供同一张图的像素到地图坐标转换文件：

```text
data/maps/transforms/<map_id>_pixel_to_map.json
```

转换后会生成 QA 报告。默认超过 RMSE 60 米或单点最大误差 120 米时，脚本会停止导入。
