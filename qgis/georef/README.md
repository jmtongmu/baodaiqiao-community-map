# 配准栅格

这里保存已经通过 QGIS Georeferencer 配准到工程坐标系的旧地图栅格。

推荐输出：

```text
qgis/georef/<map_id>_georef.tif
```

当前工程主 CRS 为 EPSG:3857。配准控制点建议优先使用城门、皇城、御街、西湖岸线、钱塘江方向和山体节点。

如果使用 `scripts/pyqgis/export_selected_raster_transform.py` 导出像素转换，它只适用于“配准后栅格本身”的像素坐标。若 OCR 是在原始旧图上运行，应使用原始旧图像素控制点另行求转换。
