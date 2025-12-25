const path = require("node:path");
const { app, BrowserWindow, ipcMain, nativeTheme, desktopCapturer, screen } = require("electron");

/** @type {BrowserWindow | null} */
let mainWindow = null;

/** @type {Set<BrowserWindow>} */
const pipWindows = new Set();

/** @type {Map<BrowserWindow, { pipId: number, sourceId: string, sourceName: string }>} */
const pipMeta = new Map();

let pipIdSeq = 1;

// Required for older-style getUserMedia constraints (chromeMediaSource / chromeMediaSourceId),
// and generally helps ensure desktop capture is enabled.
app.commandLine.appendSwitch("enable-usermedia-screen-capturing");
app.commandLine.appendSwitch("allow-http-screen-capture");

function createMainWindow() {
  const win = new BrowserWindow({
    width: 1100,
    height: 760,
    minWidth: 900,
    minHeight: 600,
    backgroundColor: "#0b1220",
    title: "InfinitePIP",
    webPreferences: {
      // Keep main window secure; source enumeration happens via IPC in main process.
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
      preload: path.join(__dirname, "preload.js")
    }
  });

  win.loadFile(path.join(__dirname, "..", "renderer", "index.html"));
  win.on("closed", () => {
    mainWindow = null;
  });

  return win;
}

function createPipWindow() {
  const win = new BrowserWindow({
    width: 520,
    height: 320,
    minWidth: 240,
    minHeight: 160,
    backgroundColor: "#000000",
    frame: false,
    transparent: false,
    alwaysOnTop: true,
    resizable: true,
    movable: true,
    hasShadow: true,
    title: "PiP",
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
      preload: path.join(__dirname, "preload.js")
    }
  });

  win.loadFile(path.join(__dirname, "..", "renderer", "pip.html"));
  win.on("closed", () => {
    pipWindows.delete(win);
    pipMeta.delete(win);
    sendPipsUpdate();
  });

  pipWindows.add(win);
  sendPipsUpdate();
  return win;
}

function pipsListPayload() {
  return [...pipMeta.values()]
    .slice()
    .sort((a, b) => a.pipId - b.pipId)
    .map((p) => ({ ...p }));
}

function sendPipsUpdate() {
  if (!mainWindow || mainWindow.isDestroyed()) return;
  try {
    mainWindow.webContents.send("pips:count", pipWindows.size);
    mainWindow.webContents.send("pips:list", pipsListPayload());
  } catch {
    // ignore
  }
}

app.whenReady().then(() => {
  // Keep Electron in “system” theme so it doesn’t surprise the user.
  nativeTheme.themeSource = "system";

  mainWindow = createMainWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      mainWindow = createMainWindow();
    }
  });
});

app.on("window-all-closed", () => {
  // Windows/Linux: quit when all windows are closed.
  // (macOS convention is different; handle if needed later.)
  if (process.platform !== "darwin") app.quit();
});

ipcMain.handle("pip:open", async (_evt, payload) => {
  const { sourceId, sourceName, crop, view } = payload || {};
  if (!sourceId) throw new Error("sourceId is required");

  const pip = createPipWindow();
  const pipId = pipIdSeq++;
  pipMeta.set(pip, {
    pipId,
    sourceId: String(sourceId),
    sourceName: String(sourceName || "Source")
  });
  sendPipsUpdate();

  // Send init after page is ready.
  pip.webContents.once("did-finish-load", () => {
    pip.webContents.send("pip:init", {
      sourceId,
      sourceName: sourceName || "Source",
      crop: crop || null,
      view: view || null
    });
  });

  return { ok: true };
});

ipcMain.handle("pips:list", async () => {
  return pipsListPayload();
});

ipcMain.handle("pip:close", async (_evt, pipId) => {
  const id = Number(pipId);
  if (!Number.isFinite(id)) return { ok: false };
  for (const [win, meta] of pipMeta.entries()) {
    if (meta?.pipId === id) {
      try {
        win.close();
        return { ok: true };
      } catch {
        return { ok: false };
      }
    }
  }
  return { ok: false };
});

ipcMain.handle("app:diagnostics", async () => {
  return {
    platform: process.platform,
    arch: process.arch,
    versions: process.versions,
    hasDesktopCapturer: !!desktopCapturer?.getSources
  };
});

ipcMain.handle("sources:get", async (_evt, options) => {
  if (!desktopCapturer?.getSources) {
    throw new Error("desktopCapturer.getSources is unavailable in main process");
  }

  const sources = await desktopCapturer.getSources(options || { types: ["screen", "window"] });
  return sources.map((s) => ({
    id: s.id,
    name: s.name,
    thumbnailDataUrl: s.thumbnail?.toDataURL?.() || null,
    appIconDataUrl: s.appIcon?.toDataURL?.() || null
  }));
});

ipcMain.handle("pip:setAlwaysOnTop", async (evt, value) => {
  const win = BrowserWindow.fromWebContents(evt.sender);
  if (!win) return { ok: false };
  win.setAlwaysOnTop(!!value, "screen-saver");
  return { ok: true };
});

ipcMain.handle("pip:setOpacity", async (evt, value) => {
  const win = BrowserWindow.fromWebContents(evt.sender);
  if (!win) return { ok: false };
  const v = Number(value);
  if (Number.isNaN(v)) return { ok: false };
  win.setOpacity(Math.max(0.1, Math.min(1, v)));
  return { ok: true };
});

ipcMain.handle("pip:setAspectRatio", async (evt, ratio) => {
  const win = BrowserWindow.fromWebContents(evt.sender);
  if (!win) return { ok: false };
  const r = Number(ratio);
  if (!Number.isFinite(r)) return { ok: false };
  try {
    // Electron: ratio 0 disables the aspect ratio constraint.
    win.setAspectRatio(r);
    return { ok: true };
  } catch {
    return { ok: false };
  }
});

ipcMain.handle("pip:isCursorInside", async (evt) => {
  const win = BrowserWindow.fromWebContents(evt.sender);
  if (!win) return false;
  const { x, y } = screen.getCursorScreenPoint();
  const b = win.getBounds();
  return x >= b.x && x < b.x + b.width && y >= b.y && y < b.y + b.height;
});

ipcMain.handle("pips:closeAll", async () => {
  for (const win of [...pipWindows]) {
    try {
      win.close();
    } catch {
      // ignore
    }
  }
  sendPipsUpdate();
  return { ok: true };
});


