// MAX Desktop Renderer Controller
(async function() {
  const { api } = window;
  if (!api) {
    console.error("Electron API bridge is not available.");
    return;
  }

  // Load state & configuration from Main Process
  let config = await api.getConfig();
  const appInfo = await api.getAppInfo();
  const masksDb = await api.getMasks();
  const themesDb = await api.getThemes();
  const avatarColors = await api.getAvatarColors();
  const stealthPreloadPath = await api.getStealthPreloadPath();

  let activeProfileName = Object.keys(config.profiles)[0] || "Основной аккаунт";
  const webviews = new Map(); // profileName -> webview DOM element
  let activeDownloadId = null;

  // DOM Elements
  const appVersionTag = document.getElementById("app-version-tag");
  const settingsVersionTag = document.getElementById("settings-version-tag");
  const supportMetaInfo = document.getElementById("support-meta-info");

  const activeProfileNameEl = document.getElementById("active-profile-name");
  const connectionDot = document.getElementById("connection-dot");

  const winBtnMin = document.getElementById("win-btn-min");
  const winBtnMax = document.getElementById("win-btn-max");
  const winBtnClose = document.getElementById("win-btn-close");
  const maxIconSvg = document.getElementById("max-icon-svg");

  const sidebarProfiles = document.getElementById("sidebar-profiles");
  const btnAddProfile = document.getElementById("btn-add-profile");
  const btnOpenSettings = document.getElementById("btn-open-settings");

  const browserContainer = document.getElementById("browser-container");
  const offlineScreen = document.getElementById("offline-screen");
  const btnOfflineRetry = document.getElementById("btn-offline-retry");

  const downloadPanel = document.getElementById("download-panel");
  const dlFilename = document.getElementById("dl-filename");
  const dlStats = document.getElementById("dl-stats");
  const dlProgressFill = document.getElementById("dl-progress-fill");
  const btnCancelDl = document.getElementById("btn-cancel-dl");

  // Modals
  const settingsModal = document.getElementById("settings-modal");
  const btnCloseSettings = document.getElementById("btn-close-settings");
  const btnSettingsCancel = document.getElementById("btn-settings-cancel");
  const btnSettingsSave = document.getElementById("btn-settings-save");

  const shortcutsModal = document.getElementById("shortcuts-modal");
  const btnCloseShortcuts = document.getElementById("btn-close-shortcuts");

  const promptModal = document.getElementById("prompt-modal");
  const promptInput = document.getElementById("prompt-input");
  const btnPromptClose = document.getElementById("btn-prompt-close");
  const btnPromptCancel = document.getElementById("btn-prompt-cancel");
  const btnPromptOk = document.getElementById("btn-prompt-ok");

  const confirmModal = document.getElementById("confirm-modal");
  const confirmMessage = document.getElementById("confirm-message");
  const btnConfirmClose = document.getElementById("btn-confirm-close");
  const btnConfirmCancel = document.getElementById("btn-confirm-cancel");
  const btnConfirmOk = document.getElementById("btn-confirm-ok");

  // Settings form elements
  const settingsProfileSelect = document.getElementById("settings-profile-select");
  const btnSettingsAddProfile = document.getElementById("btn-settings-add-profile");
  const btnSettingsDeleteProfile = document.getElementById("btn-settings-delete-profile");
  const settingsMaskSelect = document.getElementById("settings-mask-select");
  const settingsCbWebrtc = document.getElementById("settings-cb-webrtc");
  const settingsCbCanvas = document.getElementById("settings-cb-canvas");
  const settingsCbAudio = document.getElementById("settings-cb-audio");
  const settingsCbAdblock = document.getElementById("settings-cb-adblock");
  const settingsProxyType = document.getElementById("settings-proxy-type");
  const settingsProxyHost = document.getElementById("settings-proxy-host");
  const settingsProxyPort = document.getElementById("settings-proxy-port");
  const settingsThemeSelect = document.getElementById("settings-theme-select");
  const settingsZoomSelect = document.getElementById("settings-zoom-select");
  const settingsCbScrollbars = document.getElementById("settings-cb-scrollbars");
  const settingsCbMute = document.getElementById("settings-cb-mute");
  const settingsCbTray = document.getElementById("settings-cb-tray");
  const settingsCbSavewindow = document.getElementById("settings-cb-savewindow");
  const settingsDownloadPath = document.getElementById("settings-download-path");
  const btnBrowseDownloads = document.getElementById("btn-browse-downloads");
  const btnClearCache = document.getElementById("btn-clear-cache");
  const btnOpenDownloads = document.getElementById("btn-open-downloads");
  const btnOpenAppdir = document.getElementById("btn-open-appdir");
  const btnGenerateReport = document.getElementById("btn-generate-report");

  // Initialize version strings
  if (appVersionTag) appVersionTag.textContent = `v${appInfo.version}`;
  if (settingsVersionTag) settingsVersionTag.textContent = `v${appInfo.version}`;
  if (supportMetaInfo) {
    supportMetaInfo.innerHTML = `
      ${appInfo.name} v${appInfo.version}<br>
      Node.js ${appInfo.node || "24.x"} | Chromium ${appInfo.chrome || "134.x"}<br>
      ${appInfo.os || "Windows NT"}
    `;
  }

  // ── Window Controls & Maximize State ──

  const SVG_MAXIMIZE = `<path d="M0,0v10h10V0H0z M9,9H1V1h8V9z" fill="currentColor"/>`;
  const SVG_RESTORE = `<path d="M2,0v2H0v8h8V8h2V0H2z M7,9H1V3h6V9z M9,7H8V2H3V1h6V7z" fill="currentColor"/>`;

  function updateMaximizeButton(isMaximized) {
    if (!maxIconSvg || !winBtnMax) return;
    if (isMaximized) {
      maxIconSvg.innerHTML = SVG_RESTORE;
      winBtnMax.title = "Восстановить";
    } else {
      maxIconSvg.innerHTML = SVG_MAXIMIZE;
      winBtnMax.title = "Развернуть";
    }
  }

  const isInitiallyMaximized = await api.isMaximized();
  updateMaximizeButton(isInitiallyMaximized);

  api.onMaximizeChanged((isMaximized) => {
    updateMaximizeButton(isMaximized);
  });

  winBtnMin.addEventListener("click", () => api.windowAction("minimize"));
  winBtnMax.addEventListener("click", () => api.windowAction("maximize"));
  winBtnClose.addEventListener("click", () => api.windowAction("close"));

  // ── Webview Creation & Management ──

  async function getStealthConfig(profileName) {
    const pConfig = config.profiles[profileName] || {};
    const mask = masksDb[pConfig.mask] || masksDb["Windows 11 (Chrome)"];
    const themeCss = themesDb[pConfig.theme] || "";
    let fullCss = themeCss;

    if (pConfig.hide_scrollbars) {
      fullCss += "\n::-webkit-scrollbar { display: none !important; }";
    }
    if (pConfig.adblock) {
      fullCss += `
        .ads, .advertisement, [id*='yandex_rtb'], .banner, [class*='adsbygoogle'], [id*='ad-container'] {
            display: none !important;
            visibility: hidden !important;
            opacity: 0 !important;
            pointer-events: none !important;
        }
      `;
    }

    return {
      maskData: mask,
      webrtc_leak: Boolean(pConfig.webrtc_leak),
      canvas_noise: pConfig.canvas_noise !== false,
      audio_noise: pConfig.audio_noise !== false,
      css: fullCss
    };
  }

  async function createWebview(profileName) {
    if (webviews.has(profileName)) {
      return webviews.get(profileName);
    }

    const pid = await api.profileStorageId(profileName);
    const pConfig = config.profiles[profileName] || {};
    const webview = document.createElement("webview");

    webview.className = "webview-item hidden";
    webview.setAttribute("partition", `persist:profile_${pid}`);
    webview.setAttribute("preload", `file://${stealthPreloadPath.replace(/\\/g, "/")}`);
    webview.setAttribute("src", "https://web.max.ru/login");
    webview.setAttribute("webpreferences", "contextIsolation=yes, nodeIntegration=no");
    webview.setAttribute("allowpopups", "true");
    webview.setAttribute("allowfullscreen", "true");

    webview.addEventListener("did-start-loading", () => {
      if (activeProfileName === profileName) {
        setConnectionStatus(true);
      }
    });

    webview.addEventListener("did-stop-loading", async () => {
      try {
        const stealthCfg = await getStealthConfig(profileName);
        webview.send("apply-stealth-config", stealthCfg);
      } catch (e) {}
    });

    webview.addEventListener("did-fail-load", (event) => {
      if (event.errorCode !== -3) { // Ignore aborted loads
        if (activeProfileName === profileName) {
          setConnectionStatus(false);
          showOfflineScreen(true);
        }
      }
    });

    webview.addEventListener("did-navigate", () => {
      if (activeProfileName === profileName) {
        setConnectionStatus(true);
        showOfflineScreen(false);
      }
    });

    // Handle new-window / attachment downloads triggered via window.open
    webview.addEventListener("new-window", (e) => {
      const targetUrl = e.url;
      if (!targetUrl) return;

      const isDownloadOrInternal =
        targetUrl.startsWith("blob:") ||
        targetUrl.startsWith("data:") ||
        targetUrl.includes("max.ru") ||
        targetUrl.includes("storage") ||
        targetUrl.includes("download") ||
        targetUrl.includes("file") ||
        targetUrl.includes("attachment") ||
        targetUrl.includes("media") ||
        targetUrl.includes("get_file") ||
        targetUrl.includes("selcloud") ||
        targetUrl.includes("selcdn") ||
        targetUrl.includes("bizmrg") ||
        /\.(jpg|jpeg|png|gif|webp|svg|ico|bmp|mp4|webm|mov|avi|mkv|mp3|ogg|wav|m4a|aac|flac|pdf|doc|docx|xls|xlsx|ppt|pptx|zip|rar|7z|tar|gz|apk|exe|msi|txt|csv|json|xml|bin|dat|iso)(\?.*)?$/i.test(targetUrl);

      if (isDownloadOrInternal) {
        api.downloadUrl(profileName, targetUrl);
      } else {
        api.openExternal(targetUrl);
      }
    });

    webview.addEventListener("ipc-message", async (event) => {
      if (event.channel === "stealth-ready") {
        const stealthCfg = await getStealthConfig(profileName);
        webview.send("apply-stealth-config", stealthCfg);
      }
    });

    webview.addEventListener("dom-ready", async () => {
      try {
        const zoomText = String(pConfig.zoom || "100%").replace("%", "").trim();
        const zoomFactor = (parseFloat(zoomText) || 100) / 100;
        webview.setZoomFactor(zoomFactor);
      } catch (e) {}

      try {
        webview.setAudioMuted(Boolean(pConfig.mute_audio));
      } catch (e) {}

      const stealthCfg = await getStealthConfig(profileName);
      webview.send("apply-stealth-config", stealthCfg);
    });

    browserContainer.appendChild(webview);
    webviews.set(profileName, webview);
    return webview;
  }

  function getActiveWebview() {
    return webviews.get(activeProfileName);
  }

  function setConnectionStatus(connected) {
    if (connected) {
      connectionDot.className = "account-dot connected";
      connectionDot.title = "Подключено к сети";
    } else {
      connectionDot.className = "account-dot disconnected";
      connectionDot.title = "Нет подключения";
    }
  }

  function showOfflineScreen(show) {
    if (show) {
      offlineScreen.classList.remove("hidden");
    } else {
      offlineScreen.classList.add("hidden");
    }
  }

  // ── Profile Switching & Sidebar Rendering ──

  async function switchProfile(name) {
    if (!config.profiles[name]) return;
    activeProfileName = name;

    if (!webviews.has(name)) {
      await createWebview(name);
    }

    webviews.forEach((wv, pName) => {
      if (pName === name) {
        wv.classList.remove("hidden");
      } else {
        wv.classList.add("hidden");
      }
    });

    if (activeProfileNameEl) activeProfileNameEl.textContent = name;
    showOfflineScreen(false);

    renderSidebar();
  }

  function renderSidebar() {
    sidebarProfiles.innerHTML = "";
    const profileNames = Object.keys(config.profiles);

    profileNames.forEach((name, index) => {
      const colorPair = avatarColors[index % avatarColors.length];
      const initial = name.trim()[0] ? name.trim()[0].toUpperCase() : "M";

      const btn = document.createElement("button");
      btn.className = `profile-avatar-btn ${name === activeProfileName ? "active" : ""}`;
      btn.title = name;
      btn.textContent = initial;

      if (name === activeProfileName) {
        btn.style.background = `linear-gradient(135deg, ${colorPair[0]}, ${colorPair[1]})`;
        btn.style.color = "#ffffff";
      } else {
        btn.style.background = "var(--bg-secondary)";
        btn.style.color = "var(--text-secondary)";
      }

      btn.addEventListener("click", () => switchProfile(name));
      sidebarProfiles.appendChild(btn);
    });
  }

  // ── Modal Helpers ──

  let promptCallback = null;
  function showPrompt(title, label, defaultValue, cb) {
    document.getElementById("prompt-title").textContent = title;
    document.getElementById("prompt-label").textContent = label;
    promptInput.value = defaultValue || "";
    promptCallback = cb;
    promptModal.classList.remove("hidden");
    promptInput.focus();
  }

  function hidePrompt() {
    promptModal.classList.add("hidden");
    promptCallback = null;
  }

  btnPromptOk.addEventListener("click", () => {
    const val = promptInput.value.trim();
    if (val && promptCallback) {
      promptCallback(val);
    }
    hidePrompt();
  });

  btnPromptCancel.addEventListener("click", hidePrompt);
  btnPromptClose.addEventListener("click", hidePrompt);
  promptInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") btnPromptOk.click();
    if (e.key === "Escape") hidePrompt();
  });

  let confirmCallback = null;
  function showConfirm(title, message, cb) {
    document.getElementById("confirm-title").textContent = title;
    confirmMessage.textContent = message;
    confirmCallback = cb;
    confirmModal.classList.remove("hidden");
  }

  function hideConfirm() {
    confirmModal.classList.add("hidden");
    confirmCallback = null;
  }

  btnConfirmOk.addEventListener("click", () => {
    if (confirmCallback) confirmCallback();
    hideConfirm();
  });

  btnConfirmCancel.addEventListener("click", hideConfirm);
  btnConfirmClose.addEventListener("click", hideConfirm);

  // ── Profile Creation & Deletion ──

  async function addNewProfileFlow() {
    showPrompt("Новый аккаунт", "Название аккаунта:", "", async (name) => {
      if (!name) return;
      if (config.profiles[name]) {
        switchProfile(name);
        return;
      }

      const defaultProfile = {
        mask: "Windows 11 (Chrome)",
        theme: "Telegram Dark",
        zoom: "100%",
        webrtc_leak: false,
        canvas_noise: true,
        audio_noise: true,
        adblock: false,
        mute_audio: false,
        hide_scrollbars: false,
        proxy: config.global && config.global.proxy ? { ...config.global.proxy } : { type: "Нет", host: "", port: "" }
      };

      config.profiles[name] = defaultProfile;
      await api.saveConfig(config);
      await createWebview(name);
      renderSidebar();
      await switchProfile(name);
      showToast(`Аккаунт «${name}» добавлен`, "success", "✅");
    });
  }

  async function deleteProfileFlow(targetName) {
    const name = targetName || activeProfileName;
    const names = Object.keys(config.profiles);
    if (names.length <= 1) {
      showToast("Нельзя удалить единственный аккаунт.", "warning", "⚠️");
      return;
    }

    showConfirm(
      "Удалить аккаунт",
      `Удалить аккаунт «${name}»? Все данные и кэш будут удалены безвозвратно.`,
      async () => {
        const wv = webviews.get(name);
        if (wv) {
          wv.remove();
          webviews.delete(name);
        }

        delete config.profiles[name];
        await api.deleteProfileStorage(name);
        await api.saveConfig(config);

        const remaining = Object.keys(config.profiles);
        await switchProfile(remaining[0]);
        renderSidebar();
        populateSettingsDropdowns();
        showToast(`Аккаунт «${name}» удалён`, "info", "🗑");
      }
    );
  }

  // ── Settings Dialog Logic ──

  function populateSettingsDropdowns() {
    settingsProfileSelect.innerHTML = "";
    Object.keys(config.profiles).forEach(pName => {
      const opt = document.createElement("option");
      opt.value = pName;
      opt.textContent = pName;
      settingsProfileSelect.appendChild(opt);
    });
    settingsProfileSelect.value = activeProfileName;

    settingsMaskSelect.innerHTML = "";
    Object.keys(masksDb).forEach(mKey => {
      const opt = document.createElement("option");
      opt.value = mKey;
      opt.textContent = mKey;
      settingsMaskSelect.appendChild(opt);
    });

    settingsThemeSelect.innerHTML = "";
    Object.keys(themesDb).forEach(tKey => {
      const opt = document.createElement("option");
      opt.value = tKey;
      opt.textContent = tKey;
      settingsThemeSelect.appendChild(opt);
    });
  }

  function loadSettingsIntoForm() {
    populateSettingsDropdowns();

    const pConfig = config.profiles[activeProfileName] || {};
    const gConfig = config.global || {};
    const proxy = gConfig.proxy || pConfig.proxy || { type: "Нет", host: "", port: "" };

    settingsMaskSelect.value = pConfig.mask || "Windows 11 (Chrome)";
    settingsCbWebrtc.checked = Boolean(pConfig.webrtc_leak);
    settingsCbCanvas.checked = pConfig.canvas_noise !== false;
    settingsCbAudio.checked = pConfig.audio_noise !== false;
    settingsCbAdblock.checked = Boolean(pConfig.adblock);

    settingsProxyType.value = proxy.type || "Нет";
    settingsProxyHost.value = proxy.host || "";
    settingsProxyPort.value = proxy.port || "";

    settingsThemeSelect.value = pConfig.theme || "Telegram Dark";
    settingsZoomSelect.value = pConfig.zoom || "100%";
    settingsCbScrollbars.checked = Boolean(pConfig.hide_scrollbars);

    settingsCbMute.checked = Boolean(pConfig.mute_audio);
    settingsCbTray.checked = gConfig.close_to_tray !== false;
    settingsCbSavewindow.checked = gConfig.save_window_state !== false;
    settingsDownloadPath.value = gConfig.download_path || "";
  }

  function openSettingsModal() {
    loadSettingsIntoForm();
    settingsModal.classList.remove("hidden");
  }

  function closeSettingsModal() {
    settingsModal.classList.add("hidden");
  }

  // Settings Tabs Switcher
  document.querySelectorAll(".settings-tabs-header .tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".settings-tabs-header .tab-btn").forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".settings-tabs-content .tab-pane").forEach(p => p.classList.remove("active"));

      btn.classList.add("active");
      const targetId = btn.getAttribute("data-tab");
      const pane = document.getElementById(targetId);
      if (pane) pane.classList.add("active");
    });
  });

  settingsProfileSelect.addEventListener("change", () => {
    const selected = settingsProfileSelect.value;
    if (selected && config.profiles[selected]) {
      switchProfile(selected);
      loadSettingsIntoForm();
    }
  });

  btnSettingsAddProfile.addEventListener("click", () => {
    addNewProfileFlow();
  });

  btnSettingsDeleteProfile.addEventListener("click", () => {
    deleteProfileFlow(settingsProfileSelect.value);
  });

  btnBrowseDownloads.addEventListener("click", async () => {
    const picked = await api.browseFolder(settingsDownloadPath.value);
    if (picked) {
      settingsDownloadPath.value = picked;
    }
  });

  btnClearCache.addEventListener("click", async () => {
    const ok = await api.clearCache(activeProfileName);
    if (ok) {
      showToast("Кэш и данные аккаунта очищены.", "success", "🧹");
    } else {
      showToast("Ошибка при очистке кэша.", "danger", "✕");
    }
  });

  btnOpenDownloads.addEventListener("click", () => {
    api.openDownloadsFolder(settingsDownloadPath.value);
  });

  btnOpenAppdir.addEventListener("click", () => {
    api.openAppFolder();
  });

  btnGenerateReport.addEventListener("click", async () => {
    const webview = getActiveWebview();
    let ua = "";
    try {
      ua = await webview.executeJavaScript("navigator.userAgent");
    } catch(e) {}

    const reportPath = await api.createSupportReport(activeProfileName, ua);
    showToast(`Отчёт создан:\n${reportPath}`, "info", "🛠", 4000);
  });

  btnSettingsSave.addEventListener("click", async () => {
    const gConfig = config.global || {};
    gConfig.close_to_tray = settingsCbTray.checked;
    gConfig.save_window_state = settingsCbSavewindow.checked;
    gConfig.download_path = settingsDownloadPath.value.trim();

    const newProxy = {
      type: settingsProxyType.value,
      host: settingsProxyHost.value.trim(),
      port: settingsProxyPort.value.trim()
    };
    gConfig.proxy = newProxy;
    config.global = gConfig;

    const pConfig = config.profiles[activeProfileName] || {};
    pConfig.mask = settingsMaskSelect.value;
    pConfig.webrtc_leak = settingsCbWebrtc.checked;
    pConfig.canvas_noise = settingsCbCanvas.checked;
    pConfig.audio_noise = settingsCbAudio.checked;
    pConfig.adblock = settingsCbAdblock.checked;
    pConfig.theme = settingsThemeSelect.value;
    pConfig.zoom = settingsZoomSelect.value;
    pConfig.hide_scrollbars = settingsCbScrollbars.checked;
    pConfig.mute_audio = settingsCbMute.checked;
    pConfig.proxy = newProxy;

    config.profiles[activeProfileName] = pConfig;

    await api.saveConfig(config);
    await api.applyProfileSession(activeProfileName, pConfig);

    const webview = getActiveWebview();
    if (webview) {
      try {
        const zoomText = String(pConfig.zoom || "100%").replace("%", "").trim();
        const zoomFactor = (parseFloat(zoomText) || 100) / 100;
        webview.setZoomFactor(zoomFactor);
      } catch (e) {}

      try {
        webview.setAudioMuted(Boolean(pConfig.mute_audio));
      } catch (e) {}

      const stealthCfg = await getStealthConfig(activeProfileName);
      webview.send("apply-stealth-config", stealthCfg);
      try {
        webview.reload();
      } catch (e) {}
    }

    closeSettingsModal();
    showToast("Настройки успешно сохранены.", "success", "✓");
  });

  btnSettingsCancel.addEventListener("click", closeSettingsModal);
  btnCloseSettings.addEventListener("click", closeSettingsModal);

  // Offline Retry
  btnOfflineRetry.addEventListener("click", () => {
    const wv = getActiveWebview();
    if (wv) {
      showOfflineScreen(false);
      wv.reload();
    }
  });

  btnAddProfile.addEventListener("click", addNewProfileFlow);
  btnOpenSettings.addEventListener("click", openSettingsModal);

  // ── Download Handling ──

  api.onDownloadProgress((data) => {
    activeDownloadId = data.id;
    const mbRecv = (data.receivedBytes / (1024 * 1024)).toFixed(1);
    const mbTotal = (data.totalBytes / (1024 * 1024)).toFixed(1);

    dlFilename.textContent = `📥 ${data.filename}`;
    if (data.totalBytes > 0) {
      const pct = Math.min(100, Math.floor((data.receivedBytes / data.totalBytes) * 100));
      dlProgressFill.style.width = `${pct}%`;
      dlStats.textContent = `${pct}%  (${mbRecv} / ${mbTotal} МБ)`;
    } else {
      dlProgressFill.style.width = "100%";
      dlStats.textContent = `Скачано: ${mbRecv} МБ`;
    }
    downloadPanel.classList.remove("hidden");
  });

  api.onDownloadComplete((data) => {
    downloadPanel.classList.add("hidden");
    if (data.success) {
      showToast(`Файл сохранён: ${data.filename}`, "success", "✅", 4000);
    } else {
      showToast(`Ошибка загрузки: ${data.filename}`, "danger", "✕");
    }
  });

  btnCancelDl.addEventListener("click", () => {
    if (activeDownloadId) {
      api.cancelDownload(activeDownloadId);
      downloadPanel.classList.add("hidden");
      showToast("Загрузка отменена", "warning", "✕");
    }
  });

  // ── Toast System ──

  function showToast(message, type = "info", icon = "ℹ️", duration = 3000) {
    const container = document.getElementById("toast-container");
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;

    const iconSpan = document.createElement("span");
    iconSpan.className = "toast-icon";
    iconSpan.textContent = icon;

    const textSpan = document.createElement("span");
    textSpan.className = "toast-message";
    textSpan.textContent = message;

    toast.appendChild(iconSpan);
    toast.appendChild(textSpan);
    container.appendChild(toast);

    setTimeout(() => {
      toast.classList.add("fade-out");
      setTimeout(() => toast.remove(), 200);
    }, duration);
  }

  // ── Keyboard Shortcuts ──

  function showShortcutsModal() {
    shortcutsModal.classList.remove("hidden");
  }

  function closeShortcutsModal() {
    shortcutsModal.classList.add("hidden");
  }

  btnCloseShortcuts.addEventListener("click", closeShortcutsModal);

  window.addEventListener("keydown", (e) => {
    // Ctrl + T -> New Account
    if (e.ctrlKey && e.key.toLowerCase() === "t") {
      e.preventDefault();
      addNewProfileFlow();
    }
    // Ctrl + W -> Close window / Tray
    else if (e.ctrlKey && e.key.toLowerCase() === "w") {
      e.preventDefault();
      api.windowAction("close");
    }
    // Ctrl + R or F5 -> Reload Client
    else if ((e.ctrlKey && e.key.toLowerCase() === "r") || e.key === "F5") {
      e.preventDefault();
      const wv = getActiveWebview();
      if (wv) wv.reload();
    }
    // Ctrl + Shift + S -> Settings
    else if (e.ctrlKey && e.shiftKey && e.key.toLowerCase() === "s") {
      e.preventDefault();
      openSettingsModal();
    }
    // F1 -> Shortcuts
    else if (e.key === "F1") {
      e.preventDefault();
      showShortcutsModal();
    }
    // Escape -> Close any modal
    else if (e.key === "Escape") {
      closeSettingsModal();
      closeShortcutsModal();
      hidePrompt();
      hideConfirm();
    }
    // Ctrl + 1..9 -> Quick Switch Profile
    else if (e.ctrlKey && e.key >= "1" && e.key <= "9") {
      const idx = parseInt(e.key, 10) - 1;
      const names = Object.keys(config.profiles);
      if (idx >= 0 && idx < names.length) {
        e.preventDefault();
        switchProfile(names[idx]);
      }
    }
  });

  // Ctrl + Mouse Wheel Zoom
  window.addEventListener("wheel", (e) => {
    if (e.ctrlKey) {
      e.preventDefault();
      const wv = getActiveWebview();
      if (!wv) return;

      try {
        let currentZoom = wv.getZoomFactor() || 1.0;
        if (e.deltaY < 0) {
          currentZoom = Math.min(currentZoom + 0.1, 3.0);
        } else {
          currentZoom = Math.max(currentZoom - 0.1, 0.5);
        }
        wv.setZoomFactor(currentZoom);
      } catch (err) {}
    }
  }, { passive: false });

  // Handle Tray events
  api.onOpenSettings(() => {
    openSettingsModal();
  });

  // ── Initial Setup ──
  const profileNames = Object.keys(config.profiles);
  if (profileNames.length === 0) {
    config.profiles["Основной аккаунт"] = {
      mask: "Windows 11 (Chrome)",
      theme: "Telegram Dark",
      zoom: "100%",
      webrtc_leak: false,
      canvas_noise: true,
      audio_noise: true,
      adblock: false,
      mute_audio: false,
      hide_scrollbars: false,
      proxy: { type: "Нет", host: "", port: "" }
    };
    await api.saveConfig(config);
  }

  // Create webview for initial profile and switch to it
  await createWebview(activeProfileName);
  renderSidebar();
  await switchProfile(activeProfileName);

  // Pre-instantiate other webviews in background
  for (const name of Object.keys(config.profiles)) {
    if (name !== activeProfileName) {
      createWebview(name);
    }
  }

})();
