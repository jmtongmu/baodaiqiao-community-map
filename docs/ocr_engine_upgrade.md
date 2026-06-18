# OCR 引擎升级方案

Windows OCR 已被验证不适合 `京城图.png`：繁体、竖排、密集小字和版刻字的识别效果都较差。正式 OCR 应改用 PaddleOCR PP-OCRv5 或同等级中文场景文字 OCR。

## 推荐引擎

推荐优先使用 PaddleOCR 3.x 的 PP-OCRv5 server 模型。

理由：

- 官方文档说明 PP-OCRv5 server 是 PaddleOCR 3.0 默认的高精度 OCR 管线。
- PP-OCRv5 识别模型支持简体中文、繁体中文、英文、日文，也覆盖竖排、手写、拼音、罕见字等复杂场景。
- `PP-OCRv5_server_det` 比 mobile 检测模型精度更高，适合当前这种密集古地图文字。
- `PP-OCRv5_server_rec` 对繁体中文识别准确率高于 mobile 模型，更适合南宋古地图。

参考：

- PaddleOCR OCR pipeline docs: https://www.paddleocr.ai/v3.0.1/en/version3.x/pipeline_usage/OCR.html
- PaddleOCR PP-OCRv5 multilingual docs: https://github.com/PaddlePaddle/PaddleOCR/blob/main/docs/version3.x/algorithm/PP-OCRv5/PP-OCRv5_multi_languages.en.md

## 安装

当前这台机器的 pip 下载被网络代理阻断，不能直接安装。网络正常时建议：

```powershell
python -m pip install paddleocr paddlepaddle
```

如果 CPU 环境安装失败，可按 PaddleOCR 官方安装文档选择 CPU/GPU 版本。

## 推荐运行参数

命令行方向：

```powershell
paddleocr ocr `
  -i "\\10.100.66.31\tongmu_file\2025\AIwork\地方志\社区志\assets\maps\京城图.png" `
  --use_doc_orientation_classify False `
  --use_doc_unwarping False `
  --use_textline_orientation True `
  --save_path "\\10.100.66.31\tongmu_file\2025\AIwork\地方志\社区志\data\ocr\paddle_output" `
  --device cpu
```

如果模型参数可用，优先指定 server 模型：

```powershell
--text_detection_model_name PP-OCRv5_server_det
--text_recognition_model_name PP-OCRv5_server_rec
```

如果要单独测试繁体模型，可试：

```powershell
--lang chinese_cht
```

实际可用参数以安装版本的 `paddleocr ocr --help` 为准。

## 输出接入项目

如果 PaddleOCR 生成 JSON 结果，使用：

```powershell
python scripts/tools/normalize_paddleocr_json.py `
  --input data/ocr/paddle_output/<result>.json `
  --map-id jingchengtu_paddleocr `
  --image-file assets/maps/京城图.png `
  --output data/ocr/jingchengtu_paddleocr_text_candidates.json
```

然后生成原图排布 GeoJSON：

```powershell
python scripts/tools/ocr_candidates_to_image_space_geojson.py `
  --candidates data/ocr/jingchengtu_paddleocr_text_candidates.json `
  --output data/ocr/image_space/jingchengtu_paddleocr_ocr_image_space.geojson
```

最后在 QGIS 中先加载原图排布层检查 OCR 框和文字内容，再进入配准坐标转换。

## 工作原则

1. OCR 结果先在原图坐标中验证，不直接落到现代地图。
2. 文字方向由 OCR 引擎和 bbox 长宽共同记录：`horizontal`、`vertical`、`unknown`。
3. OCR 原文层只表示“图上文字资产”，不要直接混入城门、宫城、寺观等历史实体图层。
4. 只有经过人工/AI 语义解析后，OCR 原文才能转成历史地名候选。
