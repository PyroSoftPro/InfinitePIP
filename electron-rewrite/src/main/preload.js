const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("InfinitePIP", {
  async diagnostics() {
    return await ipcRenderer.invoke("app:diagnostics");
  },

  async getVersion() {
    return await ipcRenderer.invoke("app:version");
  },

  async getSources({ types = ["screen", "window"], thumbnailSize = { width: 320, height: 200 } } = {}) {
    try {
      return await ipcRenderer.invoke("sources:get", { types, thumbnailSize, fetchWindowIcons: true });
    } catch (err) {
      try {
        return await ipcRenderer.invoke("sources:get", { types, thumbnailSize, fetchWindowIcons: false });
      } catch (err2) {
        const message = String(err2?.message || err2 || err?.message || err);
        const stack = err2?.stack || err?.stack || "";
        throw new Error(
          `getSources failed (${process.platform}). ${message}${stack ? `\n${stack}` : ""}`
        );
      }
    }
  },

  openPip({ sourceId, sourceName }) {
    return ipcRenderer.invoke("pip:open", { sourceId, sourceName });
  },

  openRegionPip({ sourceId, sourceName, crop, view }) {
    return ipcRenderer.invoke("pip:open", { sourceId, sourceName, crop, view });
  },

  closeAllPips() {
    return ipcRenderer.invoke("pips:closeAll");
  },

  getPipsList() {
    return ipcRenderer.invoke("pips:list");
  },

  closePip(pipId) {
    return ipcRenderer.invoke("pip:close", pipId);
  },

  setPipAlwaysOnTop(value) {
    return ipcRenderer.invoke("pip:setAlwaysOnTop", value);
  },

  setPipOpacity(value) {
    return ipcRenderer.invoke("pip:setOpacity", value);
  },

  setPipAspectRatio(ratio) {
    return ipcRenderer.invoke("pip:setAspectRatio", ratio);
  },

  isCursorInsidePip() {
    return ipcRenderer.invoke("pip:isCursorInside");
  },

  onPipInit(cb) {
    ipcRenderer.on("pip:init", (_evt, payload) => cb(payload));
    return () => ipcRenderer.removeAllListeners("pip:init");
  },

  onPipsCount(cb) {
    ipcRenderer.on("pips:count", (_evt, count) => cb(count));
    return () => ipcRenderer.removeAllListeners("pips:count");
  },

  onPipsList(cb) {
    ipcRenderer.on("pips:list", (_evt, list) => cb(list));
    return () => ipcRenderer.removeAllListeners("pips:list");
  }
});


