# 宝带桥社区志 AIGC 互动地图

## 一键运行

解压压缩包后，双击：

```text
一键启动_宝带桥AIGC地图.bat
```

启动后会自动打开：

```text
http://127.0.0.1:8787/
```

请不要关闭启动窗口；关闭后网页服务也会停止。

## 手动启动

如果需要手动启动本地网页服务：

```powershell
python -m http.server 8787 --bind 127.0.0.1
```

然后打开：

```text
http://127.0.0.1:8787/
```

主要功能：

- 高频地名柱形：按《宝带桥社区志》提及次数生成 3D 柱形。
- 地名排行联动：点击排行后，地图飞行定位并显示“为什么高频”。
- 里程碑时间线：13 个带地点的社区发展事件，可按 20 秒节奏播放。
- 底图切换：高德卫星、高德纯图、OSM 备用。
- 图层筛选：按频次、时间类型和图层开关控制显示。

## 文件说明

- `index.html`：网页入口。
- `app.js`：地图交互逻辑。
- `styles.css`：界面样式。
- `data/`：地名、柱形、里程碑、时间分类数据。
- `vendor/`：本地 MapLibre 前端库。
- `一键启动_宝带桥AIGC地图.bat`：Windows 一键启动脚本。

注意：MapLibre 已打包到本地；高德/OSM 底图瓦片仍需要联网读取。

数据来自 `data/` 目录下的 GeoJSON 和 JSON 文件。如重新提取志书地名，先在原项目目录运行：

```powershell
python "F:\AIGC\baodaiqiao-community-map\scripts\tools\build_baodaiqiao_web_map_data.py"
```
