const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("api", {
  getConfig: () => ipcRenderer.invoke("app:get-config"),
  saveConfig: (config) => ipcRenderer.invoke("app:save-config", config),
  getAppInfo: () => ipcRenderer.invoke("app:get-info"),
  profileStorageId: (name) => ipcRenderer.invoke("app:profile-id", name),
  getStealthPreloadPath: () => ipcRenderer.invoke("app:get-stealth-preload"),
  getOfflineHtml: () => ipcRenderer.invoke("app:get-offline-html"),
  getThemes: () => ipcRenderer.invoke("app:get-themes"),
  getMasks: () => ipcRenderer.invoke("app:get-masks"),
  getColors: () => ipcRenderer.invoke("app:get-colors"),
  getAvatarColors: () => ipcRenderer.invoke("app:get-avatar-colors"),
  
  openDownloadsFolder: (customPath) => ipcRenderer.invoke("app:open-downloads", customPath),
  browseFolder: (defaultPath) => ipcRenderer.invoke("app:browse-folder", defaultPath),
  openAppFolder: () => ipcRenderer.invoke("app:open-app-folder"),
  clearCache: (profileName) => ipcRenderer.invoke("app:clear-cache", profileName),
  createSupportReport: (activeProfile, userAgent) => ipcRenderer.invoke("app:support-report", { activeProfile, userAgent }),
  
  cancelDownload: (id) => ipcRenderer.invoke("app:cancel-download", id),
  downloadUrl: (profileName, url) => ipcRenderer.invoke("app:download-url", { profileName, url }),
  windowAction: (action) => ipcRenderer.invoke("app:window-action", action),
  isMaximized: () => ipcRenderer.invoke("app:is-maximized"),
  openExternal: (url) => ipcRenderer.invoke("app:open-external", url),
  
  applyProfileSession: (profileName, config) => ipcRenderer.invoke("app:apply-profile-session", { profileName, config }),
  deleteProfileStorage: (profileName) => ipcRenderer.invoke("app:delete-profile-storage", profileName),

  // Events from Main Process
  onDownloadProgress: (cb) => {
    const handler = (e, data) => cb(data);
    ipcRenderer.on("download:progress", handler);
    return () => ipcRenderer.removeListener("download:progress", handler);
  },
  onDownloadComplete: (cb) => {
    const handler = (e, data) => cb(data);
    ipcRenderer.on("download:complete", handler);
    return () => ipcRenderer.removeListener("download:complete", handler);
  },
  onShortcut: (cb) => {
    const handler = (e, action) => cb(action);
    ipcRenderer.on("shortcut:action", handler);
    return () => ipcRenderer.removeListener("shortcut:action", handler);
  },
  onOpenSettings: (cb) => {
    const handler = () => cb();
    ipcRenderer.on("tray:open-settings", handler);
    return () => ipcRenderer.removeListener("tray:open-settings", handler);
  },
  onMaximizeChanged: (cb) => {
    const handler = (e, isMax) => cb(isMax);
    ipcRenderer.on("win:maximize-changed", handler);
    return () => ipcRenderer.removeListener("win:maximize-changed", handler);
  }
});
