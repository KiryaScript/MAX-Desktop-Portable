const os = require("os");
const fs = require("fs");
const path = require("path");
const { screen, shell } = require("electron");
const { APP_NAME, APP_VERSION } = require("./constants");
const { getAppDir } = require("./config");

function getDiagnosticsReport(configData, activeProfile, activeUserAgent) {
  const lines = [];
  const now = new Date();
  const dateStr = now.toISOString().replace(/T/, " ").replace(/\..+/, "");

  lines.push(`=== ${APP_NAME} v${APP_VERSION} — Diagnostic Report ===`);
  lines.push(`Дата создания: ${dateStr}`);

  lines.push("\n--- СИСТЕМА ---");
  lines.push(`ОС: ${os.type()} ${os.release()} (Версия: ${os.version ? os.version() : "N/A"})`);
  lines.push(`Платформа: ${os.platform()}`);
  lines.push(`Архитектура: ${os.arch()}`);
  lines.push(`Node.js: ${process.versions.node}`);
  lines.push(`Electron: ${process.versions.electron}`);
  lines.push(`Chromium: ${process.versions.chrome}`);

  lines.push("\n--- ЖЕЛЕЗО ---");
  const cpus = os.cpus();
  const cpuModel = cpus && cpus.length > 0 ? cpus[0].model : "N/A";
  lines.push(`Процессор: ${cpuModel}`);
  lines.push(`Количество ядер: ${cpus.length}`);

  const totalRamGb = (os.totalmem() / (1024 ** 3)).toFixed(1);
  const freeRamGb = (os.freemem() / (1024 ** 3)).toFixed(1);
  lines.push(`Оперативная память: ${totalRamGb} ГБ (Доступно: ${freeRamGb} ГБ)`);

  try {
    const primaryDisplay = screen.getPrimaryDisplay();
    if (primaryDisplay && primaryDisplay.size) {
      lines.push(`Разрешение экрана: ${primaryDisplay.size.width}x${primaryDisplay.size.height} (Scale: ${primaryDisplay.scaleFactor})`);
    }
  } catch (e) {
    lines.push("Разрешение экрана: недоступно");
  }

  lines.push("\n--- ПРИЛОЖЕНИЕ ---");
  lines.push(`Рабочая папка: ${getAppDir()}`);
  lines.push(`Активный профиль: ${activeProfile || "N/A"}`);
  if (activeUserAgent) {
    lines.push(`UserAgent: ${activeUserAgent}`);
  }

  lines.push("\n=== APP CONFIGURATION (JSON) ===");
  lines.push(JSON.stringify(configData, null, 4));

  return lines.join("\n");
}

async function createAndOpenSupportReport(configData, activeProfile, activeUserAgent) {
  const content = getDiagnosticsReport(configData, activeProfile, activeUserAgent);
  
  let desktopDir = path.join(os.homedir(), "Desktop");
  if (!fs.existsSync(desktopDir)) {
    desktopDir = os.homedir();
  }

  const reportPath = path.join(desktopDir, "MAX_Support_Report.txt");
  fs.writeFileSync(reportPath, content, "utf8");

  // Open Telegram developer chat
  try {
    await shell.openExternal("https://t.me/devjijlk");
  } catch (e) {
    console.warn("Could not open telegram url:", e);
  }

  return reportPath;
}

module.exports = {
  getDiagnosticsReport,
  createAndOpenSupportReport
};
