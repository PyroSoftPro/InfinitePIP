/* global InfinitePIP */

const el = (id) => document.getElementById(id);

const tabScreens = el("tabScreens");
const tabWindows = el("tabWindows");
const tabRegions = el("tabRegions");
const tabActive = el("tabActive");
const panelSources = el("panelSources");
const panelRegions = el("panelRegions");
const panelActive = el("panelActive");

const panelTitle = el("panelTitle");
const panelHelp = el("panelHelp");
const grid = el("sourcesGrid");
const emptyState = el("emptyState");
const activePipsList = el("activePipsList");
const activePipsEmpty = el("activePipsEmpty");

const refreshBtn = el("refreshBtn");
const closeAllBtn = el("closeAllBtn");
const closeAllBtn2 = el("closeAllBtn2");

const regionPreviewBtn = el("regionPreviewBtn");
const regionCreateBtn = el("regionCreateBtn");
const regionScreenSelect = el("regionScreenSelect");
const regionX = el("regionX");
const regionY = el("regionY");
const regionW = el("regionW");
const regionH = el("regionH");
const regionInfo = el("regionInfo");
const regionPreviewWrap = el("regionPreviewWrap");
const regionPreviewVideo = el("regionPreviewVideo");
const regionPreviewCanvas = el("regionPreviewCanvas");
const regionPreviewCtx = regionPreviewCanvas.getContext("2d");
const regionPreviewZoom = el("regionPreviewZoom");
const regionPreviewReset = el("regionPreviewReset");
const regionPreviewStatus = el("regionPreviewStatus");

const statusDot = el("statusDot");
const statusText = el("statusText");
const pipCount = el("pipCount");

let currentTab = "screens"; // screens | windows | regions | active

let regionScreens = [];
let regionPreviewInFlight = false;
let regionPreviewStream = null;
let regionPreviewRaf = 0;
let regionPreviewZoomValue = Number(regionPreviewZoom.value || 1);
let regionPreviewPanX = 0; // content pan (matches PiP)
let regionPreviewPanY = 0; // content pan (matches PiP)
let regionPreviewDragging = false;
let regionPreviewDragStart = null; // {x,y,cropX,cropY,panX,panY}

function setTab(tab) {
  currentTab = tab;

  tabScreens.classList.toggle("active", tab === "screens");
  tabWindows.classList.toggle("active", tab === "windows");
  tabRegions.classList.toggle("active", tab === "regions");
  tabActive.classList.toggle("active", tab === "active");

  panelSources.classList.toggle("hidden", tab === "active" || tab === "regions");
  panelRegions.classList.toggle("hidden", tab !== "regions");
  panelActive.classList.toggle("hidden", tab !== "active");

  if (tab === "screens") {
    panelTitle.textContent = "Available Screens";
    panelHelp.textContent = "Create picture-in-picture windows from any connected display.";
    loadSources();
    stopRegionPreview();
  } else if (tab === "windows") {
    panelTitle.textContent = "Application Windows";
    panelHelp.textContent = "Capture and display content from any application window.";
    loadSources();
    stopRegionPreview();
  } else if (tab === "regions") {
    ensureRegionScreens().then(() => {
      // Auto-run preview when the user enters the Regions page.
      startRegionPreview();
    });
  } else if (tab === "active") {
    stopRegionPreview();
    refreshActivePips();
  }
}

function sourceTypesForTab() {
  if (currentTab === "windows") return ["window"];
  return ["screen"];
}

function renderSources(sources) {
  grid.innerHTML = "";
  emptyState.classList.toggle("hidden", sources.length > 0);

  for (const s of sources) {
    const card = document.createElement("div");
    card.className = "card";
    card.setAttribute("role", "button");
    card.setAttribute("tabindex", "0");

    const thumb = document.createElement("div");
    thumb.className = "thumb";
    if (s.thumbnailDataUrl) {
      const img = document.createElement("img");
      img.src = s.thumbnailDataUrl;
      img.alt = s.name;
      thumb.appendChild(img);
    } else {
      thumb.textContent = "No preview";
    }

    const meta = document.createElement("div");
    meta.className = "meta";

    const metaTop = document.createElement("div");
    metaTop.className = "metaTop";

    const icon = document.createElement("div");
    icon.className = "appIcon";
    if (s.appIconDataUrl) {
      const ic = document.createElement("img");
      ic.src = s.appIconDataUrl;
      ic.alt = "";
      icon.appendChild(ic);
    } else {
      icon.textContent = "•";
    }

    const name = document.createElement("div");
    name.style.minWidth = "0";
    name.innerHTML = `<div class="name">${escapeHtml(s.name)}</div><div class="sub">${escapeHtml(
      s.id
    )}</div>`;

    metaTop.appendChild(icon);
    metaTop.appendChild(name);

    const actions = document.createElement("div");
    actions.style.display = "flex";
    actions.style.gap = "10px";

    const btn = document.createElement("button");
    btn.className = "btn primary";
    btn.textContent = "Create PiP";
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      openPip(s);
    });

    actions.appendChild(btn);

    meta.appendChild(metaTop);
    meta.appendChild(actions);

    card.appendChild(thumb);
    card.appendChild(meta);

    card.addEventListener("click", () => openPip(s));
    card.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") openPip(s);
    });

    grid.appendChild(card);
  }
}

async function loadSources() {
  try {
    refreshBtn.disabled = true;
    grid.innerHTML = "";
    emptyState.classList.add("hidden");

    const sources = await InfinitePIP.getSources({
      types: sourceTypesForTab(),
      thumbnailSize: { width: 420, height: 260 }
    });

    renderSources(sources);
  } catch (err) {
    console.error(err);
    emptyState.classList.remove("hidden");
    const diag = await Promise.resolve(InfinitePIP?.diagnostics?.()).catch(() => null);
    const diagText = diag ? `\n\nDiagnostics: ${JSON.stringify(diag)}` : "";
    emptyState.textContent = `Failed to enumerate sources.\n\n${String(
      err?.message || err
    )}${diagText}`;
  } finally {
    refreshBtn.disabled = false;
  }
}

async function openPip(source) {
  try {
    await InfinitePIP.openPip({ sourceId: source.id, sourceName: source.name });
  } catch (err) {
    console.error(err);
    alert(String(err?.message || err));
  }
}

function updateRegionInfo() {
  const x = Number(regionX.value || 0);
  const y = Number(regionY.value || 0);
  const w = Number(regionW.value || 0);
  const h = Number(regionH.value || 0);
  regionInfo.textContent = `Region: ${w}×${h} at (${x}, ${y})`;
}

function getRegionCrop() {
  const x = Math.max(0, Math.floor(Number(regionX.value || 0)));
  const y = Math.max(0, Math.floor(Number(regionY.value || 0)));
  const w = Math.max(1, Math.floor(Number(regionW.value || 1)));
  const h = Math.max(1, Math.floor(Number(regionH.value || 1)));
  return { x, y, w, h };
}

function clamp(n, min, max) {
  return Math.max(min, Math.min(max, n));
}

function applyRegionPreviewLayoutFromInputs() {
  const crop = getRegionCrop();
  // Make the preview box match the intended output aspect ratio.
  regionPreviewWrap.style.aspectRatio = `${crop.w} / ${crop.h}`;
}

function selectedRegionScreen() {
  const id = regionScreenSelect.value;
  return regionScreens.find((s) => s.id === id) || regionScreens[0] || null;
}

async function ensureRegionScreens() {
  try {
    regionPreviewStatus.textContent = "Loading screens…";
    regionScreenSelect.innerHTML = "";
    regionScreens = await InfinitePIP.getSources({
      types: ["screen"],
      thumbnailSize: { width: 320, height: 200 }
    });

    for (const s of regionScreens) {
      const opt = document.createElement("option");
      opt.value = s.id;
      opt.textContent = s.name;
      regionScreenSelect.appendChild(opt);
    }

    if (regionScreens.length === 0) {
      regionPreviewStatus.textContent = "No screens found.";
    } else {
      regionPreviewStatus.textContent = "Click “Update Preview”.";
    }
  } catch (err) {
    console.error(err);
    regionPreviewStatus.textContent =
      "Failed to enumerate screens. Check permissions (screen recording) and try again.";
  }
}

function resizeRegionPreviewCanvasToDisplay() {
  const dpr = window.devicePixelRatio || 1;
  const rect = regionPreviewCanvas.getBoundingClientRect();
  const w = Math.max(1, Math.floor(rect.width * dpr));
  const h = Math.max(1, Math.floor(rect.height * dpr));
  if (regionPreviewCanvas.width !== w || regionPreviewCanvas.height !== h) {
    regionPreviewCanvas.width = w;
    regionPreviewCanvas.height = h;
  }
}

function drawRegionPreview() {
  regionPreviewRaf = requestAnimationFrame(drawRegionPreview);
  if (!regionPreviewVideo.videoWidth || !regionPreviewVideo.videoHeight) return;

  resizeRegionPreviewCanvasToDisplay();
  const dpr = window.devicePixelRatio || 1;
  const cw = regionPreviewCanvas.width;
  const ch = regionPreviewCanvas.height;

  regionPreviewCtx.save();
  regionPreviewCtx.setTransform(1, 0, 0, 1, 0, 0);
  regionPreviewCtx.clearRect(0, 0, cw, ch);
  regionPreviewCtx.fillStyle = "#000";
  regionPreviewCtx.fillRect(0, 0, cw, ch);

  const crop = getRegionCrop();
  const sw = Math.max(1, crop.w);
  const sh = Math.max(1, crop.h);

  const maxX = Math.max(0, regionPreviewVideo.videoWidth - sw);
  const maxY = Math.max(0, regionPreviewVideo.videoHeight - sh);
  const sx = clamp(crop.x, 0, maxX);
  const sy = clamp(crop.y, 0, maxY);

  if (sx !== crop.x) regionX.value = String(sx);
  if (sy !== crop.y) regionY.value = String(sy);

  // Match PiP rendering exactly: cover-fit the crop into the canvas, then apply zoom/pan.
  const scaleFit = Math.max(cw / sw, ch / sh);
  const baseW = sw * scaleFit;
  const baseH = sh * scaleFit;

  const centerX = cw / 2 + regionPreviewPanX * dpr;
  const centerY = ch / 2 + regionPreviewPanY * dpr;

  regionPreviewCtx.translate(centerX, centerY);
  regionPreviewCtx.scale(regionPreviewZoomValue, regionPreviewZoomValue);
  regionPreviewCtx.drawImage(regionPreviewVideo, sx, sy, sw, sh, -baseW / 2, -baseH / 2, baseW, baseH);

  regionPreviewCtx.restore();
}

async function createRegionPip() {
  const screen = selectedRegionScreen();
  if (!screen) {
    alert("No screen selected.");
    return;
  }

  const crop = getRegionCrop();
  updateRegionInfo();
  await InfinitePIP.openRegionPip({
    sourceId: screen.id,
    sourceName: `Region (${crop.w}×${crop.h} at ${crop.x},${crop.y})`,
    crop,
    view: {
      zoom: regionPreviewZoomValue,
      panX: regionPreviewPanX,
      panY: regionPreviewPanY
    }
  });
}

function stopRegionPreview() {
  cancelAnimationFrame(regionPreviewRaf);
  regionPreviewRaf = 0;
  if (regionPreviewStream) {
    for (const t of regionPreviewStream.getTracks()) {
      try {
        t.stop();
      } catch {
        // ignore
      }
    }
    regionPreviewStream = null;
  }
  regionPreviewVideo.srcObject = null;
}

async function startRegionPreview() {
  if (regionPreviewInFlight) return;
  const screen = selectedRegionScreen();
  if (!screen) {
    regionPreviewStatus.textContent = "No screen selected.";
    return;
  }

  updateRegionInfo();
  applyRegionPreviewLayoutFromInputs();
  regionPreviewStatus.textContent = "Starting preview…";

  regionPreviewInFlight = true;
  try {
    stopRegionPreview();
    const constraints = {
      audio: false,
      video: { mandatory: { chromeMediaSource: "desktop", chromeMediaSourceId: screen.id } }
    };
    // eslint-disable-next-line no-undef
    regionPreviewStream = await navigator.mediaDevices.getUserMedia(constraints);
    regionPreviewVideo.srcObject = regionPreviewStream;
    await regionPreviewVideo.play();

    cancelAnimationFrame(regionPreviewRaf);
    regionPreviewRaf = requestAnimationFrame(drawRegionPreview);
    regionPreviewStatus.textContent = "Live crop tool.";
  } catch (err) {
    console.error(err);
    stopRegionPreview();
    regionPreviewStatus.textContent = "Preview failed (check permissions / try another screen).";
  } finally {
    regionPreviewInFlight = false;
  }
}

function updateStatus(count) {
  pipCount.textContent = `${count} Active PIPs`;
  if (count > 0) {
    statusDot.classList.add("active");
    statusText.textContent = "Active";
  } else {
    statusDot.classList.remove("active");
    statusText.textContent = "Ready";
  }
}

function renderActivePips(pips) {
  activePipsList.innerHTML = "";
  const list = Array.isArray(pips) ? pips : [];
  activePipsEmpty.classList.toggle("hidden", list.length > 0);

  for (const p of list) {
    const row = document.createElement("div");
    row.className = "pipItem";

    const meta = document.createElement("div");
    meta.className = "pipMeta";
    const title = document.createElement("div");
    title.className = "pipTitle";
    title.textContent = p.sourceName || "PiP";
    const sub = document.createElement("div");
    sub.className = "pipSub";
    sub.textContent = `${p.sourceId || ""} • #${p.pipId ?? ""}`;
    meta.appendChild(title);
    meta.appendChild(sub);

    const actions = document.createElement("div");
    actions.style.display = "flex";
    actions.style.gap = "10px";
    const closeBtn = document.createElement("button");
    closeBtn.className = "btn danger";
    closeBtn.textContent = "Close";
    closeBtn.addEventListener("click", async () => {
      try {
        await InfinitePIP.closePip(p.pipId);
      } catch (err) {
        console.error(err);
        alert(String(err?.message || err));
      }
    });
    actions.appendChild(closeBtn);

    row.appendChild(meta);
    row.appendChild(actions);
    activePipsList.appendChild(row);
  }
}

async function refreshActivePips() {
  try {
    const list = await InfinitePIP.getPipsList();
    renderActivePips(list);
  } catch (err) {
    console.error(err);
    activePipsList.innerHTML = "";
    activePipsEmpty.classList.remove("hidden");
    activePipsEmpty.textContent = `Failed to load active PiPs.\n\n${String(err?.message || err)}`;
  }
}

function escapeHtml(str) {
  return String(str)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

tabScreens.addEventListener("click", () => setTab("screens"));
tabWindows.addEventListener("click", () => setTab("windows"));
tabRegions.addEventListener("click", () => setTab("regions"));
tabActive.addEventListener("click", () => setTab("active"));

refreshBtn.addEventListener("click", loadSources);
closeAllBtn.addEventListener("click", () => {
  return InfinitePIP.closeAllPips();
});
closeAllBtn2.addEventListener("click", () => {
  return InfinitePIP.closeAllPips();
});

for (const input of [regionX, regionY, regionW, regionH]) {
  input.addEventListener("input", () => {
    updateRegionInfo();
    applyRegionPreviewLayoutFromInputs();
    // Crop changes should reflect immediately in the live preview.
    if (currentTab === "regions") regionPreviewStatus.textContent = "Live crop tool.";
  });
}
regionScreenSelect.addEventListener("change", () => {
  if (currentTab === "regions") startRegionPreview();
});
regionPreviewBtn.addEventListener("click", () => startRegionPreview());
regionCreateBtn.addEventListener("click", createRegionPip);

regionPreviewZoom.addEventListener("input", () => {
  regionPreviewZoomValue = Number(regionPreviewZoom.value || 1);
  applyRegionPreviewLayoutFromInputs();
});

// Dragging is always enabled for crop positioning.
regionPreviewCanvas.classList.add("pan");

regionPreviewReset.addEventListener("click", () => {
  regionPreviewZoomValue = 1.0;
  regionPreviewZoom.value = "1";
  regionPreviewPanX = 0;
  regionPreviewPanY = 0;
});

regionPreviewCanvas.addEventListener("pointerdown", (e) => {
  regionPreviewDragging = true;
  regionPreviewCanvas.classList.add("dragging");
  regionPreviewCanvas.setPointerCapture(e.pointerId);
  regionPreviewDragStart = {
    x: e.clientX,
    y: e.clientY,
    cropX: Number(regionX.value || 0),
    cropY: Number(regionY.value || 0),
    panX: regionPreviewPanX,
    panY: regionPreviewPanY
  };
});

regionPreviewCanvas.addEventListener("pointermove", (e) => {
  if (!regionPreviewDragging || !regionPreviewDragStart) return;
  const dx = e.clientX - regionPreviewDragStart.x;
  const dy = e.clientY - regionPreviewDragStart.y;

  // Drag screen under the viewport -> adjust crop origin (X/Y).
  const crop = getRegionCrop();
  const sw = Math.max(1, crop.w);
  const sh = Math.max(1, crop.h);
  const cssW = Math.max(1, regionPreviewCanvas.clientWidth);
  const cssH = Math.max(1, regionPreviewCanvas.clientHeight);
  const scaleFitCss = Math.max(cssW / sw, cssH / sh);

  const dxSrc = -dx / (scaleFitCss * regionPreviewZoomValue);
  const dySrc = -dy / (scaleFitCss * regionPreviewZoomValue);

  const maxX = Math.max(0, regionPreviewVideo.videoWidth - sw);
  const maxY = Math.max(0, regionPreviewVideo.videoHeight - sh);
  const nextX = clamp(regionPreviewDragStart.cropX + dxSrc, 0, maxX);
  const nextY = clamp(regionPreviewDragStart.cropY + dySrc, 0, maxY);

  regionX.value = String(Math.round(nextX));
  regionY.value = String(Math.round(nextY));
  updateRegionInfo();
});

applyRegionPreviewLayoutFromInputs();

function endRegionPreviewDrag() {
  regionPreviewDragging = false;
  regionPreviewDragStart = null;
  regionPreviewCanvas.classList.remove("dragging");
}

regionPreviewCanvas.addEventListener("pointerup", endRegionPreviewDrag);
regionPreviewCanvas.addEventListener("pointercancel", endRegionPreviewDrag);

// Keep canvas crisp when the user resizes the preview box.
new ResizeObserver(() => {
  resizeRegionPreviewCanvasToDisplay();
}).observe(regionPreviewCanvas);

InfinitePIP.onPipsCount(updateStatus);
InfinitePIP.onPipsList((list) => {
  // Keep the Active tab live-updated.
  if (currentTab === "active") renderActivePips(list);
});
updateStatus(0);

setTab("screens");


