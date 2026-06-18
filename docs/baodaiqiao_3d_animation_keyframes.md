# 宝带桥社区 3D 动画关键帧实践

## 核心判断

QGIS 3D 动画适合用来制作 20 秒相机漫游预演。  
QGIS 的 3D 动画关键帧是“某个时间点的相机位置”，当前 Python API 对动画设置支持不稳定，所以采用脚本生成关键帧导引层，手动在 3D Map View 中添加 keyframe。

## 已生成文件

- `data/baodaiqiao/baodaiqiao_3d_animation_keyframes.csv`  
  K0-K6 的时间、目标点、推荐距离、俯仰、朝向、旁白。
- `data/baodaiqiao/baodaiqiao_3d_animation_keyframe_targets_3857.geojson`  
  K0-K6 镜头目标点。
- `data/baodaiqiao/baodaiqiao_3d_animation_camera_path_3857.geojson`  
  镜头目标路径线。

## 加载关键帧导引层

在 QGIS Python Console 运行：

```python
exec(open(r"\\10.100.66.31\tongmu_file\2025\AIwork\地方志\社区志\scripts\pyqgis\load_baodaiqiao_3d_animation_keyframe_guide.py", encoding="utf-8").read())
```

会新增图层组：`宝带桥社区志_3D动画关键帧导引`。

## 手动添加 Keyframe

1. 打开 3D Map View。
2. 点击 3D 窗口顶部的动画/播放按钮，展开动画面板。
3. 按关键帧导引层依次对准 K0-K6。
4. 每对准一个镜头，点击 `Add Keyframe`。
5. 时间填写：
   - K0：0s，全域开场
   - K1：3s，古桥起点
   - K2：6s，基层治理与农业
   - K3：9s，开发区建设
   - K4：13s，轨交接入
   - K5：16s，澹台湖文旅更新
   - K6：20s，文化展示收束

## 镜头建议

- K0：看全域底座和所有光柱。
- K1：推近宝带桥，突出 816、1831、1872、2014。
- K2：转向社区中心，突出 1949、1956、1962。
- K3：看道路、桥梁和居住/开发区块体。
- K4：看宝带桥南站。
- K5：看澹台湖和景区一期。
- K6：看吴文化博物馆和核心展示园。

## 导出动画

在 3D Map View 动画工具里选择导出帧：

- Duration：20 秒
- FPS：25
- 总帧数：500
- 推荐分辨率：1920 x 1080
- 输出目录：`data/baodaiqiao/animation_frames`
- 文件名模板：`bdq_####.png`

导出后可用 ffmpeg 合成：

```powershell
ffmpeg -framerate 25 -i data\baodaiqiao\animation_frames\bdq_%04d.png -c:v libx264 -pix_fmt yuv420p data\baodaiqiao\baodaiqiao_3d_20s.mp4
```

## 下一步

如果 QGIS 3D 的镜头满意，再把帧导出。  
如果要做更精致的视频，再把沙盘图层导出到 Blender 做材质、字幕和镜头控制。
