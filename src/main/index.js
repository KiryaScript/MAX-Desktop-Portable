const { app, BrowserWindow, Tray, Menu, shell } = require("electron");
const path = require("path");
const fs = require("fs");
const { APP_NAME, APP_VERSION, Colors } = require("./constants");
const {
  getAppDir,
  loadConfig,
  loadWindowState,
  saveWindowState
} = require("./config");
const { registerIpcHandlers, attachDownloadHandler } = require("./ipc");

// Redirect storage/userData to local app directory for 100% portability
const appDir = getAppDir();
const portableDataDir = path.join(appDir, "storage", "userData");
try {
  if (!fs.existsSync(portableDataDir)) {
    fs.mkdirSync(portableDataDir, { recursive: true });
  }
  app.setPath("userData", portableDataDir);
} catch (e) {
  console.warn("Could not set custom userData directory:", e);
}

// Hardware, Media Playback & OS Compatibility flags (Win 10 LTSC / IoT / Lite / Win 11)
app.commandLine.appendSwitch("disable-features", "CalculateNativeWinOcclusion,SpareRendererForSitePerProcess");
app.commandLine.appendSwitch("disable-background-timer-throttling");
app.commandLine.appendSwitch("disable-renderer-backgrounding");
app.commandLine.appendSwitch("enable-smooth-scrolling");
app.commandLine.appendSwitch("force-color-profile", "srgb");
app.commandLine.appendSwitch("autoplay-policy", "no-user-gesture-required");
app.commandLine.appendSwitch("enable-gpu-rasterization");
app.commandLine.appendSwitch("force-webrtc-ip-handling-policy", "default_public_interface_only");

// Single Instance Lock
const gotTheLock = app.requestSingleInstanceLock();
if (!gotTheLock) {
  app.quit();
}

let mainWindow = null;
let tray = null;
let isQuitting = false;
const activeDownloads = new Map();

function getIconPath() {
  const iconPath = path.join(getAppDir(), "max.ico");
  if (fs.existsSync(iconPath)) {
    return iconPath;
  }
  const fallback = path.resolve(__dirname, "../../max.ico");
  if (fs.existsSync(fallback)) {
    return fallback;
  }
  return null;
}

function createWindow() {
  const windowState = loadWindowState();
  const iconPath = getIconPath();

  let bounds = {
    width: 1340,
    height: 880,
    minWidth: 800,
    minHeight: 500
  };

  if (windowState && windowState.width && windowState.height) {
    bounds.width = windowState.width;
    bounds.height = windowState.height;
    if (typeof windowState.x === "number" && typeof windowState.y === "number") {
      bounds.x = windowState.x;
      bounds.y = windowState.y;
    }
  }

  mainWindow = new BrowserWindow({
    ...bounds,
    frame: false,
    titleBarStyle: "hidden",
    backgroundColor: Colors.BG_DARKEST,
    icon: iconPath || undefined,
    show: false,
    webPreferences: {
      preload: path.join(__dirname, "../preload/preload.js"),
      webviewTag: true,
      contextIsolation: true,
      nodeIntegration: false,
      spellcheck: false
    }
  });

  if (windowState && windowState.maximized) {
    mainWindow.maximize();
  }

  mainWindow.loadFile(path.join(__dirname, "../renderer/index.html"));

  mainWindow.once("ready-to-show", () => {
    mainWindow.show();
    mainWindow.focus();
  });

  mainWindow.on("maximize", () => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send("win:maximize-changed", true);
    }
    saveCurrentState();
  });

  mainWindow.on("unmaximize", () => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.webContents.send("win:maximize-changed", false);
    }
    saveCurrentState();
  });

  const saveCurrentState = () => {
    if (!mainWindow || mainWindow.isDestroyed()) return;
    const isMaximized = mainWindow.isMaximized();
    const currentBounds = mainWindow.getBounds();
    const config = loadConfig();
    if (config.global && config.global.save_window_state !== false) {
      saveWindowState({
        x: currentBounds.x,
        y: currentBounds.y,
        width: currentBounds.width,
        height: currentBounds.height,
        maximized: isMaximized
      });
    }
  };

  mainWindow.on("resize", saveCurrentState);
  mainWindow.on("move", saveCurrentState);

  mainWindow.on("close", (event) => {
    saveCurrentState();
    const config = loadConfig();
    const closeToTray = config.global ? config.global.close_to_tray !== false : true;

    if (!isQuitting && closeToTray) {
      event.preventDefault();
      mainWindow.hide();
      if (tray) {
        try {
          tray.displayBalloon({
            title: APP_NAME,
            content: "Приложение свёрнуто в фоновый режим.",
            iconType: "info"
          });
        } catch (e) {}
      }
    }
  });
}

function setupTray() {
  const iconPath = getIconPath();
  if (!iconPath) return;

  tray = new Tray(iconPath);
  tray.setToolTip(`${APP_NAME} v${APP_VERSION}`);

  const contextMenu = Menu.buildFromTemplate([
    {
      label: "Показать",
      click: () => {
        if (mainWindow) {
          mainWindow.show();
          mainWindow.focus();
        }
      }
    },
    {
      label: "Настройки",
      click: () => {
        if (mainWindow) {
          mainWindow.show();
          mainWindow.focus();
          mainWindow.webContents.send("tray:open-settings");
        }
      }
    },
    { type: "separator" },
    {
      label: "Выход",
      click: () => {
        isQuitting = true;
        app.quit();
      }
    }
  ]);

  tray.setContextMenu(contextMenu);

  tray.on("double-click", () => {
    if (mainWindow) {
      if (mainWindow.isVisible()) {
        if (mainWindow.isMinimized()) mainWindow.restore();
        mainWindow.focus();
      } else {
        mainWindow.show();
        mainWindow.focus();
      }
    }
  });
}

// Intercept window.open and downloads for all web contents (main and guest webviews)
app.on("web-contents-created", (event, contents) => {
  const ses = contents.session;
  if (ses) {
    attachDownloadHandler(ses, activeDownloads, () => mainWindow, () => tray);
  }

  contents.setWindowOpenHandler(({ url }) => {
    if (!url) return { action: "deny" };

    const isDownloadOrInternal =
      url.startsWith("blob:") ||
      url.startsWith("data:") ||
      url.includes("max.ru") ||
      url.includes("storage") ||
      url.includes("download") ||
      url.includes("file") ||
      url.includes("attachment") ||
      url.includes("media") ||
      url.includes("get_file") ||
      url.includes("selcloud") ||
      url.includes("selcdn") ||
      url.includes("bizmrg") ||
      /\.(jpg|jpeg|png|gif|webp|svg|ico|bmp|mp4|webm|mov|avi|mkv|mp3|ogg|wav|m4a|aac|flac|pdf|doc|docx|xls|xlsx|ppt|pptx|zip|rar|7z|tar|gz|apk|exe|msi|txt|csv|json|xml|bin|dat|iso)(\?.*)?$/i.test(url);

    if (isDownloadOrInternal) {
      try {
        contents.downloadURL(url);
      } catch (e) {
        if (ses && typeof ses.downloadURL === "function") {
          ses.downloadURL(url);
        }
      }
      return { action: "deny" };
    }

    // External web link -> open in OS browser
    shell.openExternal(url);
    return { action: "deny" };
  });
});

// Second instance focus
app.on("second-instance", () => {
  if (mainWindow) {
    if (mainWindow.isMinimized()) mainWindow.restore();
    if (!mainWindow.isVisible()) mainWindow.show();
    mainWindow.focus();
  }
});

app.whenReady().then(() => {
  registerIpcHandlers({
    activeDownloads,
    getMainWindow: () => mainWindow,
    getTray: () => tray
  });
  createWindow();
  setupTray();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("before-quit", () => {
  isQuitting = true;
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});
