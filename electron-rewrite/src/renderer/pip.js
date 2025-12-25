/* global InfinitePIP */

const video = document.getElementById("video");
const canvas = document.getElementById("canvas");
const ctx = canvas.getContext("2d");
const titleEl = document.getElementById("title");
const toastEl = document.getElementById("toast");

const zoomEl = document.getElementById("zoom");
const opacityEl = document.getElementById("opacity");
const toggleAotBtn = document.getElementById("toggleAot");
const togglePanBtn = document.getElementById("togglePan");
const resetViewBtn = document.getElementById("resetView");
const closeBtn = document.getElementById("closeBtn");
const controlsEl = document.getElementById("controls");

let stream = null;
let sourceId = null;
let sourceName = "Source";
let crop = null; // {x,y,w,h} or null

let alwaysOnTop = true;
let zoom = Number(zoomEl.value);
let opacity = Number(opacityEl.value);

let panX = 0;
let panY = 0;
let dragging = false;
let dragStart = null; // {x,y,panX,panY}
let panMode = false;

let rafId = 0;
let hideUiTimer = 0;
let uiHidden = false;
let mouseInside = true;
let hoverPollTimer = 0;

function resizeCanvas() {
  const dpr = window.devicePixelRatio || 1;
  const w = Math.max(1, Math.floor(window.innerWidth * dpr));
  const h = Math.max(1, Math.floor(window.innerHeight * dpr));
  if (canvas.width !== w || canvas.height !== h) {
    canvas.width = w;
    canvas.height = h;
  }
}

function drawFrame() {
  rafId = requestAnimationFrame(drawFrame);
  if (!video.videoWidth || !video.videoHeight) return;

  resizeCanvas();

  const dpr = window.devicePixelRatio || 1;
  const cw = canvas.width;
  const ch = canvas.height;

  ctx.save();
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.clearRect(0, 0, cw, ch);
  ctx.fillStyle = "#000";
  ctx.fillRect(0, 0, cw, ch);

  const sx = crop ? crop.x : 0;
  const sy = crop ? crop.y : 0;
  const sw = crop ? crop.w : video.videoWidth;
  const sh = crop ? crop.h : video.videoHeight;

  // Fit-crop region to canvas, then apply pan/zoom on top.
  const scaleFit = Math.max(cw / sw, ch / sh);
  const baseW = sw * scaleFit;
  const baseH = sh * scaleFit;

  const centerX = cw / 2 + panX * dpr;
  const centerY = ch / 2 + panY * dpr;

  ctx.translate(centerX, centerY);
  ctx.scale(zoom, zoom);
  ctx.drawImage(video, sx, sy, sw, sh, -baseW / 2, -baseH / 2, baseW, baseH);
  ctx.restore();
}

function showToast(text) {
  toastEl.textContent = text;
  toastEl.classList.add("show");
  clearTimeout(showToast._t);
  showToast._t = setTimeout(() => toastEl.classList.remove("show"), 700);
}

function setUiHidden(hidden) {
  uiHidden = !!hidden;
  document.body.classList.toggle("ui-hidden", uiHidden);

  // Ensure the bottom control region doesn't block window dragging when hidden.
  // (CSS sets it too, but this keeps behavior robust if we tweak styles later.)
  controlsEl.style.webkitAppRegion = uiHidden ? "drag" : "no-drag";
}

function scheduleHideIfMouseNotInside() {
  clearTimeout(hideUiTimer);
  hideUiTimer = setTimeout(() => {
    if (!mouseInside) setUiHidden(true);
  }, 3000);
}

function noteActivity() {
  if (uiHidden) setUiHidden(false);
  // If the mouse is inside the PiP, keep UI visible indefinitely.
  // Only hide after the mouse leaves (handled by mouseleave).
  if (!mouseInside) scheduleHideIfMouseNotInside();
}

async function startCapture() {
  if (!sourceId) return;

  stopCapture();

  const constraints = {
    audio: false,
    video: {
      mandatory: {
        chromeMediaSource: "desktop",
        chromeMediaSourceId: sourceId
      }
    }
  };

  // eslint-disable-next-line no-undef
  stream = await navigator.mediaDevices.getUserMedia(constraints);
  video.srcObject = stream;
  await video.play();

  cancelAnimationFrame(rafId);
  rafId = requestAnimationFrame(drawFrame);
}

function stopCapture() {
  cancelAnimationFrame(rafId);
  rafId = 0;
  if (!stream) return;
  for (const track of stream.getTracks()) {
    try {
      track.stop();
    } catch {
      // ignore
    }
  }
  stream = null;
}

function clamp(n, min, max) {
  return Math.max(min, Math.min(max, n));
}

function setOpacity(nextOpacity) {
  opacity = clamp(Number(nextOpacity), 0.1, 1);
  opacityEl.value = String(opacity);
  InfinitePIP.setPipOpacity(opacity);
  showToast(`Opacity: ${Math.round(opacity * 100)}%`);
}

function updateAotUI() {
  toggleAotBtn.textContent = `Always on Top: ${alwaysOnTop ? "On" : "Off"}`;
}

function updatePanUI() {
  togglePanBtn.textContent = `Pan Mode: ${panMode ? "On" : "Off"}`;
  // When pan mode is OFF, the canvas should be a drag region so dragging moves the window.
  // When pan mode is ON, disable app-region drag so we can receive pointer events for panning.
  canvas.style.webkitAppRegion = panMode ? "no-drag" : "drag";
  canvas.style.cursor = panMode ? "grab" : "default";
}

function resetView() {
  // 0% zoom == baseline (no extra zoom) => scale 1.0
  zoom = 1.0;
  panX = 0;
  panY = 0;
  zoomEl.value = String(zoom);
  // drawing loop picks up new values
}

function closeWindow() {
  stopCapture();
  window.close();
}

canvas.addEventListener("pointerdown", (e) => {
  if (!panMode) return;
  noteActivity();
  dragging = true;
  canvas.classList.add("dragging");
  canvas.setPointerCapture(e.pointerId);
  dragStart = { x: e.clientX, y: e.clientY, panX, panY };
});

canvas.addEventListener("pointermove", (e) => {
  if (!panMode) return;
  if (!dragging || !dragStart) return;
  const dx = e.clientX - dragStart.x;
  const dy = e.clientY - dragStart.y;
  panX = dragStart.panX + dx;
  panY = dragStart.panY + dy;
});

canvas.addEventListener("pointerup", () => {
  if (!panMode) return;
  dragging = false;
  dragStart = null;
  canvas.classList.remove("dragging");
});

canvas.addEventListener("pointercancel", () => {
  if (!panMode) return;
  dragging = false;
  dragStart = null;
  canvas.classList.remove("dragging");
});

zoomEl.addEventListener("input", () => {
  noteActivity();
  zoom = Number(zoomEl.value);
});

opacityEl.addEventListener("input", () => {
  noteActivity();
  setOpacity(opacityEl.value);
});

toggleAotBtn.addEventListener("click", async () => {
  noteActivity();
  alwaysOnTop = !alwaysOnTop;
  await InfinitePIP.setPipAlwaysOnTop(alwaysOnTop);
  updateAotUI();
});

togglePanBtn.addEventListener("click", () => {
  noteActivity();
  panMode = !panMode;
  updatePanUI();
  showToast(panMode ? "Pan Mode: On" : "Pan Mode: Off");
});

resetViewBtn.addEventListener("click", () => {
  noteActivity();
  resetView();
});
closeBtn.addEventListener("click", closeWindow);

window.addEventListener("contextmenu", (e) => {
  noteActivity();
  e.preventDefault();
  closeWindow();
});

window.addEventListener("keydown", (e) => {
  noteActivity();
  if (e.key === "Escape") closeWindow();
  if (e.key === "+" || e.key === "=") setOpacity(opacity + 0.1);
  if (e.key === "-") setOpacity(opacity - 0.1);
  if (e.key === "0") setOpacity(1);
});

window.addEventListener("mousemove", noteActivity, { passive: true });
window.addEventListener("mousedown", noteActivity, { passive: true });
window.addEventListener("wheel", noteActivity, { passive: true });

async function pollHover() {
  try {
    const inside = await InfinitePIP.isCursorInsidePip();
    if (inside !== mouseInside) {
      mouseInside = inside;
      if (mouseInside) {
        setUiHidden(false);
        clearTimeout(hideUiTimer);
      } else {
        scheduleHideIfMouseNotInside();
      }
    }
  } catch {
    // ignore
  }
}

InfinitePIP.onPipInit(async (payload) => {
  sourceId = payload?.sourceId || null;
  sourceName = payload?.sourceName || "Source";
  crop = payload?.crop || null;
  titleEl.textContent = `PiP — ${sourceName}`;
  updateAotUI();
  updatePanUI();
  setOpacity(opacity);
  resetView();
  setUiHidden(false);
  mouseInside = true;
  clearTimeout(hideUiTimer);

  clearInterval(hoverPollTimer);
  hoverPollTimer = setInterval(pollHover, 200);
  pollHover();
  await startCapture();
});

window.addEventListener("beforeunload", () => {
  clearInterval(hoverPollTimer);
  stopCapture();
});

window.addEventListener("resize", () => {
  resizeCanvas();
});


