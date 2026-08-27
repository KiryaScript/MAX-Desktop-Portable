const fs = require("fs");
const path = require("path");
const os = require("os");
const crypto = require("crypto");
const { app } = require("electron");
const { DEFAULT_APP_CONFIG, DEFAULT_PROFILE_CONFIG } = require("./constants");

function getAppDir() {
  if (process.env.PORTABLE_EXECUTABLE_DIR) {
    return process.env.PORTABLE_EXECUTABLE_DIR;
  }
  if (app && app.isPackaged) {
    return path.dirname(process.execPath);
  }
  return path.resolve(__dirname, "../../");
}

function getConfigFile() {
  return path.join(getAppDir(), "config.json");
}

function getWindowStateFile() {
  return path.join(getAppDir(), ".window_state.json");
}

function getDownloadsFolder(customPath) {
  if (customPath && typeof customPath === "string" && customPath.trim()) {
    const trimmed = customPath.trim();
    if (fs.existsSync(trimmed)) {
      return trimmed;
    }
  }
  return path.join(os.homedir(), "Downloads");
}

function profileStorageId(name) {
  return crypto.createHash("sha1").update(String(name || "").trim(), "utf8").digest("hex").slice(0, 16);
}

function migrateConfig(data) {
  const cfg = data || {};
  if (!cfg.global || typeof cfg.global !== "object") {
    cfg.global = { ...DEFAULT_APP_CONFIG.global };
  }
  if (!cfg.profiles || typeof cfg.profiles !== "object") {
    cfg.profiles = {};
  }

  cfg.global.close_to_tray = cfg.global.close_to_tray !== false;
  cfg.global.save_window_state = cfg.global.save_window_state !== false;
  if (!cfg.global.proxy || typeof cfg.global.proxy !== "object") {
    cfg.global.proxy = { type: "Нет", host: "", port: "" };
  }
  if (typeof cfg.global.download_path !== "string") {
    cfg.global.download_path = "";
  }

  const oldThemeMap = {
    "Стандартная": "MAX Original",
    "Темная (Telegram)": "Telegram Dark",
    "AMOLED Черная": "AMOLED Black"
  };

  for (const [pName, profile] of Object.entries(cfg.profiles)) {
    if (profile && typeof profile === "object") {
      if (profile.theme && oldThemeMap[profile.theme]) {
        profile.theme = oldThemeMap[profile.theme];
      }
      for (const [key, val] of Object.entries(DEFAULT_PROFILE_CONFIG)) {
        if (profile[key] === undefined) {
          profile[key] = typeof val === "object" ? JSON.parse(JSON.stringify(val)) : val;
        }
      }
    }
  }

  if (Object.keys(cfg.profiles).length === 0) {
    cfg.profiles["Основной аккаунт"] = JSON.parse(JSON.stringify(DEFAULT_PROFILE_CONFIG));
  }

  return cfg;
}

function loadConfig() {
  const configFile = getConfigFile();
  try {
    if (fs.existsSync(configFile)) {
      const raw = fs.readFileSync(configFile, "utf8");
      const parsed = JSON.parse(raw);
      const migrated = migrateConfig(parsed);
      saveConfig(migrated);
      return migrated;
    }
  } catch (err) {
    console.error("Failed to load config, initializing default:", err);
  }

  const defaultCfg = JSON.parse(JSON.stringify(DEFAULT_APP_CONFIG));
  saveConfig(defaultCfg);
  return defaultCfg;
}

function saveConfig(configData) {
  const configFile = getConfigFile();
  try {
    const dir = path.dirname(configFile);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    fs.writeFileSync(configFile, JSON.stringify(configData, null, 4), "utf8");
    return true;
  } catch (err) {
    console.error("Failed to save config:", err);
    return false;
  }
}

function loadWindowState() {
  const file = getWindowStateFile();
  try {
    if (fs.existsSync(file)) {
      const raw = fs.readFileSync(file, "utf8");
      return JSON.parse(raw);
    }
  } catch (e) {
    // Ignore error
  }
  return null;
}

function saveWindowState(state) {
  const file = getWindowStateFile();
  try {
    fs.writeFileSync(file, JSON.stringify(state, null, 2), "utf8");
  } catch (e) {
    // Ignore error
  }
}

module.exports = {
  getAppDir,
  getConfigFile,
  getWindowStateFile,
  getDownloadsFolder,
  profileStorageId,
  loadConfig,
  saveConfig,
  loadWindowState,
  saveWindowState
};
