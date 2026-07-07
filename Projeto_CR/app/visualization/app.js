const canvas = document.getElementById("graphCanvas");
const ctx = canvas.getContext("2d", { alpha: false });
const tooltip = document.getElementById("tooltip");
const loading = document.getElementById("loading");
const ASSET_VERSION = "20260706-compare-1";

const els = {
  analysisWorkspace: document.getElementById("analysisWorkspace"),
  analysisTitle: document.getElementById("analysisTitle"),
  distributionCanvas: document.getElementById("distributionCanvas"),
  distributionMeta: document.getElementById("distributionMeta"),
  egoCanvas: document.getElementById("egoCanvas"),
  egoMeta: document.getElementById("egoMeta"),
  topEdgesCanvas: document.getElementById("topEdgesCanvas"),
  topEdgesMeta: document.getElementById("topEdgesMeta"),
  exportJsonButton: document.getElementById("exportJsonButton"),
  exportCsvButton: document.getElementById("exportCsvButton"),
  compareWorkspace: document.getElementById("compareWorkspace"),
  compareTitle: document.getElementById("compareTitle"),
  compareModeButton: document.getElementById("compareModeButton"),
  runCompareButton: document.getElementById("runCompareButton"),
  clearCompareButton: document.getElementById("clearCompareButton"),
  loadProjectCompareButton: document.getElementById("loadProjectCompareButton"),
  compareScopeSelect: document.getElementById("compareScopeSelect"),
  projectImportStatus: document.getElementById("projectImportStatus"),
  builtInDatasetSelect: document.getElementById("builtInDatasetSelect"),
  loadBuiltInDatasetButton: document.getElementById("loadBuiltInDatasetButton"),
  builtInDatasetStatus: document.getElementById("builtInDatasetStatus"),
  randomImportInput: document.getElementById("randomImportInput"),
  randomImportStatus: document.getElementById("randomImportStatus"),
  smallWorldImportInput: document.getElementById("smallWorldImportInput"),
  smallWorldImportStatus: document.getElementById("smallWorldImportStatus"),
  scaleFreeImportInput: document.getElementById("scaleFreeImportInput"),
  scaleFreeImportStatus: document.getElementById("scaleFreeImportStatus"),
  compareMeta: document.getElementById("compareMeta"),
  compareSummary: document.getElementById("compareSummary"),
  compareTableBody: document.getElementById("compareTableBody"),
  mapModeButton: document.getElementById("mapModeButton"),
  analysisModeButton: document.getElementById("analysisModeButton"),
  statNodes: document.getElementById("statNodes"),
  statEdges: document.getElementById("statEdges"),
  statCommunities: document.getElementById("statCommunities"),
  statLayer: document.getElementById("statLayer"),
  layerSelect: document.getElementById("layerSelect"),
  layoutModeSelect: document.getElementById("layoutModeSelect"),
  influenceSelect: document.getElementById("influenceSelect"),
  influenceLegend: document.getElementById("influenceLegend"),
  sentimentSelect: document.getElementById("sentimentSelect"),
  weightInput: document.getElementById("weightInput"),
  weightOutput: document.getElementById("weightOutput"),
  edgesToggle: document.getElementById("edgesToggle"),
  labelsToggle: document.getElementById("labelsToggle"),
  searchInput: document.getElementById("searchInput"),
  topEdgesInput: document.getElementById("topEdgesInput"),
  topEdgesOutput: document.getElementById("topEdgesOutput"),
  searchButton: document.getElementById("searchButton"),
  fitButton: document.getElementById("fitButton"),
  runAnalysisButton: document.getElementById("runAnalysisButton"),
  selectionPanel: document.getElementById("selectionPanel"),
  communityList: document.getElementById("communityList"),
};

const state = {
  data: null,
  nodes: [],
  edges: [],
  edgeCache: new Map(),
  communities: [],
  nodeById: new Map(),
  layer: "combined",
  layoutMode: "communities",
  influenceMode: "default",
  influenceComputedFor: "",
  influenceMax: { popularity: 1, bridge: 1, combined: 1 },
  sentiment: "all",
  minWeight: 1,
  showEdges: false,
  showLabels: true,
  selectedNode: null,
  hoverNode: null,
  selectedCommunity: null,
  mode: "map",
  topEdgesLimit: 250,
  lastAnalysis: null,
  compareDatasets: {
    project: null,
    random: null,
    smallWorld: null,
    scaleFree: null,
  },
  builtInComparisonDatasets: [],
  extraCompareDatasets: [],
  compareResults: [],
  transform: { x: 0, y: 0, scale: 1 },
  dragging: false,
  moved: false,
  lastPointer: { x: 0, y: 0 },
  dpr: 1,
  width: 0,
  height: 0,
};

const fmt = new Intl.NumberFormat("pt-BR");
const pct = new Intl.NumberFormat("pt-BR", {
  style: "percent",
  maximumFractionDigits: 1,
});
const decimal = new Intl.NumberFormat("pt-BR", {
  maximumFractionDigits: 3,
});
const compactNumber = new Intl.NumberFormat("pt-BR", {
  notation: "compact",
  maximumFractionDigits: 1,
});

const compareSlots = [
  { id: "project", name: "Projeto Reddit", expected: "projeto", status: "projectImportStatus" },
  { id: "random", name: "Rede aleatoria", expected: "aleatoria", input: "randomImportInput", status: "randomImportStatus" },
  { id: "smallWorld", name: "Mundo pequeno", expected: "mundo pequeno", input: "smallWorldImportInput", status: "smallWorldImportStatus" },
  { id: "scaleFree", name: "Sem escala", expected: "sem escala", input: "scaleFreeImportInput", status: "scaleFreeImportStatus" },
];

function formatNumber(value) {
  return fmt.format(Math.round(value || 0));
}

function hashString(value) {
  let hash = 2166136261;
  for (let index = 0; index < value.length; index += 1) {
    hash ^= value.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function normalizedHash(value, salt = "") {
  return hashString(`${salt}:${value}`) / 4294967295;
}

function getNodeX(node) {
  return state.layoutMode === "dispersed" ? node.scatterX : node.x;
}

function getNodeY(node) {
  return state.layoutMode === "dispersed" ? node.scatterY : node.y;
}

function currentBounds() {
  if (state.layoutMode !== "dispersed") return state.data?.meta.bounds;
  return state.scatterBounds;
}

function influenceRatio(node, key) {
  return Math.min(1, (node[key] || 0) / Math.max(1, state.influenceMax[key.replace("Score", "")] || 1));
}

function nodeVisualColor(node) {
  if (state.influenceMode === "popularity") return "#2563eb";
  if (state.influenceMode === "bridge") return "#d97706";
  if (state.influenceMode === "combined") {
    const bridge = influenceRatio(node, "bridgeScore");
    const popularity = influenceRatio(node, "popularityScore");
    if (bridge >= 0.48 && popularity >= 0.42) return "#7c3aed";
    if (bridge > popularity) return "#d97706";
    return "#2563eb";
  }
  return node.color;
}

function nodeVisualRadius(node) {
  if (state.influenceMode === "default") {
    return Math.max(1.25, Math.min(9, node.size * Math.sqrt(state.transform.scale) * 0.22));
  }
  const key = state.influenceMode === "popularity"
    ? "popularityScore"
    : state.influenceMode === "bridge"
      ? "bridgeScore"
      : "combinedScore";
  const score = influenceRatio(node, key);
  const base = 1.15 + 8.8 * Math.sqrt(score);
  return Math.max(1.15, Math.min(11, base * Math.sqrt(state.transform.scale)));
}

function worldToScreen(x, y) {
  return {
    x: x * state.transform.scale + state.transform.x,
    y: y * state.transform.scale + state.transform.y,
  };
}

function screenToWorld(x, y) {
  return {
    x: (x - state.transform.x) / state.transform.scale,
    y: (y - state.transform.y) / state.transform.scale,
  };
}

function resizeCanvas() {
  const rect = canvas.getBoundingClientRect();
  state.dpr = window.devicePixelRatio || 1;
  state.width = rect.width;
  state.height = rect.height;
  canvas.width = Math.max(1, Math.floor(rect.width * state.dpr));
  canvas.height = Math.max(1, Math.floor(rect.height * state.dpr));
  ctx.setTransform(state.dpr, 0, 0, state.dpr, 0, 0);
  draw();
}

function fitToGraph(bounds = state.data?.meta.bounds) {
  if (!bounds) return;
  const dx = Math.max(1, bounds.maxX - bounds.minX);
  const dy = Math.max(1, bounds.maxY - bounds.minY);
  const scale = Math.min((state.width - 72) / dx, (state.height - 72) / dy);
  state.transform.scale = Math.max(0.1, scale);
  state.transform.x = state.width / 2 - ((bounds.minX + bounds.maxX) / 2) * state.transform.scale;
  state.transform.y = state.height / 2 - ((bounds.minY + bounds.maxY) / 2) * state.transform.scale;
  draw();
}

function fitToCurrentLayout() {
  fitToGraph(currentBounds());
}

function edgeVisible(edge) {
  if (edge.w < state.minWeight) return false;
  if (state.sentiment === "negative") return edge.n > edge.p;
  if (state.sentiment === "positive") return edge.p >= edge.n;
  return true;
}

function prepareScatterLayout() {
  const bounds = state.data?.meta.bounds || { minX: -210, maxX: 210, minY: -210, maxY: 210 };
  const spread = Math.max(bounds.maxX - bounds.minX, bounds.maxY - bounds.minY, 420);
  const radius = spread * 0.52;
  const scatterBounds = {
    minX: Infinity,
    maxX: -Infinity,
    minY: Infinity,
    maxY: -Infinity,
  };

  for (const node of state.nodes) {
    const angle = normalizedHash(node.id, "angle") * Math.PI * 2;
    const distance = radius * Math.sqrt(normalizedHash(node.id, "distance"));
    const jitter = (normalizedHash(node.id, "jitter") - 0.5) * 6;
    node.scatterX = Math.cos(angle) * (distance + jitter);
    node.scatterY = Math.sin(angle) * (distance - jitter);
    scatterBounds.minX = Math.min(scatterBounds.minX, node.scatterX);
    scatterBounds.maxX = Math.max(scatterBounds.maxX, node.scatterX);
    scatterBounds.minY = Math.min(scatterBounds.minY, node.scatterY);
    scatterBounds.maxY = Math.max(scatterBounds.maxY, node.scatterY);
  }
  state.scatterBounds = scatterBounds;
}

function resetInfluenceMetrics() {
  for (const node of state.nodes) {
    node.popularityScore = 0;
    node.bridgeScore = 0;
    node.combinedScore = 0;
    node.bridgeWeight = 0;
    node.bridgeCommunityCount = 0;
  }
  state.influenceMax = { popularity: 1, bridge: 1, combined: 1 };
  state.influenceComputedFor = "";
}

function computeInfluenceMetrics() {
  if (!state.edges.length) {
    resetInfluenceMetrics();
    return;
  }
  const signature = `${state.layer}:${state.sentiment}:${state.minWeight}:${state.edges.length}`;
  if (state.influenceComputedFor === signature) return;

  const bridgeCommunities = new Map();
  for (const node of state.nodes) {
    node.popularityScore = 0;
    node.bridgeScore = 0;
    node.combinedScore = 0;
    node.bridgeWeight = 0;
    node.bridgeCommunityCount = 0;
    bridgeCommunities.set(node.id, new Set());
  }

  for (const edge of state.edges) {
    if (!edgeVisible(edge)) continue;
    const source = state.nodes[edge.s];
    const target = state.nodes[edge.t];
    if (!source || !target) continue;

    source.popularityScore += edge.w;
    target.popularityScore += edge.w;

    if (source.community !== target.community) {
      source.bridgeWeight += edge.w;
      target.bridgeWeight += edge.w;
      bridgeCommunities.get(source.id)?.add(target.community);
      bridgeCommunities.get(target.id)?.add(source.community);
    }
  }

  let maxPopularity = 1;
  let maxBridge = 1;
  for (const node of state.nodes) {
    node.bridgeCommunityCount = bridgeCommunities.get(node.id)?.size || 0;
    node.bridgeScore = node.bridgeWeight * (1 + Math.log1p(node.bridgeCommunityCount));
    maxPopularity = Math.max(maxPopularity, node.popularityScore);
    maxBridge = Math.max(maxBridge, node.bridgeScore);
  }

  for (const node of state.nodes) {
    const popularityRatio = node.popularityScore / maxPopularity;
    const bridgeRatio = node.bridgeScore / maxBridge;
    node.combinedScore = Math.sqrt(popularityRatio * bridgeRatio);
  }

  state.influenceMax = { popularity: maxPopularity, bridge: maxBridge, combined: 1 };
  state.influenceComputedFor = signature;
}

function updateInfluenceLegend() {
  if (!els.influenceLegend) return;
  const labels = {
    default: "Cor original por sentimento; tamanho por força/PageRank.",
    popularity: "Azul maior = mais peso recebido/enviado no filtro atual.",
    bridge: "Laranja maior = mais conexões entre comunidades diferentes.",
    combined: "Roxo = alto peso e alta conexão entre comunidades.",
  };
  els.influenceLegend.textContent = labels[state.influenceMode];
}

async function refreshInfluenceView({ refit = false } = {}) {
  if (state.layoutMode === "dispersed" || state.influenceMode !== "default") {
    if (!state.edges.length) state.edges = await loadEdges(state.layer);
    computeInfluenceMetrics();
  }
  updateInfluenceLegend();
  if (refit) fitToCurrentLayout();
  draw();
}

function drawEdges() {
  if (!state.showEdges) return;
  const edges = state.edges;
  const nodes = state.nodes;
  ctx.save();
  const dispersed = state.layoutMode === "dispersed";
  ctx.lineWidth = dispersed
    ? Math.max(0.45, Math.min(2.4, state.transform.scale * 0.045))
    : Math.max(0.18, Math.min(1.2, state.transform.scale * 0.015));
  ctx.globalAlpha = state.dragging
    ? (dispersed ? 0.08 : 0.035)
    : (dispersed ? 0.22 : 0.07);

  let drawn = 0;
  const maxDuringDrag = 55000;
  for (const edge of edges) {
    if (!edgeVisible(edge)) continue;
    if (state.dragging && drawn > maxDuringDrag) break;
    const s = nodes[edge.s];
    const t = nodes[edge.t];
    if (!s || !t) continue;
    const a = worldToScreen(getNodeX(s), getNodeY(s));
    const b = worldToScreen(getNodeX(t), getNodeY(t));
    if (
      (a.x < -30 && b.x < -30) ||
      (a.x > state.width + 30 && b.x > state.width + 30) ||
      (a.y < -30 && b.y < -30) ||
      (a.y > state.height + 30 && b.y > state.height + 30)
    ) {
      continue;
    }
    ctx.strokeStyle = edge.n > edge.p
      ? (dispersed ? "rgba(220,53,88,0.72)" : "rgba(220,53,88,0.35)")
      : (dispersed ? "rgba(50,84,170,0.62)" : "rgba(65,96,174,0.28)");
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
    drawn += 1;
  }
  ctx.restore();
}

function drawCommunities() {
  if (state.layoutMode !== "communities") return;
  const compact = state.width < 760 || state.height < 460;
  const limit = state.showLabels ? (compact ? 4 : 10) : 6;
  ctx.save();
  ctx.setLineDash([4, 4]);
  for (const community of state.communities.slice(0, limit)) {
    const center = worldToScreen(community.x, community.y);
    const radius = Math.max(28, Math.sqrt(community.nodeCount) * state.transform.scale * 0.18);
    const active = state.selectedCommunity === community.id;
    ctx.strokeStyle = active ? "#111827" : "rgba(17,24,39,0.52)";
    ctx.lineWidth = active ? 2 : 1;
    ctx.beginPath();
    ctx.ellipse(center.x, center.y, radius * 1.42, radius, 0, 0, Math.PI * 2);
    ctx.stroke();

    if (state.showLabels) {
      ctx.setLineDash([]);
      ctx.fillStyle = "#111827";
      ctx.font = `800 ${compact ? 11 : 14}px Inter, Segoe UI, sans-serif`;
      ctx.textAlign = "center";
      ctx.fillText(community.label.toUpperCase(), center.x, center.y - radius - 8);
      ctx.setLineDash([4, 4]);
    }
  }
  ctx.restore();
}

function drawNodes() {
  ctx.save();
  for (const node of state.nodes) {
    if (state.layoutMode === "communities" && state.selectedCommunity !== null && node.community !== state.selectedCommunity) {
      ctx.globalAlpha = 0.16;
    } else {
      ctx.globalAlpha = 0.78;
    }
    const p = worldToScreen(getNodeX(node), getNodeY(node));
    if (p.x < -20 || p.x > state.width + 20 || p.y < -20 || p.y > state.height + 20) continue;
    const radius = nodeVisualRadius(node);
    ctx.fillStyle = nodeVisualColor(node);
    ctx.beginPath();
    ctx.arc(p.x, p.y, radius, 0, Math.PI * 2);
    ctx.fill();

    if (state.hoverNode === node || state.selectedNode === node) {
      ctx.globalAlpha = 1;
      ctx.strokeStyle = "#111827";
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(p.x, p.y, radius + 4, 0, Math.PI * 2);
      ctx.stroke();
    }
  }
  ctx.restore();
}

function drawFocusLinks() {
  if (!state.selectedNode) return;
  const selectedIndex = state.nodes.indexOf(state.selectedNode);
  const selected = worldToScreen(getNodeX(state.selectedNode), getNodeY(state.selectedNode));
  ctx.save();
  const dispersed = state.layoutMode === "dispersed";
  ctx.lineWidth = dispersed ? 2.2 : 1.4;
  ctx.globalAlpha = dispersed ? 0.92 : 0.75;
  let drawn = 0;
  for (const edge of state.edges) {
    if (drawn > 420) break;
    if (!edgeVisible(edge)) continue;
    if (edge.s !== selectedIndex && edge.t !== selectedIndex) continue;
    const other = state.nodes[edge.s === selectedIndex ? edge.t : edge.s];
    const p = worldToScreen(getNodeX(other), getNodeY(other));
    ctx.strokeStyle = edge.n > edge.p
      ? (dispersed ? "rgba(220,53,88,0.92)" : "rgba(220,53,88,0.72)")
      : (dispersed ? "rgba(37,99,235,0.88)" : "rgba(65,96,174,0.64)");
    ctx.beginPath();
    ctx.moveTo(selected.x, selected.y);
    ctx.lineTo(p.x, p.y);
    ctx.stroke();
    drawn += 1;
  }
  ctx.restore();
}

function draw() {
  if (!state.data) return;
  ctx.clearRect(0, 0, state.width, state.height);
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, state.width, state.height);
  drawCommunities();
  drawEdges();
  drawFocusLinks();
  drawNodes();
}

function nearestNode(screenX, screenY) {
  let best = null;
  let bestDistance = Infinity;
  for (const node of state.nodes) {
    if (state.layoutMode === "communities" && state.selectedCommunity !== null && node.community !== state.selectedCommunity) continue;
    const p = worldToScreen(getNodeX(node), getNodeY(node));
    const dx = p.x - screenX;
    const dy = p.y - screenY;
    const distance = dx * dx + dy * dy;
    const threshold = Math.max(64, node.size * node.size * state.transform.scale * 1.4);
    if (distance < threshold && distance < bestDistance) {
      best = node;
      bestDistance = distance;
    }
  }
  return best;
}

function nodeDetails(node) {
  const influenceDetails = state.influenceComputedFor
    ? `
    <div class="metric-line"><span>popularidade filtrada</span><strong>${formatNumber(node.popularityScore)}</strong></div>
    <div class="metric-line"><span>peso ponte</span><strong>${formatNumber(node.bridgeWeight)}</strong></div>
    <div class="metric-line"><span>comunidades ponte</span><strong>${formatNumber(node.bridgeCommunityCount)}</strong></div>
    <div class="metric-line"><span>influencia mista</span><strong>${pct.format(node.combinedScore || 0)}</strong></div>
  `
    : "";
  return `
    <strong>${node.id}</strong>
    <div class="metric-line"><span>comunidade</span><strong>${node.communityLabel}</strong></div>
    <div class="metric-line"><span>papel</span><strong>${node.role}</strong></div>
    <div class="metric-line"><span>forca total</span><strong>${formatNumber(node.totalStrength)}</strong></div>
    <div class="metric-line"><span>entrada</span><strong>${formatNumber(node.inStrength)}</strong></div>
    <div class="metric-line"><span>saida</span><strong>${formatNumber(node.outStrength)}</strong></div>
    <div class="metric-line"><span>PageRank</span><strong>${node.pagerank.toFixed(6)}</strong></div>
    <div class="metric-line"><span>negatividade</span><strong>${pct.format(node.negativeShare)}</strong></div>
    ${influenceDetails}
  `;
}

function setSelectedNode(node) {
  state.selectedNode = node;
  if (node) {
    if (state.layoutMode === "communities") state.selectedCommunity = node.community;
    els.selectionPanel.innerHTML = nodeDetails(node);
  } else {
    els.selectionPanel.textContent = "Passe o mouse sobre um ponto ou busque um subreddit.";
  }
  draw();
}

function showTooltip(node, x, y) {
  if (!node) {
    tooltip.hidden = true;
    return;
  }
  tooltip.innerHTML = `
    <strong>${node.id}</strong>
    ${node.communityLabel}<br />
    forca total: ${formatNumber(node.totalStrength)}<br />
    PageRank: ${node.pagerank.toFixed(6)}
    ${state.influenceComputedFor ? `<br />ponte: ${formatNumber(node.bridgeWeight)}` : ""}
  `;
  tooltip.style.left = `${Math.min(state.width - 292, x + 14)}px`;
  tooltip.style.top = `${Math.min(state.height - 120, y + 14)}px`;
  tooltip.hidden = false;
}

function zoomAt(screenX, screenY, delta) {
  const before = screenToWorld(screenX, screenY);
  const factor = delta > 0 ? 0.9 : 1.1;
  state.transform.scale = Math.max(0.04, Math.min(20, state.transform.scale * factor));
  const after = worldToScreen(before.x, before.y);
  state.transform.x += screenX - after.x;
  state.transform.y += screenY - after.y;
  draw();
}

function updateStats() {
  els.statNodes.textContent = formatNumber(state.data.meta.nodeCount);
  els.statEdges.textContent = formatNumber(state.data.meta.edgeCount[state.layer]);
  els.statCommunities.textContent = formatNumber(state.data.meta.communityCount);
  els.statLayer.textContent = state.layer;
}

function invalidateProjectCompare() {
  if (!state.compareDatasets.project) return;
  state.compareDatasets.project = null;
  setImportStatus("project", "Filtro alterado. Recalcule o projeto.");
  if (state.mode === "compare") renderCompareResults();
}

function setMode(mode) {
  state.mode = mode;
  const analysisMode = mode === "analysis";
  const compareMode = mode === "compare";
  canvas.hidden = analysisMode || compareMode;
  els.analysisWorkspace.hidden = !analysisMode;
  els.compareWorkspace.hidden = !compareMode;
  els.mapModeButton.classList.toggle("active", !analysisMode);
  els.mapModeButton.classList.toggle("active", mode === "map");
  els.analysisModeButton.classList.toggle("active", analysisMode);
  els.compareModeButton.classList.toggle("active", compareMode);
  if (analysisMode) {
    runAnalysis();
  } else if (compareMode) {
    renderCompareResults();
  } else {
    draw();
  }
}

async function loadEdges(layer) {
  if (state.edgeCache.has(layer)) {
    return state.edgeCache.get(layer);
  }
  loading.hidden = false;
  loading.classList.remove("is-hidden");
  loading.innerHTML = `<strong>Carregando arestas</strong><span>Camada ${layer}...</span>`;
  const response = await fetch(`./public/edges-${layer}.json?v=${ASSET_VERSION}`);
  if (!response.ok) throw new Error(`Falha ao carregar edges-${layer}.json: ${response.status}`);
  const edges = await response.json();
  state.edgeCache.set(layer, edges);
  loading.hidden = true;
  loading.classList.add("is-hidden");
  return edges;
}

async function updateLayer() {
  state.layer = els.layerSelect.value;
  if (state.showEdges || state.edges.length > 0 || state.layoutMode === "dispersed" || state.influenceMode !== "default") {
    state.edges = await loadEdges(state.layer);
  }
  state.influenceComputedFor = "";
  computeInfluenceMetrics();
  updateStats();
  invalidateProjectCompare();
  if (state.mode === "analysis") runAnalysis();
  draw();
}

function getFilteredEdges() {
  return state.edges.filter(edgeVisible);
}

function getAnalysisCenter() {
  const query = els.searchInput.value.trim().toLowerCase();
  if (query && state.nodeById.has(query)) return query;
  if (state.selectedNode) return state.selectedNode.id;
  return "subredditdrama";
}

function computeAnalysis() {
  const edges = getFilteredEdges();
  const inStrength = new Map();
  const outStrength = new Map();
  const inDegree = new Map();
  const outDegree = new Map();
  const edgeWeights = [];
  const seenIn = new Set();
  const seenOut = new Set();

  for (const edge of edges) {
    const source = state.nodes[edge.s]?.id;
    const target = state.nodes[edge.t]?.id;
    if (!source || !target) continue;
    inStrength.set(target, (inStrength.get(target) || 0) + edge.w);
    outStrength.set(source, (outStrength.get(source) || 0) + edge.w);
    const inKey = `${source}->${target}`;
    const outKey = `${source}->${target}`;
    if (!seenIn.has(inKey)) {
      inDegree.set(target, (inDegree.get(target) || 0) + 1);
      seenIn.add(inKey);
    }
    if (!seenOut.has(outKey)) {
      outDegree.set(source, (outDegree.get(source) || 0) + 1);
      seenOut.add(outKey);
    }
    edgeWeights.push(edge.w);
  }

  const nodeIds = new Set([...inStrength.keys(), ...outStrength.keys()]);
  const nodeRows = [...nodeIds].map((id) => ({
    id,
    inStrength: inStrength.get(id) || 0,
    outStrength: outStrength.get(id) || 0,
    totalStrength: (inStrength.get(id) || 0) + (outStrength.get(id) || 0),
    inDegree: inDegree.get(id) || 0,
    outDegree: outDegree.get(id) || 0,
  }));

  const topEdges = [...edges]
    .sort((a, b) => b.w - a.w)
    .slice(0, state.topEdgesLimit);
  const center = getAnalysisCenter();
  const centerIndex = state.nodes.findIndex((node) => node.id === center);
  const incoming = [];
  const outgoing = [];
  if (centerIndex >= 0) {
    for (const edge of edges) {
      if (edge.t === centerIndex) incoming.push(edge);
      if (edge.s === centerIndex) outgoing.push(edge);
    }
  }
  incoming.sort((a, b) => b.w - a.w);
  outgoing.sort((a, b) => b.w - a.w);

  return {
    layer: state.layer,
    sentiment: state.sentiment,
    minWeight: state.minWeight,
    center,
    nodeRows,
    edgeWeights,
    topEdges,
    egoIncoming: incoming.slice(0, 24),
    egoOutgoing: outgoing.slice(0, 24),
    edgeCount: edges.length,
    nodeCount: nodeRows.length,
  };
}

function setupCanvas(canvasElement) {
  const rect = canvasElement.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  canvasElement.width = Math.max(1, Math.floor(rect.width * dpr));
  canvasElement.height = Math.max(1, Math.floor(rect.height * dpr));
  const drawingContext = canvasElement.getContext("2d");
  drawingContext.setTransform(dpr, 0, 0, dpr, 0, 0);
  drawingContext.clearRect(0, 0, rect.width, rect.height);
  drawingContext.fillStyle = "#ffffff";
  drawingContext.fillRect(0, 0, rect.width, rect.height);
  return { ctx: drawingContext, width: rect.width, height: rect.height };
}

function drawNoData(ctx, width, height, message) {
  ctx.fillStyle = "#697386";
  ctx.font = "700 14px Inter, Segoe UI, sans-serif";
  ctx.textAlign = "center";
  ctx.fillText(message, width / 2, height / 2);
}

function makeBins(values, binCount = 42) {
  const clean = values.filter((value) => Number.isFinite(value) && value >= 0);
  if (!clean.length) return [];
  const max = clean.reduce((currentMax, value) => Math.max(currentMax, value), 0);
  if (max <= 0) return [{ start: 0, end: 1, count: clean.length }];
  const bins = Array.from({ length: binCount }, (_, index) => ({
    start: (max * index) / binCount,
    end: (max * (index + 1)) / binCount,
    count: 0,
  }));
  for (const value of clean) {
    const index = Math.min(binCount - 1, Math.floor((value / max) * binCount));
    bins[index].count += 1;
  }
  return bins;
}

function drawHistogramPanel(ctx, title, values, x, y, width, height, color) {
  const bins = makeBins(values);
  ctx.save();
  ctx.fillStyle = "#111827";
  ctx.font = "800 13px Inter, Segoe UI, sans-serif";
  ctx.textAlign = "center";
  ctx.fillText(title, x + width / 2, y + 16);

  const plotX = x + 42;
  const plotY = y + 34;
  const plotW = width - 52;
  const plotH = height - 70;
  ctx.strokeStyle = "#d8deea";
  ctx.strokeRect(plotX, plotY, plotW, plotH);

  if (!bins.length) {
    drawNoData(ctx, width, height, "sem dados");
    ctx.restore();
    return;
  }

  const maxLog = Math.max(...bins.map((bin) => Math.log10(bin.count + 1)));
  const barW = plotW / bins.length;
  ctx.fillStyle = color;
  for (const [index, bin] of bins.entries()) {
    const value = Math.log10(bin.count + 1);
    const barH = maxLog ? (value / maxLog) * plotH : 0;
    ctx.fillRect(plotX + index * barW, plotY + plotH - barH, Math.max(1, barW - 1), barH);
  }

  const maxValue = values.reduce((currentMax, value) => Math.max(currentMax, value || 0), 0);
  ctx.fillStyle = "#697386";
  ctx.font = "11px Inter, Segoe UI, sans-serif";
  ctx.textAlign = "left";
  ctx.fillText("0", plotX, plotY + plotH + 18);
  ctx.textAlign = "right";
  ctx.fillText(formatNumber(maxValue), plotX + plotW, plotY + plotH + 18);
  ctx.save();
  ctx.translate(x + 12, plotY + plotH / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.textAlign = "center";
  ctx.fillText("quantidade em escala log", 0, 0);
  ctx.restore();
  ctx.restore();
}

function drawDistributions(analysis) {
  const { ctx, width, height } = setupCanvas(els.distributionCanvas);
  const panelW = width / 3;
  drawHistogramPanel(
    ctx,
    "Forca de entrada",
    analysis.nodeRows.map((row) => row.inStrength),
    0,
    0,
    panelW,
    height,
    "#5b8def",
  );
  drawHistogramPanel(
    ctx,
    "Forca de saida",
    analysis.nodeRows.map((row) => row.outStrength),
    panelW,
    0,
    panelW,
    height,
    "#2a9d8f",
  );
  drawHistogramPanel(
    ctx,
    "Peso das arestas",
    analysis.edgeWeights,
    panelW * 2,
    0,
    panelW,
    height,
    "#e76f51",
  );
  els.distributionMeta.textContent = `${formatNumber(analysis.nodeCount)} vertices | ${formatNumber(analysis.edgeCount)} arestas`;
}

function drawEgo(analysis) {
  const { ctx, width, height } = setupCanvas(els.egoCanvas);
  if (!analysis.egoIncoming.length && !analysis.egoOutgoing.length) {
    drawNoData(ctx, width, height, `sem ego para ${analysis.center}`);
    return;
  }

  const center = { x: width / 2, y: height / 2 };
  const leftX = 92;
  const rightX = width - 92;
  const top = 42;
  const bottom = height - 28;
  const maxRows = Math.max(analysis.egoIncoming.length, analysis.egoOutgoing.length, 1);
  const rowY = (index) => top + (index * (bottom - top)) / Math.max(1, maxRows - 1);
  const maxWeight = [...analysis.egoIncoming, ...analysis.egoOutgoing].reduce(
    (currentMax, edge) => Math.max(currentMax, edge.w),
    1,
  );

  ctx.font = "800 12px Inter, Segoe UI, sans-serif";
  ctx.fillStyle = "#111827";
  ctx.textAlign = "center";
  ctx.fillText("Entram no centro", leftX, 20);
  ctx.fillText("Saem do centro", rightX, 20);

  function drawSide(edges, side) {
    edges.forEach((edge, index) => {
      const nodeIndex = side === "in" ? edge.s : edge.t;
      const node = state.nodes[nodeIndex];
      const x = side === "in" ? leftX : rightX;
      const y = rowY(index);
      const widthLine = 1 + 5 * Math.sqrt(edge.w / maxWeight);
      ctx.strokeStyle = edge.n > edge.p ? "rgba(220,53,88,0.34)" : "rgba(83,118,217,0.28)";
      ctx.lineWidth = widthLine;
      ctx.beginPath();
      if (side === "in") {
        ctx.moveTo(x + 34, y);
        ctx.quadraticCurveTo(width * 0.38, y, center.x - 18, center.y);
      } else {
        ctx.moveTo(center.x + 18, center.y);
        ctx.quadraticCurveTo(width * 0.62, y, x - 34, y);
      }
      ctx.stroke();
      ctx.fillStyle = node?.color || "#5376d9";
      ctx.strokeStyle = "#1f2937";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.arc(x, y, 13, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = "#111827";
      ctx.font = "11px Inter, Segoe UI, sans-serif";
      ctx.textAlign = side === "in" ? "right" : "left";
      ctx.fillText(node?.id || "?", side === "in" ? x - 18 : x + 18, y + 4);
    });
  }

  drawSide(analysis.egoIncoming, "in");
  drawSide(analysis.egoOutgoing, "out");
  ctx.fillStyle = "#111827";
  ctx.beginPath();
  ctx.arc(center.x, center.y, 19, 0, Math.PI * 2);
  ctx.fill();
  ctx.fillStyle = "#111827";
  ctx.font = "800 12px Inter, Segoe UI, sans-serif";
  ctx.textAlign = "center";
  ctx.fillText(analysis.center, center.x, center.y + 34);
  els.egoMeta.textContent = `${analysis.egoIncoming.length} entradas | ${analysis.egoOutgoing.length} saidas`;
}

function drawTopEdges(analysis) {
  const { ctx, width, height } = setupCanvas(els.topEdgesCanvas);
  const edges = analysis.topEdges;
  if (!edges.length) {
    drawNoData(ctx, width, height, "sem arestas filtradas");
    return;
  }

  const nodeIds = new Set();
  for (const edge of edges) {
    nodeIds.add(edge.s);
    nodeIds.add(edge.t);
  }
  const ids = [...nodeIds];
  const center = { x: width / 2, y: height / 2 };
  const radius = Math.max(80, Math.min(width, height) * 0.36);
  const positions = new Map();
  ids.forEach((nodeIndex, index) => {
    const angle = (Math.PI * 2 * index) / ids.length - Math.PI / 2;
    positions.set(nodeIndex, {
      x: center.x + radius * Math.cos(angle),
      y: center.y + radius * Math.sin(angle),
    });
  });

  const maxWeight = edges.reduce((currentMax, edge) => Math.max(currentMax, edge.w), 1);
  ctx.save();
  for (const edge of edges) {
    const a = positions.get(edge.s);
    const b = positions.get(edge.t);
    if (!a || !b) continue;
    ctx.strokeStyle = edge.n > edge.p ? "rgba(220,53,88,0.20)" : "rgba(83,118,217,0.18)";
    ctx.lineWidth = 0.5 + 4 * Math.sqrt(edge.w / maxWeight);
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
  }
  for (const nodeIndex of ids) {
    const node = state.nodes[nodeIndex];
    const position = positions.get(nodeIndex);
    ctx.fillStyle = node?.color || "#5376d9";
    ctx.strokeStyle = "#1f2937";
    ctx.lineWidth = 0.8;
    ctx.beginPath();
    ctx.arc(position.x, position.y, Math.max(3, Math.min(12, (node?.size || 4) * 0.7)), 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
  }
  const labelNodes = ids
    .map((nodeIndex) => state.nodes[nodeIndex])
    .filter(Boolean)
    .sort((a, b) => b.totalStrength - a.totalStrength)
    .slice(0, 14);
  ctx.fillStyle = "#111827";
  ctx.font = "800 11px Inter, Segoe UI, sans-serif";
  ctx.textAlign = "center";
  for (const node of labelNodes) {
    const position = positions.get(state.nodes.indexOf(node));
    if (position) ctx.fillText(node.id, position.x, position.y - 12);
  }
  ctx.restore();
  els.topEdgesMeta.textContent = `${formatNumber(edges.length)} arestas | ${formatNumber(ids.length)} vertices`;
}

async function runAnalysis() {
  if (!state.edges.length) {
    state.edges = await loadEdges(state.layer);
  }
  state.lastAnalysis = computeAnalysis();
  els.analysisTitle.textContent = `Camada ${state.layer} | sinal ${state.sentiment} | peso >= ${state.minWeight}`;
  drawDistributions(state.lastAnalysis);
  drawEgo(state.lastAnalysis);
  drawTopEdges(state.lastAnalysis);
}

function downloadText(filename, mimeType, text) {
  const blob = new Blob([text], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function exportAnalysisJson() {
  if (!state.lastAnalysis) runAnalysis();
  const analysis = state.lastAnalysis;
  const payload = {
    filters: {
      layer: analysis.layer,
      sentiment: analysis.sentiment,
      minWeight: analysis.minWeight,
      egoCenter: analysis.center,
      topEdges: state.topEdgesLimit,
    },
    summary: {
      nodeCount: analysis.nodeCount,
      edgeCount: analysis.edgeCount,
    },
    topNodesByStrength: [...analysis.nodeRows]
      .sort((a, b) => b.totalStrength - a.totalStrength)
      .slice(0, 30),
    topEdges: analysis.topEdges.slice(0, 50).map(edgeToRow),
    egoIncoming: analysis.egoIncoming.map(edgeToRow),
    egoOutgoing: analysis.egoOutgoing.map(edgeToRow),
  };
  downloadText("reddit_graph_analysis.json", "application/json", JSON.stringify(payload, null, 2));
}

function edgeToRow(edge) {
  return {
    source: state.nodes[edge.s]?.id,
    target: state.nodes[edge.t]?.id,
    weight: edge.w,
    positive: edge.p,
    negative: edge.n,
    sentimentBalance: edge.b,
  };
}

function exportAnalysisCsv() {
  if (!state.lastAnalysis) runAnalysis();
  const rows = state.lastAnalysis.topEdges.map(edgeToRow);
  const header = ["source", "target", "weight", "positive", "negative", "sentimentBalance"];
  const csv = [
    header.join(","),
    ...rows.map((row) =>
      header
        .map((key) => `"${String(row[key] ?? "").replaceAll('"', '""')}"`)
        .join(","),
    ),
  ].join("\n");
  downloadText("reddit_top_edges_filtered.csv", "text/csv", csv);
}

function setImportStatus(slotId, text, type = "") {
  const slot = compareSlots.find((item) => item.id === slotId);
  const status = slot ? els[slot.status] : null;
  if (!status) return;
  status.textContent = text;
  status.classList.toggle("is-ready", type === "ready");
  status.classList.toggle("is-error", type === "error");
}

function parseCsvGraph(text) {
  const lines = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line && !line.startsWith("#"));
  if (!lines.length) return { edges: [] };

  const first = lines[0];
  const delimiter = first.includes(";")
    ? ";"
    : first.includes("\t")
      ? "\t"
      : first.includes(",")
        ? ","
        : /\s+/;
  const splitLine = (line) => line.split(delimiter).map((part) => part.trim().replace(/^"|"$/g, ""));
  const firstParts = splitLine(first);
  const headerTokens = firstParts.map((part) => part.toLowerCase());
  const hasHeader = headerTokens.some((part) =>
    ["source", "target", "src", "dst", "from", "to", "origem", "destino"].includes(part),
  );
  const sourceIndex = hasHeader
    ? Math.max(0, headerTokens.findIndex((part) => ["source", "src", "from", "origem"].includes(part)))
    : 0;
  const targetIndex = hasHeader
    ? Math.max(1, headerTokens.findIndex((part) => ["target", "dst", "to", "destino"].includes(part)))
    : 1;
  const weightIndex = hasHeader
    ? headerTokens.findIndex((part) => ["weight", "peso", "w"].includes(part))
    : 2;
  const dataLines = hasHeader ? lines.slice(1) : lines;

  const edges = [];
  for (const line of dataLines) {
    const parts = splitLine(line);
    const source = parts[sourceIndex];
    const target = parts[targetIndex];
    if (!source || !target || source === target) continue;
    const weight = weightIndex >= 0 ? Number(parts[weightIndex]) || 1 : 1;
    edges.push({ source, target, weight });
  }
  return { edges };
}

function edgeEndpoint(value, nodes) {
  if (value && typeof value === "object") {
    return String(value.id ?? value.name ?? value.label ?? JSON.stringify(value));
  }
  if (Number.isInteger(value) && Array.isArray(nodes) && nodes[value]) {
    const node = nodes[value];
    return String(node.id ?? node.name ?? node.label ?? value);
  }
  return String(value);
}

function normalizeJsonEdges(payload) {
  const nodes = Array.isArray(payload?.nodes) ? payload.nodes : [];
  const rawEdges = Array.isArray(payload)
    ? payload
    : Array.isArray(payload?.edges)
      ? payload.edges
      : Array.isArray(payload?.links)
        ? payload.links
        : [];

  const edges = [];
  for (const item of rawEdges) {
    let source;
    let target;
    let weight = 1;
    if (Array.isArray(item)) {
      [source, target, weight = 1] = item;
    } else if (item && typeof item === "object") {
      source = item.source ?? item.src ?? item.from ?? item.s;
      target = item.target ?? item.dst ?? item.to ?? item.t;
      weight = item.weight ?? item.peso ?? item.w ?? 1;
    }
    if (source === undefined || target === undefined || source === target) continue;
    edges.push({
      source: edgeEndpoint(source, nodes),
      target: edgeEndpoint(target, nodes),
      weight: Number(weight) || 1,
    });
  }
  return { edges };
}

function parseGraphText(text, filename = "") {
  const trimmed = text.trim();
  if (!trimmed) return { edges: [] };
  if (filename.toLowerCase().endsWith(".json") || /^[\[{]/.test(trimmed)) {
    return normalizeJsonEdges(JSON.parse(trimmed));
  }
  return parseCsvGraph(trimmed);
}

function buildUndirectedAdjacency(edges) {
  const adjacency = new Map();
  const pairSet = new Set();
  for (const edge of edges) {
    const source = String(edge.source);
    const target = String(edge.target);
    if (!source || !target || source === target) continue;
    const a = source < target ? source : target;
    const b = source < target ? target : source;
    const key = `${a}\u0000${b}`;
    if (pairSet.has(key)) continue;
    pairSet.add(key);
    if (!adjacency.has(source)) adjacency.set(source, new Set());
    if (!adjacency.has(target)) adjacency.set(target, new Set());
    adjacency.get(source).add(target);
    adjacency.get(target).add(source);
  }
  return { adjacency, edgeCount: pairSet.size };
}

function sampleList(items, limit) {
  if (items.length <= limit) return items;
  const sampled = [];
  const step = items.length / limit;
  for (let index = 0; index < limit; index += 1) {
    sampled.push(items[Math.min(items.length - 1, Math.floor(index * step))]);
  }
  return sampled;
}

function largestComponent(adjacency) {
  const visited = new Set();
  let largest = [];
  for (const start of adjacency.keys()) {
    if (visited.has(start)) continue;
    const component = [];
    const queue = [start];
    visited.add(start);
    for (let head = 0; head < queue.length; head += 1) {
      const node = queue[head];
      component.push(node);
      for (const neighbor of adjacency.get(node) || []) {
        if (!visited.has(neighbor)) {
          visited.add(neighbor);
          queue.push(neighbor);
        }
      }
    }
    if (component.length > largest.length) largest = component;
  }
  return largest;
}

function bfsDistances(start, adjacency, allowed) {
  const distances = new Map([[start, 0]]);
  const queue = [start];
  for (let head = 0; head < queue.length; head += 1) {
    const node = queue[head];
    const nextDistance = distances.get(node) + 1;
    for (const neighbor of adjacency.get(node) || []) {
      if (allowed && !allowed.has(neighbor)) continue;
      if (!distances.has(neighbor)) {
        distances.set(neighbor, nextDistance);
        queue.push(neighbor);
      }
    }
  }
  return distances;
}

function estimateAveragePathLength(adjacency, component) {
  if (component.length < 2) return 0;
  const allowed = new Set(component);
  const seeds = sampleList(component, Math.min(48, component.length));
  let total = 0;
  let count = 0;
  for (const seed of seeds) {
    const distances = bfsDistances(seed, adjacency, allowed);
    for (const [node, distance] of distances) {
      if (node === seed) continue;
      total += distance;
      count += 1;
    }
  }
  return count ? total / count : null;
}

function estimateClustering(adjacency, component) {
  const candidates = sampleList(
    component.filter((node) => (adjacency.get(node)?.size || 0) >= 2),
    900,
  );
  if (!candidates.length) return 0;
  let total = 0;
  let evaluated = 0;

  for (const node of candidates) {
    const neighbors = [...(adjacency.get(node) || [])];
    const degree = neighbors.length;
    const possible = (degree * (degree - 1)) / 2;
    if (!possible) continue;

    let coefficient = 0;
    if (degree <= 180) {
      let links = 0;
      for (let i = 0; i < degree; i += 1) {
        const neighborSet = adjacency.get(neighbors[i]);
        for (let j = i + 1; j < degree; j += 1) {
          if (neighborSet?.has(neighbors[j])) links += 1;
        }
      }
      coefficient = links / possible;
    } else {
      let links = 0;
      const pairSamples = 800;
      for (let index = 0; index < pairSamples; index += 1) {
        const a = Math.floor(normalizedHash(`${node}:${index}`, "cluster-a") * degree);
        let b = Math.floor(normalizedHash(`${node}:${index}`, "cluster-b") * degree);
        if (a === b) b = (b + 1) % degree;
        if (adjacency.get(neighbors[a])?.has(neighbors[b])) links += 1;
      }
      coefficient = links / pairSamples;
    }
    total += coefficient;
    evaluated += 1;
  }
  return evaluated ? total / evaluated : 0;
}

function degreeGini(degrees) {
  const sorted = [...degrees].sort((a, b) => a - b);
  const sum = sorted.reduce((acc, value) => acc + value, 0);
  if (!sum) return 0;
  let weighted = 0;
  for (let index = 0; index < sorted.length; index += 1) {
    weighted += (index + 1) * sorted[index];
  }
  return (2 * weighted) / (sorted.length * sum) - (sorted.length + 1) / sorted.length;
}

function estimatePowerLawSlope(degrees) {
  const counts = new Map();
  for (const degree of degrees) {
    if (degree >= 2) counts.set(degree, (counts.get(degree) || 0) + 1);
  }
  const points = [...counts.entries()]
    .filter(([, count]) => count >= 2)
    .map(([degree, count]) => [Math.log(degree), Math.log(count)]);
  if (points.length < 4) return null;
  const meanX = points.reduce((sum, point) => sum + point[0], 0) / points.length;
  const meanY = points.reduce((sum, point) => sum + point[1], 0) / points.length;
  let numerator = 0;
  let denominator = 0;
  for (const [x, y] of points) {
    numerator += (x - meanX) * (y - meanY);
    denominator += (x - meanX) ** 2;
  }
  return denominator ? numerator / denominator : null;
}

function classifyNetwork(metrics) {
  if (metrics.nodeCount < 10 || metrics.edgeCount < 5) {
    return {
      key: "mixed",
      label: "dados insuficientes",
      reason: "A rede e pequena demais para uma inferencia confiavel.",
    };
  }

  const clusteringRatio = metrics.density > 0 ? metrics.clustering / metrics.density : 0;
  const pathStretch = metrics.randomPathEstimate
    ? metrics.avgPathLength / metrics.randomPathEstimate
    : Infinity;
  const hubRatio = metrics.avgDegree ? metrics.maxDegree / metrics.avgDegree : 0;
  const slopeLooksScaleFree = metrics.powerLawSlope !== null
    && metrics.powerLawSlope <= -1.4
    && metrics.powerLawSlope >= -3.8;
  const scaleScore = [
    metrics.degreeCv >= 1.8,
    hubRatio >= 8,
    metrics.topOneDegreeShare >= 0.025,
    slopeLooksScaleFree,
  ].filter(Boolean).length;
  const smallWorldLike = clusteringRatio >= 4 && pathStretch <= 2.5 && metrics.avgPathLength !== null;
  const randomLike = metrics.degreeCv < 1.25 && clusteringRatio >= 0.35 && clusteringRatio <= 3.2 && pathStretch <= 1.8;

  if (scaleScore >= 2 && smallWorldLike) {
    return {
      key: "mixed",
      label: "sem escala + mundo pequeno",
      reason: "Ha hubs fortes e tambem agrupamento alto com caminhos curtos.",
    };
  }
  if (scaleScore >= 2) {
    return {
      key: "scale-free",
      label: "sem escala",
      reason: "A distribuicao de grau e muito desigual e concentrada em hubs.",
    };
  }
  if (smallWorldLike) {
    return {
      key: "small-world",
      label: "mundo pequeno",
      reason: "O agrupamento supera a densidade e a distancia media segue curta.",
    };
  }
  if (randomLike) {
    return {
      key: "random",
      label: "aleatoria",
      reason: "O grau e homogeneo e o agrupamento fica proximo da densidade.",
    };
  }
  return {
    key: "mixed",
    label: "hibrida/indefinida",
    reason: "As metricas nao se encaixam claramente nos tres modelos basicos.",
  };
}

function computeNetworkMetrics(edges) {
  const { adjacency, edgeCount } = buildUndirectedAdjacency(edges);
  const nodes = [...adjacency.keys()];
  const nodeCount = nodes.length;
  const degrees = nodes.map((node) => adjacency.get(node).size);
  const degreeSum = degrees.reduce((sum, degree) => sum + degree, 0);
  const avgDegree = nodeCount ? degreeSum / nodeCount : 0;
  const density = nodeCount > 1 ? (2 * edgeCount) / (nodeCount * (nodeCount - 1)) : 0;
  const maxDegree = degrees.reduce((max, degree) => Math.max(max, degree), 0);
  const variance = nodeCount
    ? degrees.reduce((sum, degree) => sum + (degree - avgDegree) ** 2, 0) / nodeCount
    : 0;
  const degreeStd = Math.sqrt(variance);
  const degreeCv = avgDegree ? degreeStd / avgDegree : 0;
  const component = largestComponent(adjacency);
  const componentShare = nodeCount ? component.length / nodeCount : 0;
  const avgPathLength = estimateAveragePathLength(adjacency, component);
  const clustering = estimateClustering(adjacency, component);
  const randomPathEstimate = avgDegree > 1 && nodeCount > 2
    ? Math.log(nodeCount) / Math.log(avgDegree)
    : null;
  const sortedDegrees = [...degrees].sort((a, b) => b - a);
  const topOneDegreeShare = degreeSum ? (sortedDegrees[0] || 0) / degreeSum : 0;
  const topFiveDegreeShare = degreeSum
    ? sortedDegrees.slice(0, 5).reduce((sum, degree) => sum + degree, 0) / degreeSum
    : 0;
  const metrics = {
    nodeCount,
    edgeCount,
    avgDegree,
    density,
    maxDegree,
    degreeCv,
    degreeGini: degreeGini(degrees),
    componentShare,
    avgPathLength,
    clustering,
    randomPathEstimate,
    topOneDegreeShare,
    topFiveDegreeShare,
    powerLawSlope: estimatePowerLawSlope(degrees),
  };
  metrics.classification = classifyNetwork(metrics);
  return metrics;
}

async function importCompareFile(slotId, file) {
  if (!file) return;
  setImportStatus(slotId, "Lendo arquivo...", "");
  try {
    const text = await file.text();
    const graph = parseGraphText(text, file.name);
    if (!graph.edges.length) throw new Error("Nenhuma aresta valida encontrada.");
    const slot = compareSlots.find((item) => item.id === slotId);
    state.compareDatasets[slotId] = {
      id: slotId,
      name: slot.name,
      expected: slot.expected,
      fileName: file.name,
      edges: graph.edges,
      metrics: null,
    };
    setImportStatus(slotId, `${file.name} - ${formatNumber(graph.edges.length)} arestas`, "ready");
    renderCompareResults();
  } catch (error) {
    state.compareDatasets[slotId] = null;
    setImportStatus(slotId, `Erro: ${error.message}`, "error");
  }
}

function projectCompareEdgesForScope() {
  const scope = els.compareScopeSelect.value;
  const filtered = getFilteredEdges();

  if (scope === "community") {
    const communityId = state.selectedCommunity ?? state.selectedNode?.community;
    if (communityId === null || communityId === undefined) {
      throw new Error("Selecione uma comunidade no mapa ou na lista antes de comparar.");
    }
    const community = state.communities.find((item) => item.id === communityId);
    const edges = filtered
      .filter((edge) => state.nodes[edge.s]?.community === communityId && state.nodes[edge.t]?.community === communityId)
      .map((edge) => ({
        source: state.nodes[edge.s]?.id ?? String(edge.s),
        target: state.nodes[edge.t]?.id ?? String(edge.t),
        weight: edge.w,
      }));
    return {
      edges,
      scopeLabel: `comunidade ${community?.label ?? communityId}`,
    };
  }

  if (scope === "ego") {
    const query = els.searchInput.value.trim().toLowerCase();
    const center = query && state.nodeById.has(query)
      ? state.nodeById.get(query)
      : state.selectedNode;
    if (!center) {
      throw new Error("Busque ou selecione um subreddit antes de comparar a rede ego.");
    }
    const centerIndex = state.nodes.indexOf(center);
    const nodeSet = new Set([centerIndex]);
    for (const edge of filtered) {
      if (edge.s === centerIndex) nodeSet.add(edge.t);
      if (edge.t === centerIndex) nodeSet.add(edge.s);
    }
    const edges = filtered
      .filter((edge) => nodeSet.has(edge.s) && nodeSet.has(edge.t))
      .map((edge) => ({
        source: state.nodes[edge.s]?.id ?? String(edge.s),
        target: state.nodes[edge.t]?.id ?? String(edge.t),
        weight: edge.w,
      }));
    return {
      edges,
      scopeLabel: `ego de ${center.id}`,
    };
  }

  return {
    edges: filtered.map((edge) => ({
      source: state.nodes[edge.s]?.id ?? String(edge.s),
      target: state.nodes[edge.t]?.id ?? String(edge.t),
      weight: edge.w,
    })),
    scopeLabel: "rede completa",
  };
}

async function loadProjectCompareDataset() {
  setImportStatus("project", "Carregando camada atual...", "");
  if (!state.edges.length) {
    state.edges = await loadEdges(state.layer);
  }
  const { edges, scopeLabel } = projectCompareEdgesForScope();
  if (!edges.length) {
    throw new Error("O escopo escolhido nao possui arestas com os filtros atuais.");
  }
  state.compareDatasets.project = {
    id: "project",
    name: "Projeto Reddit",
    expected: "projeto",
    fileName: `${scopeLabel}, camada ${state.layer}`,
    edges,
    metrics: null,
  };
  setImportStatus("project", `${scopeLabel} - ${formatNumber(edges.length)} arestas`, "ready");
}

async function loadBuiltInComparisonDatasets() {
  try {
    const response = await fetch(`./public/comparison-datasets.json?v=${ASSET_VERSION}`);
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload = await response.json();
    state.builtInComparisonDatasets = payload.datasets || [];
    els.builtInDatasetSelect.innerHTML = state.builtInComparisonDatasets
      .map((dataset) => `<option value="${dataset.id}">${dataset.name} - ${dataset.model}</option>`)
      .join("");
    els.builtInDatasetStatus.textContent = `${formatNumber(state.builtInComparisonDatasets.length)} exemplos disponiveis`;
    els.builtInDatasetStatus.classList.add("is-ready");
  } catch (error) {
    els.builtInDatasetSelect.innerHTML = `<option value="">Sem exemplos</option>`;
    els.builtInDatasetStatus.textContent = `Erro ao carregar exemplos: ${error.message}`;
    els.builtInDatasetStatus.classList.add("is-error");
  }
}

function addBuiltInDataset() {
  const datasetId = els.builtInDatasetSelect.value;
  const dataset = state.builtInComparisonDatasets.find((item) => item.id === datasetId);
  if (!dataset) return;
  const normalized = {
    id: `builtIn:${dataset.id}`,
    name: dataset.name,
    expected: dataset.model,
    fileName: dataset.source,
    edges: dataset.edges,
    metrics: null,
  };
  state.extraCompareDatasets = state.extraCompareDatasets.filter((item) => item.id !== normalized.id);
  state.extraCompareDatasets.push(normalized);
  els.builtInDatasetStatus.textContent = `${dataset.name} adicionado`;
  els.builtInDatasetStatus.classList.add("is-ready");
  renderCompareResults();
}

function formatMetric(value, fallback = "-") {
  if (value === null || value === undefined || Number.isNaN(value)) return fallback;
  return decimal.format(value);
}

function classChip(classification) {
  return `<span class="class-chip ${classification.key}">${classification.label}</span>`;
}

function renderCompareResults() {
  const datasets = [
    ...compareSlots.map((slot) => state.compareDatasets[slot.id]).filter(Boolean),
    ...state.extraCompareDatasets,
  ];
  if (!datasets.length) {
    els.compareMeta.textContent = "Aguardando calculo";
    els.compareSummary.textContent = "Importe as redes de referencia e clique em Comparar.";
    els.compareTableBody.innerHTML = `<tr><td colspan="8">Sem resultados ainda.</td></tr>`;
    return;
  }

  const withMetrics = datasets.filter((dataset) => dataset.metrics);
  els.compareMeta.textContent = withMetrics.length
    ? `${formatNumber(withMetrics.length)} redes calculadas`
    : `${formatNumber(datasets.length)} redes importadas`;

  const project = state.compareDatasets.project;
  if (project?.metrics) {
    els.compareSummary.innerHTML = `
      <strong>Projeto classificado como ${project.metrics.classification.label}</strong>
      ${project.metrics.classification.reason}
      <div class="metric-line"><span>camada/filtro</span><strong>${state.layer}, sinal ${state.sentiment}, peso >= ${state.minWeight}</strong></div>
      <div class="metric-line"><span>componente principal</span><strong>${pct.format(project.metrics.componentShare)}</strong></div>
    `;
  } else {
    els.compareSummary.textContent = "Clique em Comparar para calcular as metricas aproximadas do projeto e das redes importadas.";
  }

  els.compareTableBody.innerHTML = datasets
    .map((dataset) => {
      if (!dataset.metrics) {
        return `
          <tr>
            <td><strong>${dataset.name}</strong><br /><small>${dataset.fileName}</small></td>
            <td colspan="7">Importado. Calculo pendente.</td>
          </tr>
        `;
      }
      const metrics = dataset.metrics;
      return `
        <tr>
          <td><strong>${dataset.name}</strong><br /><small>${dataset.fileName}</small></td>
          <td>${classChip(metrics.classification)}<br /><small>${metrics.classification.reason}</small></td>
          <td>${compactNumber.format(metrics.nodeCount)}</td>
          <td>${compactNumber.format(metrics.edgeCount)}</td>
          <td>${formatMetric(metrics.avgPathLength)}</td>
          <td>${formatMetric(metrics.clustering)}</td>
          <td>${formatMetric(metrics.avgDegree)}</td>
          <td>
            CV ${formatMetric(metrics.degreeCv)}<br />
            hub/max ${formatMetric(metrics.avgDegree ? metrics.maxDegree / metrics.avgDegree : 0)}
          </td>
        </tr>
      `;
    })
    .join("");
}

async function runCompare() {
  els.compareMeta.textContent = "Calculando metricas...";
  if (!state.compareDatasets.project) {
    try {
      await loadProjectCompareDataset();
    } catch (error) {
      setImportStatus("project", `Erro: ${error.message}`, "error");
    }
  }
  const datasets = [
    ...compareSlots.map((slot) => state.compareDatasets[slot.id]).filter(Boolean),
    ...state.extraCompareDatasets,
  ];
  for (const dataset of datasets) {
    if (!dataset.metrics) {
      setImportStatus(dataset.id, `Calculando ${dataset.name}...`, "");
      await new Promise((resolve) => setTimeout(resolve, 0));
      dataset.metrics = computeNetworkMetrics(dataset.edges);
      setImportStatus(dataset.id, `${formatNumber(dataset.metrics.nodeCount)} vertices analisados`, "ready");
    }
  }
  state.compareResults = datasets;
  renderCompareResults();
}

function clearCompare() {
  state.compareDatasets = {
    project: null,
    random: null,
    smallWorld: null,
    scaleFree: null,
  };
  state.extraCompareDatasets = [];
  state.compareResults = [];
  for (const slot of compareSlots) {
    if (slot.input && els[slot.input]) els[slot.input].value = "";
    setImportStatus(slot.id, slot.id === "project" ? "Pronto para calcular" : "Nenhum arquivo");
  }
  renderCompareResults();
}

function renderCommunities() {
  els.communityList.innerHTML = "";
  for (const community of state.communities.slice(0, 12)) {
    const item = document.createElement("button");
    item.className = "community-item";
    item.type = "button";
    item.innerHTML = `
      <span class="community-swatch" style="background:${community.color}"></span>
      <span>
        <span class="community-name">${community.label}</span>
        <span class="community-top">${community.topNodes}</span>
      </span>
      <span class="community-count">${formatNumber(community.nodeCount)}</span>
    `;
    item.addEventListener("click", () => {
      state.selectedCommunity = state.selectedCommunity === community.id ? null : community.id;
      state.selectedNode = null;
      els.selectionPanel.innerHTML = `
        <strong>${community.label}</strong>
        <div class="metric-line"><span>vertices</span><strong>${formatNumber(community.nodeCount)}</strong></div>
        <div class="metric-line"><span>peso interno</span><strong>${formatNumber(community.internalWeight)}</strong></div>
        <div class="metric-line"><span>top subreddits</span><strong>${community.topNodes}</strong></div>
      `;
      draw();
    });
    els.communityList.appendChild(item);
  }
}

function searchNode() {
  const query = els.searchInput.value.trim().toLowerCase();
  if (!query) return;
  const node = state.nodeById.get(query);
  if (!node) {
    els.selectionPanel.textContent = `Subreddit "${query}" nao encontrado.`;
    return;
  }
  setSelectedNode(node);
  const p = worldToScreen(getNodeX(node), getNodeY(node));
  state.transform.x += state.width / 2 - p.x;
  state.transform.y += state.height / 2 - p.y;
  state.transform.scale = Math.max(state.transform.scale, 2.2);
  draw();
}

function attachEvents() {
  window.addEventListener("resize", resizeCanvas);
  canvas.addEventListener("wheel", (event) => {
    event.preventDefault();
    zoomAt(event.offsetX, event.offsetY, event.deltaY);
  }, { passive: false });

  canvas.addEventListener("pointerdown", (event) => {
    state.dragging = true;
    state.moved = false;
    state.lastPointer = { x: event.clientX, y: event.clientY };
    canvas.setPointerCapture(event.pointerId);
  });

  canvas.addEventListener("pointermove", (event) => {
    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    if (state.dragging) {
      const dx = event.clientX - state.lastPointer.x;
      const dy = event.clientY - state.lastPointer.y;
      if (Math.abs(dx) + Math.abs(dy) > 2) state.moved = true;
      state.transform.x += dx;
      state.transform.y += dy;
      state.lastPointer = { x: event.clientX, y: event.clientY };
      draw();
      return;
    }
    state.hoverNode = nearestNode(x, y);
    showTooltip(state.hoverNode, x, y);
    draw();
  });

  canvas.addEventListener("pointerup", (event) => {
    state.dragging = false;
    canvas.releasePointerCapture(event.pointerId);
    if (!state.moved && state.hoverNode) {
      setSelectedNode(state.hoverNode);
    }
    draw();
  });

  canvas.addEventListener("pointerleave", () => {
    state.hoverNode = null;
    tooltip.hidden = true;
    if (!state.dragging) draw();
  });

  els.layerSelect.addEventListener("change", updateLayer);
  els.layoutModeSelect.addEventListener("change", async () => {
    state.layoutMode = els.layoutModeSelect.value;
    state.selectedCommunity = null;
    state.selectedNode = null;
    await refreshInfluenceView({ refit: true });
  });
  els.influenceSelect.addEventListener("change", async () => {
    state.influenceMode = els.influenceSelect.value;
    await refreshInfluenceView();
  });
  els.sentimentSelect.addEventListener("change", () => {
    state.sentiment = els.sentimentSelect.value;
    state.influenceComputedFor = "";
    computeInfluenceMetrics();
    invalidateProjectCompare();
    if (state.mode === "analysis") runAnalysis();
    draw();
  });
  els.weightInput.addEventListener("input", () => {
    state.minWeight = Number(els.weightInput.value);
    els.weightOutput.textContent = state.minWeight;
    state.influenceComputedFor = "";
    computeInfluenceMetrics();
    invalidateProjectCompare();
    if (state.mode === "analysis") runAnalysis();
    draw();
  });
  els.topEdgesInput.addEventListener("input", () => {
    state.topEdgesLimit = Number(els.topEdgesInput.value);
    els.topEdgesOutput.textContent = state.topEdgesLimit;
    if (state.mode === "analysis") runAnalysis();
  });
  els.edgesToggle.addEventListener("change", async () => {
    state.showEdges = els.edgesToggle.checked;
    if (state.showEdges && state.edges.length === 0) {
      state.edges = await loadEdges(state.layer);
      state.influenceComputedFor = "";
      computeInfluenceMetrics();
    }
    draw();
  });
  els.labelsToggle.addEventListener("change", () => {
    state.showLabels = els.labelsToggle.checked;
    draw();
  });
  els.searchButton.addEventListener("click", searchNode);
  els.searchInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") searchNode();
  });
  els.fitButton.addEventListener("click", () => {
    state.selectedCommunity = null;
    state.selectedNode = null;
    fitToCurrentLayout();
  });
  els.runAnalysisButton.addEventListener("click", () => setMode("analysis"));
  els.mapModeButton.addEventListener("click", () => setMode("map"));
  els.analysisModeButton.addEventListener("click", () => setMode("analysis"));
  els.compareModeButton.addEventListener("click", () => setMode("compare"));
  els.exportJsonButton.addEventListener("click", exportAnalysisJson);
  els.exportCsvButton.addEventListener("click", exportAnalysisCsv);
  els.runCompareButton.addEventListener("click", runCompare);
  els.clearCompareButton.addEventListener("click", clearCompare);
  els.loadProjectCompareButton.addEventListener("click", async () => {
    try {
      await loadProjectCompareDataset();
      renderCompareResults();
    } catch (error) {
      setImportStatus("project", `Erro: ${error.message}`, "error");
    }
  });
  els.compareScopeSelect.addEventListener("change", invalidateProjectCompare);
  els.loadBuiltInDatasetButton.addEventListener("click", addBuiltInDataset);
  for (const slot of compareSlots) {
    if (!slot.input || !els[slot.input]) continue;
    els[slot.input].addEventListener("change", (event) => {
      importCompareFile(slot.id, event.target.files?.[0]);
    });
  }
}

async function init() {
  attachEvents();
  resizeCanvas();
  const response = await fetch(`./public/graph-core.json?v=${ASSET_VERSION}`);
  if (!response.ok) throw new Error(`Falha ao carregar graph-core.json: ${response.status}`);
  state.data = await response.json();
  state.nodes = state.data.nodes;
  state.communities = state.data.communities;
  state.nodeById = new Map(state.nodes.map((node) => [node.id, node]));
  prepareScatterLayout();
  resetInfluenceMetrics();
  updateStats();
  updateInfluenceLegend();
  renderCommunities();
  loadBuiltInComparisonDatasets();
  loading.hidden = true;
  loading.classList.add("is-hidden");
  fitToGraph();
}

init().catch((error) => {
  loading.innerHTML = `<strong>Erro ao carregar</strong><span>${error.message}</span>`;
  console.error(error);
});

window.redditGraphApp = {
  setMode,
  runAnalysis,
  getState: () => ({
    mode: state.mode,
    layer: state.layer,
    layoutMode: state.layoutMode,
    influenceMode: state.influenceMode,
    sentiment: state.sentiment,
    minWeight: state.minWeight,
    topEdgesLimit: state.topEdgesLimit,
    nodes: state.nodes.length,
    edges: state.edges.length,
    hasAnalysis: Boolean(state.lastAnalysis),
    compareResults: state.compareResults.length,
  }),
};
