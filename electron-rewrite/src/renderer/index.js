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
const regionPreviewImg = el("regionPreviewImg");
const regionPreviewStatus = el("regionPreviewStatus");

const statusDot = el("statusDot");
const statusText = el("statusText");
const pipCount = el("pipCount");

let currentTab = "screens"; // screens | windows | regions | active

let regionScreens = [];
let regionPreviewInFlight = false;

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
  } else if (tab === "windows") {
    panelTitle.textContent = "Application Windows";
    panelHelp.textContent = "Capture and display content from any application window.";
    loadSources();
  } else if (tab === "regions") {
    ensureRegionScreens().then(() => {
      // Auto-run preview when the user enters the Regions page.
      captureRegionPreview();
    });
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

async function captureRegionPreview() {
  if (regionPreviewInFlight) return;
  const screen = selectedRegionScreen();
  if (!screen) {
    regionPreviewStatus.textContent = "No screen selected.";
    return;
  }

  const crop = getRegionCrop();
  updateRegionInfo();
  regionPreviewStatus.textContent = "Capturing preview…";

  let stream = null;
  regionPreviewInFlight = true;
  try {
    const constraints = {
      audio: false,
      video: { mandatory: { chromeMediaSource: "desktop", chromeMediaSourceId: screen.id } }
    };
    // eslint-disable-next-line no-undef
    stream = await navigator.mediaDevices.getUserMedia(constraints);

    const v = document.createElement("video");
    v.muted = true;
    v.playsInline = true;
    v.srcObject = stream;
    await v.play();

    await new Promise((r) => setTimeout(r, 60));

    const canvas = document.createElement("canvas");
    canvas.width = Math.max(1, crop.w);
    canvas.height = Math.max(1, crop.h);
    const ctx = canvas.getContext("2d");
    ctx.drawImage(v, crop.x, crop.y, crop.w, crop.h, 0, 0, canvas.width, canvas.height);

    regionPreviewImg.src = canvas.toDataURL("image/jpeg", 0.85);
    regionPreviewStatus.textContent = "Preview updated.";
  } catch (err) {
    console.error(err);
    regionPreviewStatus.textContent = "Preview failed (are coordinates valid for that screen?).";
  } finally {
    regionPreviewInFlight = false;
    if (stream) {
      for (const t of stream.getTracks()) {
        try {
          t.stop();
        } catch {
          // ignore
        }
      }
    }
  }
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
    crop
  });
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
  input.addEventListener("input", updateRegionInfo);
}
regionPreviewBtn.addEventListener("click", captureRegionPreview);
regionCreateBtn.addEventListener("click", createRegionPip);

InfinitePIP.onPipsCount(updateStatus);
updateStatus(0);

setTab("screens");


