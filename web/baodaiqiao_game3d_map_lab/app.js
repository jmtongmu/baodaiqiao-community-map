const DATA_URLS = {
  mentionPoints: "./data/mention_points.geojson",
  mentionColumns: "./data/mention_columns.geojson",
  milestones: "./data/milestones.geojson",
  temporalPoints: "./data/temporal_points.geojson",
  stats: "./data/stats.json",
};

const CENTER = [120.6488, 31.2586];
const INITIAL_VIEW = {
  center: CENTER,
  zoom: 13.55,
  pitch: 58,
  bearing: -24,
};

const state = {
  mapReady: false,
  activeTab: "ranking",
  activeLevel: "全部",
  activeTime: "全部",
  activePlaceName: "",
  activeMilestoneIndex: 0,
  currentBase: "satellite",
  isPlaying: false,
  playTimer: null,
  data: null,
  popup: null,
};

const $ = (selector) => document.querySelector(selector);

const els = {
  summaryGrid: $("#summaryGrid"),
  rankList: $("#rankList"),
  milestoneList: $("#milestoneList"),
  missingList: $("#missingList"),
  detailPanel: $("#detailPanel"),
  timelineTrack: $("#timelineTrack"),
  timelineTitle: $("#timelineTitle"),
  timelineSubtitle: $("#timelineSubtitle"),
  progressFill: $("#progressFill"),
  playTimeline: $("#playTimeline"),
  placeSearch: $("#placeSearch"),
  levelFilter: $("#levelFilter"),
  timeFilter: $("#timeFilter"),
  panelToggle: $("#panelToggle"),
  sidePanel: $(".side-panel"),
};

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function numberText(value) {
  return Number(value || 0).toLocaleString("zh-CN");
}

function getPlaceName(props) {
  return props.gazetteer_name || props.name || "";
}

function sortedMilestones() {
  return [...state.data.milestones.features].sort((a, b) => {
    return Number(a.properties.order || 0) - Number(b.properties.order || 0);
  });
}

function featureCollection(features = []) {
  return {
    type: "FeatureCollection",
    features,
  };
}

function createMap() {
  return new maplibregl.Map({
    container: "map",
    style: {
      version: 8,
      glyphs: "https://demotiles.maplibre.org/font/{fontstack}/{range}.pbf",
      sources: {
        "amap-satellite": {
          type: "raster",
          tiles: [
            "https://webst01.is.autonavi.com/appmaptile?style=6&x={x}&y={y}&z={z}",
            "https://webst02.is.autonavi.com/appmaptile?style=6&x={x}&y={y}&z={z}",
            "https://webst03.is.autonavi.com/appmaptile?style=6&x={x}&y={y}&z={z}",
          ],
          tileSize: 256,
          attribution: "高德地图",
        },
        "amap-satellite-labels": {
          type: "raster",
          tiles: [
            "https://webst01.is.autonavi.com/appmaptile?style=8&x={x}&y={y}&z={z}",
            "https://webst02.is.autonavi.com/appmaptile?style=8&x={x}&y={y}&z={z}",
          ],
          tileSize: 256,
        },
        "amap-vector": {
          type: "raster",
          tiles: [
            "https://webrd01.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}",
            "https://webrd02.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}",
            "https://webrd03.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}",
          ],
          tileSize: 256,
          attribution: "高德地图",
        },
        "osm-raster": {
          type: "raster",
          tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
          tileSize: 256,
          attribution: "OpenStreetMap",
        },
      },
      layers: [
        { id: "amap-satellite", type: "raster", source: "amap-satellite" },
        { id: "amap-satellite-labels", type: "raster", source: "amap-satellite-labels" },
        {
          id: "amap-vector",
          type: "raster",
          source: "amap-vector",
          layout: { visibility: "none" },
        },
        {
          id: "osm-raster",
          type: "raster",
          source: "osm-raster",
          layout: { visibility: "none" },
        },
      ],
    },
    ...INITIAL_VIEW,
    antialias: true,
    localIdeographFontFamily: "Microsoft YaHei, PingFang SC, Noto Sans CJK SC, sans-serif",
  });
}

async function loadJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`无法读取 ${url}`);
  }
  return response.json();
}

async function loadAllData() {
  const [mentionPoints, mentionColumns, milestones, temporalPoints, stats] = await Promise.all([
    loadJson(DATA_URLS.mentionPoints),
    loadJson(DATA_URLS.mentionColumns),
    loadJson(DATA_URLS.milestones),
    loadJson(DATA_URLS.temporalPoints),
    loadJson(DATA_URLS.stats),
  ]);
  return { mentionPoints, mentionColumns, milestones, temporalPoints, stats };
}

function addDataLayers(map) {
  map.addSource("mention-columns", {
    type: "geojson",
    data: state.data.mentionColumns,
    generateId: true,
  });
  map.addSource("mention-points", {
    type: "geojson",
    data: state.data.mentionPoints,
    generateId: true,
  });
  map.addSource("milestones", {
    type: "geojson",
    data: state.data.milestones,
    generateId: true,
  });
  map.addSource("temporal-points", {
    type: "geojson",
    data: state.data.temporalPoints,
    generateId: true,
  });
  map.addSource("active-column", {
    type: "geojson",
    data: featureCollection(),
  });
  map.addSource("active-milestone", {
    type: "geojson",
    data: featureCollection(),
  });
  map.addSource("milestone-route", {
    type: "geojson",
    data: makeMilestoneRoute(),
  });

  map.addLayer({
    id: "temporal-points",
    type: "circle",
    source: "temporal-points",
    layout: { visibility: "none" },
    paint: {
      "circle-radius": ["interpolate", ["linear"], ["zoom"], 12, 3, 15, 6],
      "circle-color": ["get", "color"],
      "circle-opacity": 0.72,
      "circle-stroke-width": 1,
      "circle-stroke-color": "rgba(255,255,255,0.72)",
    },
  });

  map.addLayer({
    id: "milestone-route",
    type: "line",
    source: "milestone-route",
    paint: {
      "line-color": "#f2bb4a",
      "line-width": ["interpolate", ["linear"], ["zoom"], 12, 1.2, 15, 3],
      "line-opacity": 0.58,
      "line-dasharray": [1.2, 1.6],
    },
  });

  map.addLayer({
    id: "mention-columns",
    type: "fill-extrusion",
    source: "mention-columns",
    paint: {
      "fill-extrusion-color": ["get", "color"],
      "fill-extrusion-height": ["to-number", ["get", "height_m"], 24],
      "fill-extrusion-base": 0,
      "fill-extrusion-opacity": 0.84,
      "fill-extrusion-vertical-gradient": true,
    },
  });

  map.addLayer({
    id: "active-column-glow",
    type: "fill-extrusion",
    source: "active-column",
    paint: {
      "fill-extrusion-color": "#ffffff",
      "fill-extrusion-height": ["*", ["to-number", ["get", "height_m"], 24], 1.12],
      "fill-extrusion-base": 0,
      "fill-extrusion-opacity": 0.22,
      "fill-extrusion-vertical-gradient": false,
    },
  });

  map.addLayer({
    id: "mention-column-outline",
    type: "line",
    source: "mention-columns",
    paint: {
      "line-color": "rgba(255,255,255,0.75)",
      "line-width": 0.8,
      "line-opacity": 0.55,
    },
  });

  map.addLayer({
    id: "mention-points",
    type: "circle",
    source: "mention-points",
    paint: {
      "circle-radius": ["interpolate", ["linear"], ["to-number", ["get", "count_num"], 0], 0, 4, 455, 13],
      "circle-color": ["get", "color"],
      "circle-opacity": 0.92,
      "circle-stroke-width": 1.5,
      "circle-stroke-color": "#ffffff",
    },
  });

  map.addLayer({
    id: "milestone-circles",
    type: "circle",
    source: "milestones",
    paint: {
      "circle-radius": ["interpolate", ["linear"], ["zoom"], 12, 7, 15, 12],
      "circle-color": ["get", "color"],
      "circle-opacity": 0.94,
      "circle-stroke-width": 2.5,
      "circle-stroke-color": "#fff4d1",
    },
  });

  map.addLayer({
    id: "active-milestone-ring",
    type: "circle",
    source: "active-milestone",
    paint: {
      "circle-radius": ["interpolate", ["linear"], ["zoom"], 12, 17, 15, 25],
      "circle-color": "rgba(255,255,255,0)",
      "circle-stroke-width": 3,
      "circle-stroke-color": "#ffffff",
      "circle-stroke-opacity": 0.86,
    },
  });

  map.addLayer({
    id: "mention-labels",
    type: "symbol",
    source: "mention-points",
    layout: {
      "text-field": ["get", "column_label"],
      "text-size": ["interpolate", ["linear"], ["to-number", ["get", "rank_num"], 100], 1, 14, 10, 12, 100, 10],
      "text-offset": [0, -1.35],
      "text-anchor": "bottom",
      "text-allow-overlap": false,
      "text-ignore-placement": false,
    },
    paint: {
      "text-color": "#ffffff",
      "text-halo-color": "rgba(5,8,10,0.92)",
      "text-halo-width": 1.4,
    },
  });

  map.addLayer({
    id: "milestone-labels",
    type: "symbol",
    source: "milestones",
    layout: {
      "text-field": ["get", "map_label"],
      "text-size": 12,
      "text-offset": [0, 1.25],
      "text-anchor": "top",
      "text-allow-overlap": false,
    },
    paint: {
      "text-color": "#fff7da",
      "text-halo-color": "rgba(5,8,10,0.92)",
      "text-halo-width": 1.5,
    },
  });

  attachMapInteractions(map);
  applyLevelFilter();
  applyTimeFilter();
}

function makeMilestoneRoute() {
  const coordinates = sortedMilestones().map((feature) => feature.geometry.coordinates);
  return {
    type: "Feature",
    geometry: { type: "LineString", coordinates },
    properties: { name: "社区发展里程碑路径" },
  };
}

function attachMapInteractions(map) {
  map.on("click", "mention-columns", (event) => {
    const feature = event.features?.[0];
    if (!feature) return;
    selectPlace(feature.properties.gazetteer_name, true, event.lngLat);
  });

  map.on("click", "mention-points", (event) => {
    const feature = event.features?.[0];
    if (!feature) return;
    selectPlace(feature.properties.gazetteer_name, true, event.lngLat);
  });

  map.on("click", "milestone-circles", (event) => {
    const feature = event.features?.[0];
    if (!feature) return;
    const index = sortedMilestones().findIndex((item) => item.properties.event_id === feature.properties.event_id);
    setActiveMilestone(Math.max(index, 0), false, event.lngLat);
  });

  ["mention-columns", "mention-points", "milestone-circles"].forEach((layerId) => {
    map.on("mouseenter", layerId, () => {
      map.getCanvas().style.cursor = "pointer";
    });
    map.on("mouseleave", layerId, () => {
      map.getCanvas().style.cursor = "";
    });
  });
}

function renderUi() {
  renderSummary();
  renderRankings();
  renderMilestoneList();
  renderMissingList();
  renderTimeline();
  const first = state.data.stats.rankings_mapped[0];
  if (first) {
    selectPlace(first.name, false, null, false);
  }
  setActiveMilestone(0, false, null, { silentDetail: true });
}

function renderSummary() {
  const summary = state.data.stats.summary;
  els.summaryGrid.innerHTML = [
    statTile(numberText(summary.mapped_columns), "已上图柱形"),
    statTile(numberText(summary.curated_places), "志书地名"),
    statTile(numberText(summary.top_count), summary.top_name || "最高频"),
  ].join("");
}

function statTile(value, label) {
  return `<div class="stat-tile"><strong>${escapeHtml(value)}</strong><span>${escapeHtml(label)}</span></div>`;
}

function renderRankings() {
  const keyword = els.placeSearch.value.trim();
  const items = state.data.stats.rankings_mapped.filter((item) => {
    if (state.activeLevel !== "全部" && item.level !== state.activeLevel) return false;
    if (!keyword) return true;
    return item.name.includes(keyword) || item.reason.includes(keyword);
  });
  els.rankList.innerHTML = items
    .map((item) => {
      const active = item.name === state.activePlaceName ? " is-active" : "";
      return `
        <button class="rank-item${active}" type="button" data-place="${escapeHtml(item.name)}">
          <span class="rank-badge">${escapeHtml(item.rank)}</span>
          <span class="rank-main">
            <strong>${escapeHtml(item.name)}</strong>
            <span>${escapeHtml(item.reason)}</span>
          </span>
          <span class="count-pill">${numberText(item.count)}次</span>
        </button>`;
    })
    .join("");
}

function renderMilestoneList() {
  els.milestoneList.innerHTML = sortedMilestones()
    .map((feature, index) => {
      const props = feature.properties;
      const active = index === state.activeMilestoneIndex ? " is-active" : "";
      return `
        <button class="milestone-item${active}" type="button" data-milestone="${index}">
          <span class="year-badge">${escapeHtml(props.start_year)}</span>
          <span class="milestone-main">
            <strong>${escapeHtml(props.title)}</strong>
            <span>${escapeHtml(props.gazetteer_place)} · ${escapeHtml(props.significance_short || props.milestone_significance)}</span>
          </span>
          <span class="level-pill">${escapeHtml(props.time_type)}</span>
        </button>`;
    })
    .join("");
}

function renderMissingList() {
  els.missingList.innerHTML = state.data.stats.missing_top
    .map((item) => {
      return `
        <div class="missing-item">
          <span class="rank-badge">${escapeHtml(item.rank)}</span>
          <span class="missing-main">
            <strong>${escapeHtml(item.name)}</strong>
            <span>${escapeHtml(item.reason)}</span>
          </span>
          <span class="count-pill">${numberText(item.count)}次</span>
        </div>`;
    })
    .join("");
}

function renderTimeline() {
  els.timelineTrack.innerHTML = sortedMilestones()
    .map((feature, index) => {
      const props = feature.properties;
      const active = index === state.activeMilestoneIndex ? " is-active" : "";
      return `
        <button class="timeline-chip${active}" type="button" data-timeline="${index}">
          <strong>${escapeHtml(props.start_year)} · ${escapeHtml(props.gazetteer_place)}</strong>
          <span>${escapeHtml(props.title)}</span>
        </button>`;
    })
    .join("");
  updateTimelineProgress();
}

function selectPlace(name, fly = true, popupLngLat = null, showPopup = true) {
  const point = state.data.mentionPoints.features.find((feature) => getPlaceName(feature.properties) === name);
  const column = state.data.mentionColumns.features.find((feature) => getPlaceName(feature.properties) === name);
  if (!point) return;
  state.activePlaceName = name;
  renderRankings();
  setActiveColumn(column);
  setPlaceDetail(point.properties);
  if (fly) {
    flyTo(point.geometry.coordinates, 15.1);
  }
  if (showPopup) {
    showPlacePopup(point, popupLngLat);
  }
}

function setActiveColumn(feature) {
  const source = state.map.getSource("active-column");
  if (!source) return;
  source.setData(feature ? featureCollection([feature]) : featureCollection());
}

function setPlaceDetail(props) {
  const count = props.count_num || props.canonical_mention_count || props.occurrence_count || 0;
  els.detailPanel.innerHTML = `
    <p class="detail-kicker">高频地名</p>
    <h2>${escapeHtml(props.gazetteer_name)}</h2>
    <div class="detail-meta">
      <span>${numberText(count)}次提及</span>
      <span>${escapeHtml(props.mention_level || props.time_type || "未分级")}</span>
      <span>${escapeHtml(props.coordinate_quality || props.coord_status || "坐标待核")}</span>
    </div>
    <div class="detail-text">
      <p><strong>为什么高频</strong>${escapeHtml(props.reason || "志书中多次出现，建议继续补充上下文解释。")}</p>
      <p><strong>地图对应</strong>${escapeHtml(props.gaode_map_item || props.gazetteer_name)} · ${escapeHtml(props.place_type || "地名")}</p>
    </div>`;
}

function setMilestoneDetail(props) {
  els.detailPanel.innerHTML = `
    <p class="detail-kicker">发展里程碑</p>
    <h2>${escapeHtml(props.start_year)} · ${escapeHtml(props.title)}</h2>
    <div class="detail-meta">
      <span>${escapeHtml(props.gazetteer_place)}</span>
      <span>${escapeHtml(props.time_type)}</span>
      <span>${escapeHtml(props.period_label || "时间待补")}</span>
    </div>
    <div class="detail-text">
      <p><strong>里程碑意义</strong>${escapeHtml(props.milestone_significance || "")}</p>
      <p><strong>志书原文</strong>${escapeHtml(props.source_text || "")}</p>
    </div>`;
}

function showPlacePopup(feature, popupLngLat = null) {
  const props = feature.properties;
  const count = props.count_num || props.canonical_mention_count || props.occurrence_count || 0;
  const html = `
    <h3 class="popup-title">${escapeHtml(props.gazetteer_name)}</h3>
    <div class="popup-meta">
      <span>${numberText(count)}次</span>
      <span>${escapeHtml(props.mention_level || "")}</span>
      <span>${escapeHtml(props.coordinate_quality || props.coord_status || "")}</span>
    </div>
    <p class="popup-body">${escapeHtml(props.reason || props.time_anchor_note || "")}</p>`;
  openPopup(popupLngLat || feature.geometry.coordinates, html);
}

function showMilestonePopup(feature, popupLngLat = null) {
  const props = feature.properties;
  const html = `
    <h3 class="popup-title">${escapeHtml(props.start_year)} ${escapeHtml(props.title)}</h3>
    <div class="popup-meta">
      <span>${escapeHtml(props.gazetteer_place)}</span>
      <span>${escapeHtml(props.time_type)}</span>
    </div>
    <p class="popup-body">${escapeHtml(props.milestone_significance || props.source_text || "")}</p>`;
  openPopup(popupLngLat || feature.geometry.coordinates, html);
}

function openPopup(lngLat, html) {
  if (state.popup) state.popup.remove();
  state.popup = new maplibregl.Popup({
    offset: 18,
    maxWidth: "360px",
    className: "story-popup",
    closeButton: true,
    closeOnClick: false,
  })
    .setLngLat(lngLat)
    .setHTML(html)
    .addTo(state.map);
}

function setActiveMilestone(index, fly = true, popupLngLat = null, options = {}) {
  const milestones = sortedMilestones();
  const feature = milestones[index];
  if (!feature) return;
  state.activeMilestoneIndex = index;
  const source = state.map?.getSource("active-milestone");
  if (source) source.setData(featureCollection([feature]));
  renderMilestoneList();
  renderTimeline();
  const props = feature.properties;
  els.timelineTitle.textContent = `${props.start_year} · ${props.title}`;
  els.timelineSubtitle.textContent = `${props.gazetteer_place}｜${props.significance_short || props.milestone_significance}`;
  if (!options.silentDetail) {
    setMilestoneDetail(props);
    showMilestonePopup(feature, popupLngLat);
  }
  const linkedPlace = props.gazetteer_place || props.gazetteer_name;
  if (linkedPlace) {
    const matchingColumn = state.data.mentionColumns.features.find(
      (item) => getPlaceName(item.properties) === linkedPlace,
    );
    setActiveColumn(matchingColumn);
    state.activePlaceName = linkedPlace;
    renderRankings();
  }
  if (fly) {
    flyTo(feature.geometry.coordinates, 15.25, {
      bearing: -28 + index * 3,
      pitch: 62,
    });
  }
}

function updateTimelineProgress() {
  const total = Math.max(sortedMilestones().length - 1, 1);
  const width = `${Math.round((state.activeMilestoneIndex / total) * 100)}%`;
  els.progressFill.style.width = width;
  document.querySelectorAll(".timeline-chip").forEach((node) => {
    node.classList.toggle("is-active", Number(node.dataset.timeline) === state.activeMilestoneIndex);
  });
}

function flyTo(coordinates, zoom = 15, extra = {}) {
  const desktopOffset = window.innerWidth > 980 ? [120, 0] : [0, 0];
  state.map.flyTo({
    center: coordinates,
    zoom,
    pitch: extra.pitch ?? 60,
    bearing: extra.bearing ?? -26,
    speed: 0.75,
    curve: 1.35,
    offset: desktopOffset,
    essential: true,
  });
}

function applyLevelFilter() {
  if (!state.mapReady) return;
  const filter = state.activeLevel === "全部" ? null : ["==", ["get", "mention_level"], state.activeLevel];
  ["mention-columns", "mention-column-outline", "mention-points", "mention-labels"].forEach((layerId) => {
    if (state.map.getLayer(layerId)) state.map.setFilter(layerId, filter);
  });
}

function applyTimeFilter() {
  if (!state.mapReady) return;
  const filter = state.activeTime === "全部" ? null : ["==", ["get", "time_type"], state.activeTime];
  ["temporal-points", "milestone-circles", "milestone-labels"].forEach((layerId) => {
    if (state.map.getLayer(layerId)) state.map.setFilter(layerId, filter);
  });
  updateMilestoneRouteForFilter();
}

function updateMilestoneRouteForFilter() {
  const source = state.map.getSource("milestone-route");
  if (!source) return;
  const features = sortedMilestones().filter((feature) => {
    return state.activeTime === "全部" || feature.properties.time_type === state.activeTime;
  });
  const coordinates = features.map((feature) => feature.geometry.coordinates);
  source.setData(
    coordinates.length > 1
      ? {
          type: "Feature",
          geometry: { type: "LineString", coordinates },
          properties: { name: "社区发展里程碑路径" },
        }
      : featureCollection(),
  );
}

function setLayerVisibility(key, visible) {
  if (!state.mapReady) return;
  const visibility = visible ? "visible" : "none";
  const groups = {
    columns: ["mention-columns", "mention-column-outline", "mention-points", "active-column-glow"],
    labels: ["mention-labels", "milestone-labels"],
    milestones: ["milestone-route", "milestone-circles", "active-milestone-ring"],
    temporal: ["temporal-points"],
  };
  (groups[key] || []).forEach((layerId) => {
    if (state.map.getLayer(layerId)) state.map.setLayoutProperty(layerId, "visibility", visibility);
  });
}

function setBaseLayer(base) {
  state.currentBase = base;
  const visible = (id, shouldShow) => {
    if (state.map.getLayer(id)) {
      state.map.setLayoutProperty(id, "visibility", shouldShow ? "visible" : "none");
    }
  };
  visible("amap-satellite", base === "satellite");
  visible("amap-satellite-labels", base === "satellite");
  visible("amap-vector", base === "vector");
  visible("osm-raster", base === "osm");
  document.querySelectorAll("#baseSwitch button").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.base === base);
  });
}

function switchTab(tab) {
  state.activeTab = tab;
  document.querySelectorAll(".tab-strip button").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.tab === tab);
  });
  $("#rankingPanel").classList.toggle("is-hidden", tab !== "ranking");
  $("#milestonePanel").classList.toggle("is-hidden", tab !== "milestone");
  $("#missingPanel").classList.toggle("is-hidden", tab !== "missing");
}

function startTimelinePlayback() {
  if (state.isPlaying) {
    stopTimelinePlayback();
    return;
  }
  state.isPlaying = true;
  els.playTimeline.classList.add("is-playing");
  els.playTimeline.querySelector("span").textContent = "暂停";
  const milestones = sortedMilestones();
  let index = state.activeMilestoneIndex;
  const stepMs = Math.max(900, Math.round(20000 / Math.max(milestones.length, 1)));

  const tick = () => {
    setActiveMilestone(index, true);
    index += 1;
    if (index >= milestones.length) {
      stopTimelinePlayback();
      return;
    }
    state.playTimer = window.setTimeout(tick, stepMs);
  };
  tick();
}

function stopTimelinePlayback() {
  state.isPlaying = false;
  window.clearTimeout(state.playTimer);
  state.playTimer = null;
  els.playTimeline.classList.remove("is-playing");
  els.playTimeline.querySelector("span").textContent = "播放20秒";
}

function bindUiEvents() {
  $("#resetView").addEventListener("click", () => {
    stopTimelinePlayback();
    state.map.flyTo({ ...INITIAL_VIEW, speed: 0.8, essential: true });
  });

  $("#baseSwitch").addEventListener("click", (event) => {
    const button = event.target.closest("button[data-base]");
    if (!button) return;
    setBaseLayer(button.dataset.base);
  });

  document.querySelectorAll("[data-layer-toggle]").forEach((checkbox) => {
    checkbox.addEventListener("change", () => {
      setLayerVisibility(checkbox.dataset.layerToggle, checkbox.checked);
    });
  });

  els.levelFilter.addEventListener("change", () => {
    state.activeLevel = els.levelFilter.value;
    applyLevelFilter();
    renderRankings();
  });

  els.timeFilter.addEventListener("change", () => {
    state.activeTime = els.timeFilter.value;
    applyTimeFilter();
  });

  els.placeSearch.addEventListener("input", renderRankings);

  els.rankList.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-place]");
    if (!button) return;
    stopTimelinePlayback();
    selectPlace(button.dataset.place, true);
  });

  els.milestoneList.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-milestone]");
    if (!button) return;
    stopTimelinePlayback();
    setActiveMilestone(Number(button.dataset.milestone), true);
  });

  els.timelineTrack.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-timeline]");
    if (!button) return;
    stopTimelinePlayback();
    setActiveMilestone(Number(button.dataset.timeline), true);
  });

  $(".tab-strip").addEventListener("click", (event) => {
    const button = event.target.closest("button[data-tab]");
    if (!button) return;
    switchTab(button.dataset.tab);
  });

  els.playTimeline.addEventListener("click", startTimelinePlayback);

  els.panelToggle.addEventListener("click", () => {
    els.sidePanel.classList.toggle("is-collapsed");
  });
}

function showLoadError(error) {
  els.detailPanel.innerHTML = `
    <p class="detail-kicker">读取失败</p>
    <h2>地图数据没有加载成功</h2>
    <p>${escapeHtml(error.message)}。请确认本页面通过本地服务打开，而不是直接双击 HTML 文件。</p>`;
}

async function main() {
  bindUiEvents();
  if (window.innerWidth <= 560) {
    els.sidePanel.classList.add("is-collapsed");
  }
  state.map = createMap();
  const styleLoaded = new Promise((resolve) => {
    if (state.map.isStyleLoaded()) {
      resolve();
      return;
    }
    state.map.once("style.load", resolve);
  });
  try {
    state.data = await loadAllData();
    await styleLoaded;
    state.mapReady = true;
    addDataLayers(state.map);
    renderUi();
    setBaseLayer("satellite");
  } catch (error) {
    showLoadError(error);
    console.error(error);
  }
}

main();
