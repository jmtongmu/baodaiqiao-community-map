# 宝带桥社区志 Game3D 实验地图

这是从 `web/baodaiqiao_aigc_map` 分支出来的实验目录，用于后续探索“网页游戏 3D 引擎作为地图基板”的可视化路线。

当前状态：

- 已复制稳定版互动地图的数据、界面和 MapLibre 依赖。
- 页面标题和标识已改为 `Game3D 实验分支`。
- 暂时仍沿用 MapLibre 作为可运行底座，便于和稳定版对照。

后续建议探索：

- Three.js / Babylon.js 作为 3D 场景主引擎。
- 高德瓦片或离线影像作为地表贴图。
- 将 `data/mention_columns.geojson` 转为 3D 柱体 mesh。
- 将 `data/milestones.geojson` 转为可播放的剧情节点。
- 保留原网页的排行、筛选、时间线 UI，逐步替换地图基板。

运行方式与稳定版一致：

```powershell
python -m http.server 8787 --bind 127.0.0.1
```

然后打开：

```text
http://127.0.0.1:8787/
```
