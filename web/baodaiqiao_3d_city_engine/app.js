const DATASETS = {
  columns: "./data/mention_columns.geojson",
  milestones: "./data/milestones.geojson",
  stats: "./data/stats.json",
};

const state = {
  engine: null,
  scene: null,
  camera: null,
  columns: [],
  milestones: [],
  placeMeshes: [],
  milestoneMeshes: [],
  labels: [],
  timelineMeshes: [],
  selectedTimeType: "全部",
  currentYear: 0,
  minYear: 0,
  maxYear: 0,
  isPlaying: false,
  lastTick: performance.now(),
  world: null,
};

const $ = (id) => document.getElementById(id);

const clamp = (value, min, max) => Math.min(Math.max(value, min), max);

const toNumber = (value, fallback = 0) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
};

async function loadJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`${url} ${response.status}`);
  }
  return response.json();
}

function centroid(feature) {
  if (!feature?.geometry) return null;
  if (feature.geometry.type === "Point") {
    const [lon, lat] = feature.geometry.coordinates;
    return { lon, lat };
  }
  const ring = feature.geometry.coordinates?.[0];
  if (!Array.isArray(ring) || !ring.length) return null;
  const total = ring.reduce(
    (acc, coord) => ({ lon: acc.lon + coord[0], lat: acc.lat + coord[1] }),
    { lon: 0, lat: 0 },
  );
  return { lon: total.lon / ring.length, lat: total.lat / ring.length };
}

function prepareData(rawColumns, rawMilestones) {
  const columns = rawColumns.features
    .map((feature) => {
      const center = centroid(feature);
      const props = feature.properties || {};
      return {
        feature,
        props,
        lon: center?.lon,
        lat: center?.lat,
        rank: toNumber(props.rank_num || props.rank, 999),
        count: toNumber(props.count_num || props.canonical_mention_count || props.occurrence_count, 0),
        heightM: toNumber(props.height_m, 20),
        radiusM: toNumber(props.radius_m, 20),
        name: props.gazetteer_name || props.gaode_map_item || "未命名地名",
        timeType: props.time_type || "未分类",
        color: props.color || "#d83b2d",
      };
    })
    .filter((item) => Number.isFinite(item.lon) && Number.isFinite(item.lat))
    .sort((a, b) => a.rank - b.rank);

  const samePlaceCounter = new Map();
  const milestones = rawMilestones.features
    .map((feature) => {
      const props = feature.properties || {};
      const [lon, lat] = feature.geometry?.coordinates || [];
      const year = toNumber(props.start_year, 0);
      const key = `${lon?.toFixed?.(5)}:${lat?.toFixed?.(5)}`;
      const offsetIndex = samePlaceCounter.get(key) || 0;
      samePlaceCounter.set(key, offsetIndex + 1);
      return {
        feature,
        props,
        lon,
        lat,
        year,
        offsetIndex,
        title: props.title || props.map_label || "未命名里程碑",
        place: props.gazetteer_name || props.gazetteer_place || "未命名地点",
        color: props.color || "#a66cff",
      };
    })
    .filter((item) => Number.isFinite(item.lon) && Number.isFinite(item.lat) && Number.isFinite(item.year))
    .sort((a, b) => a.year - b.year);

  return { columns, milestones };
}

function buildWorld(columns, milestones) {
  const allCoords = [...columns, ...milestones];
  const centerLon = allCoords.reduce((sum, p) => sum + p.lon, 0) / allCoords.length;
  const centerLat = allCoords.reduce((sum, p) => sum + p.lat, 0) / allCoords.length;
  const metersPerLon = 111320 * Math.cos((centerLat * Math.PI) / 180);
  const metersPerLat = 110540;
  const scale = 0.072;

  const project = (lon, lat, y = 0) =>
    new BABYLON.Vector3(
      (lon - centerLon) * metersPerLon * scale,
      y,
      (centerLat - lat) * metersPerLat * scale,
    );

  const projected = allCoords.map((p) => project(p.lon, p.lat));
  const xs = projected.map((p) => p.x);
  const zs = projected.map((p) => p.z);
  const minX = Math.min(...xs) - 74;
  const maxX = Math.max(...xs) + 74;
  const minZ = Math.min(...zs) - 64;
  const maxZ = Math.max(...zs) + 64;

  return {
    centerLon,
    centerLat,
    scale,
    project,
    width: Math.max(160, maxX - minX),
    depth: Math.max(130, maxZ - minZ),
    center: new BABYLON.Vector3((minX + maxX) / 2, 0, (minZ + maxZ) / 2),
    bounds: { minX, maxX, minZ, maxZ },
  };
}

function makeStandardMaterial(scene, name, color, options = {}) {
  const material = new BABYLON.StandardMaterial(name, scene);
  material.diffuseColor = BABYLON.Color3.FromHexString(color);
  material.specularColor = new BABYLON.Color3(0.12, 0.14, 0.16);
  material.alpha = options.alpha ?? 1;
  if (options.emissive) {
    material.emissiveColor = BABYLON.Color3.FromHexString(color).scale(options.emissive);
  }
  return material;
}

function createLabel(scene, text, position, color = "#eef6f4", width = 11) {
  const texture = new BABYLON.DynamicTexture(`labelTexture-${text}`, { width: 720, height: 156 }, scene, true);
  const ctx = texture.getContext();
  ctx.clearRect(0, 0, 720, 156);
  ctx.fillStyle = "rgba(8, 14, 20, 0.72)";
  ctx.fillRect(0, 0, 720, 156);
  ctx.strokeStyle = "rgba(255, 255, 255, 0.22)";
  ctx.lineWidth = 5;
  ctx.strokeRect(3, 3, 714, 150);
  ctx.fillStyle = color;
  ctx.font = "700 42px Microsoft YaHei, PingFang SC, sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(text.slice(0, 18), 360, 78);
  texture.update();
  texture.hasAlpha = true;

  const plane = BABYLON.MeshBuilder.CreatePlane(`label-${text}`, { width, height: width * 0.22 }, scene);
  const material = new BABYLON.StandardMaterial(`labelMat-${text}`, scene);
  material.diffuseTexture = texture;
  material.opacityTexture = texture;
  material.emissiveColor = BABYLON.Color3.White();
  material.disableLighting = true;
  material.backFaceCulling = false;
  material.useAlphaFromDiffuseTexture = true;
  plane.material = material;
  plane.position = position;
  plane.billboardMode = BABYLON.Mesh.BILLBOARDMODE_ALL;
  state.labels.push(plane);
  return plane;
}

function deterministicRandom(seed) {
  let t = seed + 0x6d2b79f5;
  return function random() {
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function buildBasemapPaths(world) {
  const { minX, maxX, minZ, maxZ } = world.bounds;
  const width = maxX - minX;
  const depth = maxZ - minZ;
  const cx = world.center.x;
  const cz = world.center.z;

  const point = (x, z, y = 0.22) => new BABYLON.Vector3(x, y, z);

  return {
    water: [
      {
        name: "grand-canal",
        width: Math.max(7, width * 0.038),
        points: [
          point(minX - width * 0.08, cz + depth * 0.31),
          point(minX + width * 0.18, cz + depth * 0.23),
          point(cx - width * 0.08, cz + depth * 0.08),
          point(cx + width * 0.17, cz - depth * 0.03),
          point(maxX + width * 0.08, cz - depth * 0.21),
        ],
      },
      {
        name: "community-canal",
        width: Math.max(4.6, width * 0.024),
        points: [
          point(cx - width * 0.22, maxZ + depth * 0.04),
          point(cx - width * 0.12, cz + depth * 0.21),
          point(cx - width * 0.04, cz + depth * 0.02),
          point(cx + width * 0.02, cz - depth * 0.16),
          point(cx + width * 0.15, minZ - depth * 0.04),
        ],
      },
      {
        name: "taitai-lake-arm",
        width: Math.max(3.6, width * 0.018),
        points: [
          point(cx + width * 0.05, cz + depth * 0.34),
          point(cx + width * 0.19, cz + depth * 0.26),
          point(cx + width * 0.34, cz + depth * 0.27),
          point(cx + width * 0.46, cz + depth * 0.2),
        ],
      },
    ],
    roads: [
      {
        name: "urban-artery-east-west",
        width: 4.8,
        points: [
          point(minX - 24, cz + depth * 0.08),
          point(cx - width * 0.18, cz + depth * 0.05),
          point(cx + width * 0.12, cz + depth * 0.02),
          point(maxX + 24, cz - depth * 0.03),
        ],
      },
      {
        name: "urban-artery-north-south",
        width: 5.2,
        points: [
          point(cx + width * 0.09, minZ - 22),
          point(cx + width * 0.05, cz - depth * 0.12),
          point(cx + width * 0.02, cz + depth * 0.11),
          point(cx - width * 0.02, maxZ + 22),
        ],
      },
      {
        name: "ring-road-west",
        width: 3.8,
        points: [
          point(minX + width * 0.08, cz - depth * 0.24),
          point(minX + width * 0.25, cz - depth * 0.15),
          point(minX + width * 0.33, cz + depth * 0.07),
          point(minX + width * 0.28, cz + depth * 0.31),
        ],
      },
      {
        name: "ring-road-east",
        width: 3.8,
        points: [
          point(maxX - width * 0.12, cz - depth * 0.32),
          point(maxX - width * 0.24, cz - depth * 0.07),
          point(maxX - width * 0.19, cz + depth * 0.18),
          point(maxX - width * 0.08, cz + depth * 0.33),
        ],
      },
      {
        name: "community-spine",
        width: 3.2,
        points: [
          point(cx - width * 0.34, cz - depth * 0.04),
          point(cx - width * 0.17, cz - depth * 0.01),
          point(cx + width * 0.03, cz - depth * 0.06),
          point(cx + width * 0.24, cz - depth * 0.13),
          point(cx + width * 0.43, cz - depth * 0.12),
        ],
      },
    ],
  };
}

function createWorldMapper(world, textureSize) {
  const padding = Math.max(world.width, world.depth) * 0.06;
  const minX = world.bounds.minX - padding;
  const maxX = world.bounds.maxX + padding;
  const minZ = world.bounds.minZ - padding;
  const maxZ = world.bounds.maxZ + padding;
  return (point) => ({
    x: ((point.x - minX) / (maxX - minX)) * textureSize,
    y: ((point.z - minZ) / (maxZ - minZ)) * textureSize,
  });
}

function strokeMapPath(ctx, mapper, points, width, color, options = {}) {
  if (!points.length) return;
  ctx.save();
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.globalAlpha = options.alpha ?? 1;
  ctx.strokeStyle = color;
  ctx.lineWidth = width;
  if (options.blur) {
    ctx.shadowBlur = options.blur;
    ctx.shadowColor = options.shadowColor || color;
  }
  ctx.beginPath();
  points.forEach((point, index) => {
    const mapped = mapper(point);
    if (index === 0) ctx.moveTo(mapped.x, mapped.y);
    else ctx.lineTo(mapped.x, mapped.y);
  });
  ctx.stroke();
  ctx.restore();
}

function createGroundMapMaterial(scene, world, paths) {
  const size = 4096;
  const texture = new BABYLON.DynamicTexture("procedural-city-map", { width: size, height: size }, scene, false);
  const ctx = texture.getContext();
  const mapper = createWorldMapper(world, size);
  const random = deterministicRandom(9127);
  const background = ctx.createLinearGradient(0, 0, size, size);
  background.addColorStop(0, "#11242f");
  background.addColorStop(0.45, "#182d36");
  background.addColorStop(1, "#0e1a24");
  ctx.fillStyle = background;
  ctx.fillRect(0, 0, size, size);

  ctx.save();
  ctx.globalAlpha = 0.18;
  for (let index = 0; index < 1100; index += 1) {
    const x = random() * size;
    const y = random() * size;
    const w = 18 + random() * 120;
    const h = 12 + random() * 90;
    ctx.fillStyle = random() > 0.72 ? "#49605b" : "#263c43";
    ctx.fillRect(x, y, w, h);
  }
  ctx.restore();

  ctx.save();
  ctx.globalAlpha = 0.23;
  ctx.strokeStyle = "#6f8386";
  ctx.lineWidth = 2;
  for (let x = 90; x < size; x += 126) {
    ctx.beginPath();
    ctx.moveTo(x + (random() - 0.5) * 36, 0);
    ctx.lineTo(x + (random() - 0.5) * 48, size);
    ctx.stroke();
  }
  for (let y = 80; y < size; y += 118) {
    ctx.beginPath();
    ctx.moveTo(0, y + (random() - 0.5) * 34);
    ctx.lineTo(size, y + (random() - 0.5) * 46);
    ctx.stroke();
  }
  ctx.restore();

  paths.water.forEach((path) => {
    const width = path.width * 12.5;
    strokeMapPath(ctx, mapper, path.points, width + 34, "rgba(0, 0, 0, 0.34)");
    strokeMapPath(ctx, mapper, path.points, width + 12, "#0a3c4d", { alpha: 0.95 });
    strokeMapPath(ctx, mapper, path.points, width, "#0d6575", { alpha: 0.86 });
    strokeMapPath(ctx, mapper, path.points, Math.max(5, width * 0.1), "#57d5db", { alpha: 0.18, blur: 10 });
  });

  paths.roads.forEach((path) => {
    const width = path.width * 10;
    strokeMapPath(ctx, mapper, path.points, width + 18, "rgba(5, 9, 12, 0.48)");
    strokeMapPath(ctx, mapper, path.points, width, "#54666b", { alpha: 0.82 });
    strokeMapPath(ctx, mapper, path.points, Math.max(4, width * 0.12), "#9fb3b0", { alpha: 0.38 });
  });

  ctx.save();
  ctx.globalAlpha = 0.22;
  for (let index = 0; index < 180; index += 1) {
    const x = random() * size;
    const y = random() * size;
    const r = 10 + random() * 44;
    const glow = ctx.createRadialGradient(x, y, 0, x, y, r);
    glow.addColorStop(0, "rgba(248, 172, 78, 0.65)");
    glow.addColorStop(1, "rgba(248, 172, 78, 0)");
    ctx.fillStyle = glow;
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.restore();

  texture.update();

  const material = new BABYLON.StandardMaterial("mat-procedural-city-map", scene);
  material.diffuseTexture = texture;
  material.emissiveTexture = texture;
  material.diffuseColor = new BABYLON.Color3(0.82, 0.9, 0.94);
  material.emissiveColor = new BABYLON.Color3(0.18, 0.25, 0.28);
  material.specularColor = new BABYLON.Color3(0.06, 0.08, 0.09);
  material.alpha = 0.34;
  material.transparencyMode = BABYLON.Material.MATERIAL_ALPHABLEND;
  return material;
}

function createAerialBaseMaterial(scene) {
  const texture = new BABYLON.Texture("./assets/baodaiqiao-aerial-basemap.png", scene);
  texture.wrapU = BABYLON.Texture.CLAMP_ADDRESSMODE;
  texture.wrapV = BABYLON.Texture.CLAMP_ADDRESSMODE;
  const material = new BABYLON.StandardMaterial("mat-aerial-city-basemap", scene);
  material.diffuseTexture = texture;
  material.emissiveTexture = texture;
  material.diffuseColor = new BABYLON.Color3(0.98, 1, 1);
  material.emissiveColor = new BABYLON.Color3(0.42, 0.47, 0.52);
  material.specularColor = new BABYLON.Color3(0.08, 0.09, 0.1);
  return material;
}

function createRibbonPath(scene, name, points, width, material, y = 0.25) {
  const left = [];
  const right = [];
  points.forEach((point, index) => {
    const previous = points[Math.max(0, index - 1)];
    const next = points[Math.min(points.length - 1, index + 1)];
    const dx = next.x - previous.x;
    const dz = next.z - previous.z;
    const length = Math.hypot(dx, dz) || 1;
    const px = -dz / length;
    const pz = dx / length;
    left.push(new BABYLON.Vector3(point.x + px * width * 0.5, y, point.z + pz * width * 0.5));
    right.push(new BABYLON.Vector3(point.x - px * width * 0.5, y, point.z - pz * width * 0.5));
  });
  const mesh = BABYLON.MeshBuilder.CreateRibbon(
    name,
    { pathArray: [left, right], closeArray: false, sideOrientation: BABYLON.Mesh.DOUBLESIDE },
    scene,
  );
  mesh.material = material;
  return mesh;
}

function distancePointToSegment(x, z, a, b) {
  const dx = b.x - a.x;
  const dz = b.z - a.z;
  const lengthSq = dx * dx + dz * dz || 1;
  const t = clamp(((x - a.x) * dx + (z - a.z) * dz) / lengthSq, 0, 1);
  const px = a.x + t * dx;
  const pz = a.z + t * dz;
  return Math.hypot(x - px, z - pz);
}

function distanceToPath(x, z, points) {
  let min = Infinity;
  for (let index = 1; index < points.length; index += 1) {
    min = Math.min(min, distancePointToSegment(x, z, points[index - 1], points[index]));
  }
  return min;
}

function isClearOfCorridors(x, z, paths, margin) {
  const nearWater = paths.water.some((path) => distanceToPath(x, z, path.points) < path.width * 0.72 + margin);
  const nearRoad = paths.roads.some((path) => distanceToPath(x, z, path.points) < path.width * 0.65 + margin * 0.55);
  return !nearWater && !nearRoad;
}

function addPathLightDots(scene, path, material, count, y = 0.62) {
  for (let index = 0; index < count; index += 1) {
    const segmentIndex = index % (path.points.length - 1);
    const a = path.points[segmentIndex];
    const b = path.points[segmentIndex + 1];
    const t = (index + 0.5) / count;
    const localT = (t * (path.points.length - 1)) % 1;
    const x = a.x + (b.x - a.x) * localT;
    const z = a.z + (b.z - a.z) * localT;
    const dot = BABYLON.MeshBuilder.CreateSphere(`path-light-${path.name}-${index}`, { diameter: 0.55, segments: 12 }, scene);
    dot.position = new BABYLON.Vector3(x, y, z);
    dot.material = material;
  }
}

function createBridge(scene, name, position, rotation, width, length, materials) {
  const deck = BABYLON.MeshBuilder.CreateBox(`${name}-deck`, { width, height: 0.42, depth: length }, scene);
  deck.position = new BABYLON.Vector3(position.x, 1.05, position.z);
  deck.rotation.y = rotation;
  deck.material = materials.bridge;

  const railOffset = width * 0.43;
  [-1, 1].forEach((side) => {
    const rail = BABYLON.MeshBuilder.CreateBox(`${name}-rail-${side}`, { width: 0.22, height: 0.72, depth: length }, scene);
    rail.position = new BABYLON.Vector3(position.x + Math.cos(rotation) * railOffset * side, 1.55, position.z - Math.sin(rotation) * railOffset * side);
    rail.rotation.y = rotation;
    rail.material = materials.bridgeRail;
  });
}

function createContextCity(scene, world, materials) {
  const paths = buildBasemapPaths(world);
  materials.ground = createGroundMapMaterial(scene, world, paths);
  const groundWidth = world.width * 1.78;
  const groundDepth = world.depth * 1.68;
  const cityBounds = {
    minX: world.center.x - groundWidth / 2,
    maxX: world.center.x + groundWidth / 2,
    minZ: world.center.z - groundDepth / 2,
    maxZ: world.center.z + groundDepth / 2,
  };
  const aerialBase = BABYLON.MeshBuilder.CreateGround(
    "aerial-city-basemap",
    { width: groundWidth, height: groundDepth, subdivisions: 2 },
    scene,
  );
  aerialBase.position = world.center.add(new BABYLON.Vector3(0, -0.04, 0));
  aerialBase.material = createAerialBaseMaterial(scene);
  aerialBase.isPickable = false;

  const ground = BABYLON.MeshBuilder.CreateGround(
    "city-ground",
    { width: groundWidth, height: groundDepth, subdivisions: 18 },
    scene,
  );
  ground.position = world.center.clone();
  ground.material = materials.ground;

  paths.water.forEach((path) => {
    createRibbonPath(scene, `${path.name}-surface`, path.points, path.width, materials.water, 0.32);
    const edgeLine = BABYLON.MeshBuilder.CreateLines(`${path.name}-edge`, { points: path.points }, scene);
    edgeLine.color = BABYLON.Color3.FromHexString("#72e9ec");
  });

  paths.roads.forEach((path) => {
    createRibbonPath(scene, `${path.name}-road`, path.points, path.width, materials.road, 0.38);
    addPathLightDots(scene, path, materials.streetLight, 11, 0.64);
  });

  const random = deterministicRandom(20260618);
  const buildingMaterials = [materials.block, materials.blockCool, materials.blockWarm, materials.blockDark];
  for (let index = 0; index < 860; index += 1) {
    let x = 0;
    let z = 0;
    let tries = 0;
    do {
      x = cityBounds.minX + random() * (cityBounds.maxX - cityBounds.minX);
      z = cityBounds.minZ + random() * (cityBounds.maxZ - cityBounds.minZ);
      tries += 1;
    } while (!isClearOfCorridors(x, z, paths, 3.8) && tries < 16);

    if (tries >= 16) continue;

    const width = 1.2 + random() * 6.4;
    const depth = 1.2 + random() * 5.8;
    const height = 0.45 + Math.pow(random(), 2.0) * 10.4;
    const block = BABYLON.MeshBuilder.CreateBox(`context-block-${index}`, { width, height, depth }, scene);
    block.position = new BABYLON.Vector3(x, height / 2 + 0.45, z);
    block.rotation.y = (random() - 0.5) * 0.58;
    block.material = buildingMaterials[index % buildingMaterials.length];

    if (index % 5 === 0) {
      const roof = BABYLON.MeshBuilder.CreateBox(`context-roof-${index}`, { width: width * 0.92, height: 0.08, depth: depth * 0.92 }, scene);
      roof.position = new BABYLON.Vector3(x, height + 0.52, z);
      roof.rotation.y = block.rotation.y;
      roof.material = materials.roof;
    }
  }

  createBridge(scene, "baodaiqiao-bridge", world.center.add(new BABYLON.Vector3(-1, 0, 1)), -0.52, 7.2, 22, materials);
  createBridge(scene, "canal-crossing-east", world.center.add(new BABYLON.Vector3(world.width * 0.18, 0, -world.depth * 0.06)), -0.38, 5.4, 16, materials);
  addPathLightDots(scene, paths.water[0], materials.waterLight, 18, 0.58);
}

function createPlaceColumns(scene, world, columns) {
  const meshes = [];
  columns.forEach((item) => {
    const base = world.project(item.lon, item.lat);
    const height = clamp(item.heightM * 0.35, 4, 58);
    const radius = clamp(item.radiusM * 0.04, 1.15, 5.6);
    const mesh = BABYLON.MeshBuilder.CreateCylinder(
      `place-${item.rank}-${item.name}`,
      { height, diameter: radius * 2, tessellation: 40 },
      scene,
    );
    mesh.position = new BABYLON.Vector3(base.x, height / 2 + 0.2, base.z);
    const material = makeStandardMaterial(scene, `mat-place-${item.rank}`, item.color, { emissive: item.rank <= 5 ? 0.12 : 0 });
    mesh.material = material;
    mesh.metadata = { kind: "place", item, focus: mesh.position.clone() };
    meshes.push(mesh);

    const cap = BABYLON.MeshBuilder.CreateCylinder(
      `place-cap-${item.rank}`,
      { height: 0.24, diameter: radius * 2.25, tessellation: 40 },
      scene,
    );
    cap.position = new BABYLON.Vector3(base.x, height + 0.44, base.z);
    cap.material = makeStandardMaterial(scene, `mat-place-cap-${item.rank}`, "#ffcf77", { emissive: 0.25 });
    cap.metadata = mesh.metadata;
    meshes.push(cap);

    if (item.rank <= 12) {
      createLabel(scene, `${item.rank}. ${item.name}`, new BABYLON.Vector3(base.x, height + 6.5, base.z), "#fff4cf", 13);
    }
  });
  state.placeMeshes = meshes;
}

function offsetMilestonePosition(base, index) {
  const angle = index * 1.18;
  const radius = index === 0 ? 0 : 5.2 + index * 0.5;
  return base.add(new BABYLON.Vector3(Math.cos(angle) * radius, 0, Math.sin(angle) * radius));
}

function createMilestones(scene, world, milestones) {
  const meshes = [];
  const pathPoints = [];
  milestones.forEach((item, index) => {
    const base = offsetMilestonePosition(world.project(item.lon, item.lat), item.offsetIndex);
    pathPoints.push(new BABYLON.Vector3(base.x, 1.0, base.z));
    const beamHeight = 18 + (index % 4) * 2;
    const beam = BABYLON.MeshBuilder.CreateCylinder(
      `milestone-beam-${item.props.event_id || index}`,
      { height: beamHeight, diameterTop: 0.55, diameterBottom: 2.6, tessellation: 32 },
      scene,
    );
    beam.position = new BABYLON.Vector3(base.x, beamHeight / 2 + 1.0, base.z);
    beam.material = makeStandardMaterial(scene, `mat-milestone-${index}`, item.color, { alpha: 0.72, emissive: 0.55 });
    beam.metadata = { kind: "milestone", item, focus: beam.position.clone() };

    const sphere = BABYLON.MeshBuilder.CreateSphere(
      `milestone-core-${item.props.event_id || index}`,
      { diameter: 2.4, segments: 24 },
      scene,
    );
    sphere.position = new BABYLON.Vector3(base.x, beamHeight + 2.2, base.z);
    sphere.material = makeStandardMaterial(scene, `mat-milestone-core-${index}`, "#f8d27d", { emissive: 0.7 });
    sphere.metadata = beam.metadata;

    const ring = BABYLON.MeshBuilder.CreateTorus(
      `milestone-ring-${item.props.event_id || index}`,
      { diameter: 5.8, thickness: 0.12, tessellation: 48 },
      scene,
    );
    ring.position = new BABYLON.Vector3(base.x, 0.45, base.z);
    ring.rotation.x = Math.PI / 2;
    ring.material = makeStandardMaterial(scene, `mat-milestone-ring-${index}`, "#f5b54b", { alpha: 0.78, emissive: 0.35 });
    ring.metadata = beam.metadata;

    createLabel(scene, `${item.year}`, new BABYLON.Vector3(base.x, beamHeight + 7.0, base.z), "#ffdf9c", 7.2);
    meshes.push(beam, sphere, ring);
  });

  const timeline = BABYLON.MeshBuilder.CreateLines("milestone-time-path", { points: pathPoints }, scene);
  timeline.color = BABYLON.Color3.FromHexString("#f5b54b");
  state.timelineMeshes = [timeline];
  state.milestoneMeshes = meshes;
}

function createScene(columns, milestones) {
  const canvas = $("renderCanvas");
  state.engine = new BABYLON.Engine(canvas, true, {
    preserveDrawingBuffer: true,
    stencil: true,
    antialias: true,
  });

  const scene = new BABYLON.Scene(state.engine);
  scene.clearColor = new BABYLON.Color4(0.012, 0.02, 0.032, 1);
  scene.fogMode = BABYLON.Scene.FOGMODE_EXP2;
  scene.fogDensity = 0.0022;
  scene.fogColor = new BABYLON.Color3(0.035, 0.06, 0.082);
  state.scene = scene;
  state.world = buildWorld(columns, milestones);

  const camera = new BABYLON.ArcRotateCamera(
    "main-camera",
    -Math.PI * 0.74,
    Math.PI * 0.34,
    Math.max(state.world.width, state.world.depth) * 0.82,
    state.world.center.add(new BABYLON.Vector3(0, 10, 0)),
    scene,
  );
  camera.lowerRadiusLimit = 28;
  camera.upperRadiusLimit = 260;
  camera.lowerBetaLimit = 0.18;
  camera.upperBetaLimit = Math.PI * 0.48;
  camera.wheelPrecision = 38;
  camera.panningSensibility = 42;
  camera.attachControl(canvas, true);
  state.camera = camera;

  const hemi = new BABYLON.HemisphericLight("hemi", new BABYLON.Vector3(0, 1, 0), scene);
  hemi.intensity = 0.9;
  hemi.groundColor = new BABYLON.Color3(0.08, 0.15, 0.17);

  const sun = new BABYLON.DirectionalLight("sun", new BABYLON.Vector3(-0.6, -1, -0.35), scene);
  sun.position = new BABYLON.Vector3(90, 120, 80);
  sun.intensity = 1.35;

  const glow = new BABYLON.GlowLayer("city-glow", scene);
  glow.intensity = 0.5;

  const materials = {
    water: makeStandardMaterial(scene, "mat-water", "#0b5d6b", { alpha: 0.56, emissive: 0.08 }),
    road: makeStandardMaterial(scene, "mat-road", "#52666b", { alpha: 0.88, emissive: 0.04 }),
    block: makeStandardMaterial(scene, "mat-block", "#263b42", { alpha: 0.95 }),
    blockCool: makeStandardMaterial(scene, "mat-block-cool", "#304953", { alpha: 0.95 }),
    blockWarm: makeStandardMaterial(scene, "mat-block-warm", "#485848", { alpha: 0.92 }),
    blockDark: makeStandardMaterial(scene, "mat-block-dark", "#18272e", { alpha: 0.96 }),
    roof: makeStandardMaterial(scene, "mat-roof", "#70857b", { alpha: 0.88, emissive: 0.03 }),
    bridge: makeStandardMaterial(scene, "mat-bridge", "#d8b46e", { alpha: 0.96, emissive: 0.1 }),
    bridgeRail: makeStandardMaterial(scene, "mat-bridge-rail", "#ffe2a0", { alpha: 0.9, emissive: 0.16 }),
    streetLight: makeStandardMaterial(scene, "mat-street-light", "#ffd783", { emissive: 0.9 }),
    waterLight: makeStandardMaterial(scene, "mat-water-light", "#75eff5", { emissive: 0.85 }),
  };

  createContextCity(scene, state.world, materials);
  createPlaceColumns(scene, state.world, columns);
  createMilestones(scene, state.world, milestones);

  scene.onPointerObservable.add((pointerInfo) => {
    if (pointerInfo.type !== BABYLON.PointerEventTypes.POINTERPICK) return;
    const mesh = pointerInfo.pickInfo?.pickedMesh;
    if (mesh?.metadata) {
      selectObject(mesh.metadata);
    }
  });

  state.engine.runRenderLoop(() => {
    tickTimeline();
    scene.render();
  });

  window.addEventListener("resize", () => state.engine.resize());
}

function selectObject(metadata) {
  if (!metadata) return;
  if (metadata.kind === "place") {
    renderPlaceInspector(metadata.item);
    setRankActive(metadata.item.rank);
  }
  if (metadata.kind === "milestone") {
    renderMilestoneInspector(metadata.item);
    setRankActive(null);
  }
  focusCamera(metadata.focus);
}

function focusCamera(position) {
  const target = new BABYLON.Vector3(position.x, 8, position.z);
  BABYLON.Animation.CreateAndStartAnimation("camera-target", state.camera, "target", 45, 28, state.camera.target, target, 0);
  BABYLON.Animation.CreateAndStartAnimation(
    "camera-radius",
    state.camera,
    "radius",
    45,
    28,
    state.camera.radius,
    clamp(state.camera.radius * 0.72, 46, 110),
    0,
  );
}

function resetCamera() {
  const world = state.world;
  const target = world.center.add(new BABYLON.Vector3(0, 10, 0));
  BABYLON.Animation.CreateAndStartAnimation("camera-reset-target", state.camera, "target", 45, 30, state.camera.target, target, 0);
  BABYLON.Animation.CreateAndStartAnimation(
    "camera-reset-radius",
    state.camera,
    "radius",
    45,
    30,
    state.camera.radius,
    Math.max(world.width, world.depth) * 0.82,
    0,
  );
}

function renderTopList(columns) {
  const rankList = $("rankList");
  rankList.innerHTML = "";
  columns.slice(0, 16).forEach((item) => {
    const button = document.createElement("button");
    button.className = "rank-item";
    button.type = "button";
    button.dataset.rank = String(item.rank);
    button.innerHTML = `
      <span class="rank-index">${item.rank}</span>
      <span class="rank-name">${item.name}</span>
      <span class="rank-count">${item.count}次</span>
    `;
    button.addEventListener("click", () => {
      const mesh = state.placeMeshes.find((candidate) => candidate.metadata?.item?.rank === item.rank);
      if (mesh) selectObject(mesh.metadata);
    });
    rankList.appendChild(button);
  });
}

function setRankActive(rank) {
  document.querySelectorAll(".rank-item").forEach((item) => {
    item.classList.toggle("is-active", rank && item.dataset.rank === String(rank));
  });
}

function renderTimeFilters(columns) {
  const holder = $("timeTypeFilters");
  const types = ["全部", ...new Set(columns.map((item) => item.timeType).filter(Boolean))];
  holder.innerHTML = "";
  types.forEach((type) => {
    const button = document.createElement("button");
    button.className = "filter-button";
    button.type = "button";
    button.textContent = type;
    button.classList.toggle("is-active", type === state.selectedTimeType);
    button.addEventListener("click", () => {
      state.selectedTimeType = type;
      document.querySelectorAll(".filter-button").forEach((item) => item.classList.remove("is-active"));
      button.classList.add("is-active");
      updateVisibility();
    });
    holder.appendChild(button);
  });
}

function initTimeline(milestones) {
  state.minYear = Math.min(...milestones.map((item) => item.year));
  state.maxYear = Math.max(...milestones.map((item) => item.year));
  state.currentYear = state.maxYear;
  $("yearSlider").min = String(state.minYear);
  $("yearSlider").max = String(state.maxYear);
  $("yearSlider").value = String(state.currentYear);
  $("minYearLabel").textContent = String(state.minYear);
  $("maxYearLabel").textContent = String(state.maxYear);
  updateYearLabels();
}

function tickTimeline() {
  const now = performance.now();
  const elapsed = now - state.lastTick;
  state.lastTick = now;
  if (!state.isPlaying) return;
  const span = state.maxYear - state.minYear;
  state.currentYear += (span * elapsed) / 20000;
  if (state.currentYear >= state.maxYear) {
    state.currentYear = state.minYear;
  }
  $("yearSlider").value = String(Math.round(state.currentYear));
  updateYearLabels();
  updateVisibility();
}

function updateYearLabels() {
  const year = Math.round(state.currentYear);
  $("yearLabel").textContent = `${year}`;
  const currentYearMetric = $("currentYearMetric");
  if (currentYearMetric) {
    currentYearMetric.textContent = `${year}`;
  }
}

function updateVisibility() {
  const showPlaces = $("togglePlaces").checked;
  const showMilestones = $("toggleMilestones").checked;
  const showTimeline = $("toggleTimeline").checked;
  const showLabels = $("toggleLabels").checked;
  const year = Math.round(state.currentYear);

  state.placeMeshes.forEach((mesh) => {
    const item = mesh.metadata?.item;
    const matchType = state.selectedTimeType === "全部" || item?.timeType === state.selectedTimeType;
    mesh.setEnabled(showPlaces && matchType);
  });

  state.milestoneMeshes.forEach((mesh) => {
    const item = mesh.metadata?.item;
    mesh.setEnabled(showMilestones && item?.year <= year);
  });

  state.timelineMeshes.forEach((mesh) => mesh.setEnabled(showTimeline));
  state.labels.forEach((mesh) => mesh.setEnabled(showLabels));
}

function renderPlaceInspector(item) {
  $("inspectorKicker").textContent = "高频地名";
  $("inspectorTitle").textContent = item.name;
  $("inspectorMeta").textContent = `${item.count} 次提及 · ${item.timeType} · ${item.props.coordinate_quality || "坐标待核"}`;
  $("inspectorBody").innerHTML = `
    <div class="metric-pair"><span>排行</span><strong>${item.rank}</strong></div>
    <div class="metric-pair"><span>提及次数</span><strong>${item.count}次</strong></div>
    <div class="metric-pair"><span>柱体高度</span><strong>${Math.round(item.heightM)}m</strong></div>
    <div class="detail-block">
      <h3>为什么高频</h3>
      <p>${item.props.reason || "暂无说明"}</p>
    </div>
    <div class="detail-block">
      <h3>时间锚点</h3>
      <p>${item.props.time_anchor_note || item.props.time_context || "暂无时间锚点"}</p>
    </div>
  `;
}

function renderMilestoneInspector(item) {
  $("inspectorKicker").textContent = "里程碑";
  $("inspectorTitle").textContent = item.title;
  $("inspectorMeta").textContent = `${item.year} · ${item.place} · ${item.props.event_type || "event"}`;
  $("inspectorBody").innerHTML = `
    <div class="metric-pair"><span>年份</span><strong>${item.year}</strong></div>
    <div class="metric-pair"><span>地点</span><strong>${item.place}</strong></div>
    <div class="detail-block">
      <h3>里程碑意义</h3>
      <p>${item.props.milestone_significance || item.props.significance_short || "暂无说明"}</p>
    </div>
    <div class="detail-block">
      <h3>志书原文</h3>
      <p>${item.props.source_text || "暂无原文摘录"}</p>
    </div>
  `;
}

function initControls() {
  ["togglePlaces", "toggleMilestones", "toggleTimeline", "toggleLabels"].forEach((id) => {
    $(id).addEventListener("change", updateVisibility);
  });

  $("yearSlider").addEventListener("input", (event) => {
    state.currentYear = Number(event.target.value);
    updateYearLabels();
    updateVisibility();
  });

  $("playButton").addEventListener("click", () => {
    state.isPlaying = !state.isPlaying;
    $("playButton").textContent = state.isPlaying ? "暂停" : "播放";
  });

  $("resetCameraButton").addEventListener("click", resetCamera);
}

function renderInitialInspector(columns, milestones) {
  $("placeCount").textContent = columns.length;
  $("milestoneCount").textContent = milestones.length;
  $("runtimeHint").textContent = "鼠标拖拽旋转，滚轮缩放；点击柱体看地名统计，点击光柱看里程碑意义。";
}

async function boot() {
  try {
    const [rawColumns, rawMilestones] = await Promise.all([loadJson(DATASETS.columns), loadJson(DATASETS.milestones)]);
    const { columns, milestones } = prepareData(rawColumns, rawMilestones);
    state.columns = columns;
    state.milestones = milestones;
    createScene(columns, milestones);
    renderTopList(columns);
    renderTimeFilters(columns);
    initTimeline(milestones);
    initControls();
    renderInitialInspector(columns, milestones);
    updateVisibility();
    if (columns[0]) {
      const firstMesh = state.placeMeshes.find((mesh) => mesh.metadata?.item?.rank === columns[0].rank);
      if (firstMesh) renderPlaceInspector(firstMesh.metadata.item);
    }
  } catch (error) {
    console.error(error);
    $("runtimeHint").textContent = `载入失败：${error.message}`;
  }
}

boot();
