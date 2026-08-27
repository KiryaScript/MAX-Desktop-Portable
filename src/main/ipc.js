const { ipcMain, dialog, shell, session } = require("electron");
const path = require("path");
const fs = require("fs");
const os = require("os");
const { APP_NAME, APP_VERSION, Colors, MASKS_DB, THEMES, OFFLINE_HTML, AVATAR_COLORS } = require("./constants");
const {
  getAppDir,
  loadConfig,
  saveConfig,
  profileStorageId,
  getDownloadsFolder
} = require("./config");
const { applySessionStealth } = require("./stealth");
const { createAndOpenSupportReport } = require("./diagnostics");

const MIME_EXT_MAP = {
  "image/jpeg": ".jpg",
  "image/png": ".png",
  "image/webp": ".webp",
  "image/gif": ".gif",
  "image/svg+xml": ".svg",
  "video/mp4": ".mp4",
  "video/webm": ".webm",
  "video/quicktime": ".mov",
  "video/x-matroska": ".mkv",
  "audio/mpeg": ".mp3",
  "audio/ogg": ".ogg",
  "audio/wav": ".wav",
  "audio/mp4": ".m4a",
  "audio/aac": ".aac",
  "application/pdf": ".pdf",
  "application/zip": ".zip",
  "application/x-rar-compressed": ".rar",
  "application/x-7z-compressed": ".7z",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
  "application/msword": ".doc",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
  "application/vnd.ms-excel": ".xls",
  "text/plain": ".txt"
};

function resolveDownloadFilename(rawFilename, mimeType) {
  let name = (rawFilename || "attachment").trim();
  // Strip URL query params if present in filename
  name = name.split("?")[0].split("#")[0];

  if (!name || name === "download" || name === "attachment") {
    name = "file_" + Date.now();
  }

  // If file doesn't have an extension, try to infer it from MIME type
  if (!path.extname(name)) {
    if (mimeType && MIME_EXT_MAP[mimeType.toLowerCase()]) {
      name += MIME_EXT_MAP[mimeType.toLowerCase()];
    } else if (mimeType && mimeType.includes("webp")) {
      name += ".webp";
    } else if (mimeType && mimeType.includes("mp4")) {
      name += ".mp4";
    } else if (mimeType && mimeType.includes("png")) {
      name += ".png";
    } else if (mimeType && mimeType.includes("jpeg")) {
      name += ".jpg";
    } else if (mimeType && mimeType.includes("pdf")) {
      name += ".pdf";
    }
  }
  return name;
}

function attachDownloadHandler(ses, activeDownloads, getMainWindow, getTray) {
  if (!ses) return;

  ses.removeAllListeners("will-download");
  ses.on("will-download", (event, item, webContents) => {
    const config = loadConfig();
    const downloadFolder = getDownloadsFolder(config.global ? config.global.download_path : "");
    if (!fs.existsSync(downloadFolder)) {
      try {
        fs.mkdirSync(downloadFolder, { recursive: true });
      } catch (e) {}
    }

    const mimeType = item.getMimeType ? item.getMimeType() : "";
    const rawName = item.getFilename() || "attachment";
    const resolvedName = resolveDownloadFilename(rawName, mimeType);

    let target = path.join(downloadFolder, resolvedName);
    if (fs.existsSync(target)) {
      const ext = path.extname(resolvedName);
      const stem = path.basename(resolvedName, ext);
      const now = new Date();
      const pad = (n) => String(n).padStart(2, "0");
      const timestamp = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}_${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
      target = path.join(downloadFolder, `${stem}_${timestamp}${ext}`);
    }

    item.setSavePath(target);
    const downloadId = `${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
    if (activeDownloads) activeDownloads.set(downloadId, item);

    const mainWindow = getMainWindow ? getMainWindow() : null;
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send("download:progress", {
        id: downloadId,
        filename: path.basename(target),
        receivedBytes: 0,
        totalBytes: item.getTotalBytes(),
        state: "progressing"
      });
    }

    item.on("updated", (e, state) => {
      if (state === "interrupted" || state === "progressing") {
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.webContents.send("download:progress", {
            id: downloadId,
            filename: path.basename(target),
            receivedBytes: item.getReceivedBytes(),
            totalBytes: item.getTotalBytes(),
            state: state
          });
        }
      }
    });

    item.once("done", (e, state) => {
      if (activeDownloads) activeDownloads.delete(downloadId);
      const isCompleted = state === "completed";

      if (mainWindow && !mainWindow.isDestroyed()) {
        mainWindow.webContents.send("download:complete", {
          id: downloadId,
          filename: path.basename(target),
          fullPath: target,
          success: isCompleted
        });
      }

      const tray = getTray ? getTray() : null;
      if (isCompleted && tray) {
        try {
          tray.displayBalloon({
            title: "Загрузка завершена",
            content: `Файл сохранён: ${path.basename(target)}`,
            iconType: "info"
          });
        } catch (err) {}
      }
    });
  });
}

function setupProfileSession(profileName, profileConfig, globalConfig, activeDownloads, getMainWindow, getTray) {
  const pid = profileStorageId(profileName);
  const partitionName = `persist:profile_${pid}`;
  const ses = session.fromPartition(partitionName, { cache: true });

  // Grant all permissions for media playback, notifications, audio/video capture, clipboard, fullscreen
  try {
    ses.setPermissionRequestHandler((webContents, permission, callback) => {
      callback(true);
    });
    ses.setPermissionCheckHandler(() => true);
  } catch (e) {}

  applySessionStealth(ses, profileConfig, globalConfig);
  attachDownloadHandler(ses, activeDownloads, getMainWindow, getTray);

  return ses;
}

function registerIpcHandlers({ activeDownloads, getMainWindow, getTray } = {}) {
  const handlerNames = [
    "app:get-config", "app:save-config", "app:get-info", "app:profile-id",
    "app:get-stealth-preload", "app:get-offline-html", "app:get-themes",
    "app:get-masks", "app:get-colors", "app:get-avatar-colors",
    "app:open-downloads", "app:browse-folder", "app:open-app-folder",
    "app:clear-cache", "app:support-report", "app:cancel-download",
    "app:window-action", "app:apply-profile-session", "app:delete-profile-storage",
    "app:open-external", "app:is-maximized", "app:download-url"
  ];
  for (const name of handlerNames) {
    ipcMain.removeHandler(name);
  }

  // Hook default session download handler as well
  attachDownloadHandler(session.defaultSession, activeDownloads, getMainWindow, getTray);

  ipcMain.handle("app:get-config", () => {
    const cfg = loadConfig();
    for (const [name, pConfig] of Object.entries(cfg.profiles || {})) {
      setupProfileSession(name, pConfig, cfg.global, activeDownloads, getMainWindow, getTray);
    }
    return cfg;
  });

  ipcMain.handle("app:save-config", (event, newConfig) => {
    const ok = saveConfig(newConfig);
    if (ok) {
      for (const [name, pConfig] of Object.entries(newConfig.profiles || {})) {
        setupProfileSession(name, pConfig, newConfig.global, activeDownloads, getMainWindow, getTray);
      }
    }
    return ok;
  });

  ipcMain.handle("app:get-info", () => {
    return {
      name: APP_NAME,
      version: APP_VERSION,
      node: process.versions.node,
      electron: process.versions.electron,
      chrome: process.versions.chrome,
      os: `${os.type()} ${os.release()}`
    };
  });

  ipcMain.handle("app:profile-id", (event, name) => {
    return profileStorageId(name);
  });

  ipcMain.handle("app:get-stealth-preload", () => {
    return path.join(__dirname, "../preload/stealth-preload.js");
  });

  ipcMain.handle("app:get-offline-html", () => {
    return OFFLINE_HTML;
  });

  ipcMain.handle("app:get-themes", () => {
    return THEMES;
  });

  ipcMain.handle("app:get-masks", () => {
    return MASKS_DB;
  });

  ipcMain.handle("app:get-colors", () => {
    return Colors;
  });

  ipcMain.handle("app:get-avatar-colors", () => {
    return AVATAR_COLORS;
  });

  ipcMain.handle("app:open-downloads", (event, customPath) => {
    const dir = getDownloadsFolder(customPath);
    if (!fs.existsSync(dir)) {
      try {
        fs.mkdirSync(dir, { recursive: true });
      } catch (e) {}
    }
    shell.openPath(dir);
    return true;
  });

  ipcMain.handle("app:browse-folder", async (event, defaultPath) => {
    const mainWindow = getMainWindow ? getMainWindow() : null;
    if (!mainWindow) return null;
    const res = await dialog.showOpenDialog(mainWindow, {
      title: "Выберите папку загрузок",
      defaultPath: defaultPath || getDownloadsFolder(),
      properties: ["openDirectory", "createDirectory"]
    });
    if (!res.canceled && res.filePaths && res.filePaths.length > 0) {
      return res.filePaths[0];
    }
    return null;
  });

  ipcMain.handle("app:open-app-folder", () => {
    shell.openPath(getAppDir());
    return true;
  });

  ipcMain.handle("app:clear-cache", async (event, profileName) => {
    const pid = profileStorageId(profileName);
    const partitionName = `persist:profile_${pid}`;
    const ses = session.fromPartition(partitionName);
    try {
      await ses.clearCache();
      await ses.clearStorageData();
      return true;
    } catch (e) {
      console.warn("Failed to clear cache:", e);
      return false;
    }
  });

  ipcMain.handle("app:support-report", async (event, { activeProfile, userAgent }) => {
    const config = loadConfig();
    const reportPath = await createAndOpenSupportReport(config, activeProfile, userAgent);
    return reportPath;
  });

  ipcMain.handle("app:download-url", (event, { profileName, url }) => {
    const pid = profileStorageId(profileName);
    const partitionName = `persist:profile_${pid}`;
    const ses = session.fromPartition(partitionName);
    try {
      if (typeof ses.downloadURL === "function") {
        ses.downloadURL(url);
        return true;
      }
    } catch (e) {
      console.warn("Direct ses.downloadURL failed:", e);
    }
    return false;
  });

  ipcMain.handle("app:cancel-download", (event, id) => {
    if (activeDownloads && activeDownloads.has(id)) {
      const item = activeDownloads.get(id);
      try {
        item.cancel();
      } catch (e) {}
      activeDownloads.delete(id);
      return true;
    }
    return false;
  });

  ipcMain.handle("app:open-external", (event, url) => {
    if (url && (url.startsWith("http://") || url.startsWith("https://") || url.startsWith("mailto:"))) {
      shell.openExternal(url);
      return true;
    }
    return false;
  });

  ipcMain.handle("app:is-maximized", () => {
    const mainWindow = getMainWindow ? getMainWindow() : null;
    return mainWindow ? mainWindow.isMaximized() : false;
  });

  ipcMain.handle("app:window-action", (event, action) => {
    const mainWindow = getMainWindow ? getMainWindow() : null;
    if (!mainWindow) return;
    if (action === "minimize") {
      mainWindow.minimize();
    } else if (action === "maximize") {
      if (mainWindow.isMaximized()) {
        mainWindow.unmaximize();
      } else {
        mainWindow.maximize();
      }
    } else if (action === "close") {
      mainWindow.close();
    }
  });

  ipcMain.handle("app:apply-profile-session", (event, { profileName, config }) => {
    const appConfig = loadConfig();
    setupProfileSession(profileName, config, appConfig.global, activeDownloads, getMainWindow, getTray);
    return true;
  });

  ipcMain.handle("app:delete-profile-storage", async (event, profileName) => {
    const pid = profileStorageId(profileName);
    const partitionName = `persist:profile_${pid}`;
    try {
      const ses = session.fromPartition(partitionName);
      await ses.clearStorageData();
      await ses.clearCache();
    } catch (e) {}

    const storagePath = path.join(getAppDir(), "storage", pid);
    if (fs.existsSync(storagePath)) {
      try {
        fs.rmSync(storagePath, { recursive: true, force: true });
      } catch (e) {}
    }
    return true;
  });
}

module.exports = {
  registerIpcHandlers,
  setupProfileSession,
  attachDownloadHandler
};
