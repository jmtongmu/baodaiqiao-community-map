# 宝带桥社区 3D 沙盘实践流程

## 推荐路线

当前阶段采用 **QGIS 3D 沙盘预演**：先把社区志提取的时间地名、里程碑意义、点位坐标转成可拉伸的 2.5D 面图层，在 QGIS 里验证叙事和镜头。等 20 秒节奏稳定后，再导入 Blender 做正式视频。

## 已生成图层

- `data/baodaiqiao/baodaiqiao_3d_scene_stage.geojson`  
  社区叙事底座面。后续可替换为真实社区边界。
- `data/baodaiqiao/baodaiqiao_3d_scene_place_blocks.geojson`  
  已定位地名块体，包含 `height_m`、`scene_class`、`time_type`。
- `data/baodaiqiao/baodaiqiao_3d_scene_milestone_columns.geojson`  
  13 个里程碑意义光柱，包含 `significance`、`source_text`、`height_m`。
- `data/baodaiqiao/baodaiqiao_3d_scene_milestone_path.geojson`  
  20 秒叙事时间路径线。

## 重新生成数据

如果前面的地名、坐标、里程碑字段更新，先在 PowerShell 里运行：

```powershell
python scripts\tools\build_baodaiqiao_3d_scene_layers.py
```

## 加载到 QGIS

在 QGIS Python Console 运行：

```python
exec(open(r"F:\AIGC\baodaiqiao-community-map\scripts\pyqgis\load_baodaiqiao_3d_scene_practice.py", encoding="utf-8").read())
```

脚本会创建图层组：`宝带桥社区志_3D沙盘实践`。

## 打开 3D 视图

1. 菜单选择 `视图 > 新建3D地图视图`。
2. 相机俯仰调到约 45 度。
3. 先看三个主体：
   - 地名块体：社区空间底座。
   - 里程碑意义光柱：20 秒叙事节点。
   - 时间路径线：发展顺序。

如果自动 3D 拉伸未生效，在图层属性里手动设置：

- `3D_地名块体_面`：`图层属性 > 3D视图 > 启用3D渲染`，拉伸高度用字段 `height_m`。
- `3D_里程碑意义光柱_面`：同样启用 3D 渲染，拉伸高度用字段 `height_m`。
- `3D_社区叙事底座_面`：高度可设为 `0.2` 或保持贴地。

## 后续替换真实数据

当前图层是“可演示版”。后续建议逐步替换：

- 用真实社区边界替换 `stage`。
- 用真实水系面替换澹台湖、运河锚点。
- 用建筑轮廓面替换地名块体。
- 保留里程碑光柱和时间路径作为叙事层。
