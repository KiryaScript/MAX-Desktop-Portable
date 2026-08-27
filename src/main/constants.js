const APP_VERSION = "2.5.0";
const APP_NAME = "MAX Desktop";
const DEFAULT_URL = "https://web.max.ru/login";

const Colors = {
  BG_DARKEST: "#0a0e14",
  BG_DARKER: "#0f1923",
  BG_DARK: "#141e2b",
  BG_PRIMARY: "#1a2332",
  BG_SECONDARY: "#1f2b3d",
  BG_ELEVATED: "#243147",
  BG_HOVER: "#2a3a52",

  ACCENT: "#6c7bf2",
  ACCENT_HOVER: "#5865f2",
  ACCENT_ACTIVE: "#4752c4",
  ACCENT_GLOW: "rgba(108, 123, 242, 0.15)",
  ACCENT_GRADIENT_START: "#6c7bf2",
  ACCENT_GRADIENT_END: "#8b5cf6",

  TEXT_PRIMARY: "#e8edf3",
  TEXT_SECONDARY: "#8899aa",
  TEXT_MUTED: "#5c6e80",

  SUCCESS: "#34d399",
  SUCCESS_HOVER: "#10b981",
  DANGER: "#f87171",
  DANGER_HOVER: "#ef4444",
  WARNING: "#fbbf24",

  BORDER: "#1e2d40",
  BORDER_HOVER: "#2a3f5a",
  OVERLAY: "rgba(10, 14, 20, 0.85)",
  GLASS: "rgba(26, 35, 50, 0.65)"
};

const MASKS_DB = {
  "Windows 11 (Chrome)": {
    ua: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    platform: "Win32",
    vendor: "Google Inc.",
    renderer: "ANGLE (NVIDIA, RTX 3060, D3D11)",
    touch: 0,
    width: 1920,
    height: 1080,
    timezone: "Europe/Moscow",
    locale: "ru-RU"
  },
  "macOS (Safari)": {
    ua: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    platform: "MacIntel",
    vendor: "Apple Computer, Inc.",
    renderer: "Apple GPU",
    touch: 0,
    width: 2560,
    height: 1600,
    timezone: "Europe/London",
    locale: "en-GB"
  },
  "Linux (Firefox)": {
    ua: "Mozilla/5.0 (X11; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",
    platform: "Linux x86_64",
    vendor: "Mozilla",
    renderer: "Mesa",
    touch: 0,
    width: 1920,
    height: 1080,
    timezone: "Europe/Moscow",
    locale: "ru-RU"
  }
};

const THEMES = {
  "MAX Original": "",
  "Telegram Dark": `
    :root {
        --tg-theme-bg-color: #17212b !important;
        --tg-theme-secondary-bg-color: #0e1621 !important;
        --tg-theme-text-color: #ffffff !important;
        --tg-theme-hint-color: #8b9fad !important;
        --tg-theme-link-color: #5865f2 !important;
        --tg-theme-button-color: #5865f2 !important;
        --tg-theme-bottom-bar-bg-color: #17212b !important;
        --tg-theme-accent-text-color: #ffffff !important;
        --tg-theme-section-bg-color: #17212b !important;
        --tg-theme-header-bg-color: #17212b !important;
        --tg-theme-subtitle-text-color: #8b9fad !important;
        --tg-theme-destructive-text-color: #e81123 !important;
    }
    body, .main-container, .sidebar, .chat-list, .message-item, .app-container {
        background-color: #17212b !important;
        color: #ffffff !important;
    }
    .message-in, .incoming-message { background-color: #182533 !important; }
    .message-out, .outgoing-message { background-color: #2b5278 !important; }
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-thumb { background: #2b5278; border-radius: 3px; }
    ::-webkit-scrollbar-track { background: transparent; }
    input, textarea, .search-bar {
        background-color: #232e3c !important;
        color: #ffffff !important;
        border: 1px solid #2b5278 !important;
    }
  `,
  "AMOLED Black": `
    body, .main-container, .sidebar, .chat-list, .message-item, .app-container {
        background-color: #000000 !important;
        color: #ffffff !important;
    }
    .message-in, .incoming-message { background-color: #111111 !important; }
    .message-out, .outgoing-message { background-color: #1e1e1e !important; }
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-thumb { background: #333333; border-radius: 3px; }
    ::-webkit-scrollbar-track { background: transparent; }
  `,
  "Nord": `
    body, .main-container, .sidebar, .chat-list, .message-item, .app-container {
        background-color: #2e3440 !important;
        color: #eceff4 !important;
    }
    .message-in, .incoming-message { background-color: #3b4252 !important; }
    .message-out, .outgoing-message { background-color: #434c5e !important; }
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-thumb { background: #4c566a; border-radius: 3px; }
    ::-webkit-scrollbar-track { background: transparent; }
    input, textarea, .search-bar {
        background-color: #3b4252 !important;
        color: #eceff4 !important;
        border: 1px solid #4c566a !important;
    }
  `,
  "Monokai": `
    body, .main-container, .sidebar, .chat-list, .message-item, .app-container {
        background-color: #272822 !important;
        color: #f8f8f2 !important;
    }
    .message-in, .incoming-message { background-color: #3e3d32 !important; }
    .message-out, .outgoing-message { background-color: #49483e !important; }
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-thumb { background: #75715e; border-radius: 3px; }
    ::-webkit-scrollbar-track { background: transparent; }
    input, textarea, .search-bar {
        background-color: #3e3d32 !important;
        color: #f8f8f2 !important;
        border: 1px solid #75715e !important;
    }
  `
};

const OFFLINE_HTML = `<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: linear-gradient(135deg, #0a0e14 0%, #141e2b 50%, #0f1923 100%);
            color: #8899aa;
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
            text-align: center;
            overflow: hidden;
            user-select: none;
        }
        .container {
            max-width: 460px;
            padding: 48px;
            background: rgba(26, 35, 50, 0.6);
            border: 1px solid rgba(108, 123, 242, 0.15);
            border-radius: 24px;
            backdrop-filter: blur(20px);
            animation: fadeInUp 0.6s ease-out;
        }
        @keyframes fadeInUp {
            from { opacity: 0; transform: translateY(30px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .icon {
            width: 80px; height: 80px; margin: 0 auto 24px;
            background: linear-gradient(135deg, rgba(108,123,242,0.2), rgba(139,92,246,0.2));
            border-radius: 20px;
            display: flex; align-items: center; justify-content: center;
            font-size: 40px;
            animation: pulse 2s ease-in-out infinite;
        }
        @keyframes pulse {
            0%, 100% { transform: scale(1); opacity: 1; }
            50% { transform: scale(1.05); opacity: 0.8; }
        }
        h1 { color: #e8edf3; font-size: 22px; font-weight: 700; margin-bottom: 12px; }
        p { font-size: 14px; line-height: 1.7; color: #8899aa; }
        .dots { display: flex; gap: 6px; justify-content: center; margin-top: 28px; }
        .dots span {
            width: 8px; height: 8px; border-radius: 50%; background: #6c7bf2;
            animation: dotPulse 1.4s ease-in-out infinite;
        }
        .dots span:nth-child(2) { animation-delay: 0.2s; }
        .dots span:nth-child(3) { animation-delay: 0.4s; }
        @keyframes dotPulse {
            0%, 100% { opacity: 0.3; transform: scale(0.8); }
            50% { opacity: 1; transform: scale(1.2); }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">📡</div>
        <h1>Ожидание подключения</h1>
        <p>Нет подключения к интернету.<br>Приложение автоматически восстановит связь,<br>когда появится сеть.</p>
        <div class="dots"><span></span><span></span><span></span></div>
    </div>
</body>
</html>`;

const DEFAULT_PROXY = {
  type: "Нет",
  host: "",
  port: ""
};

const DEFAULT_PROFILE_CONFIG = {
  mask: "Windows 11 (Chrome)",
  theme: "Telegram Dark",
  zoom: "100%",
  webrtc_leak: false,
  canvas_noise: true,
  audio_noise: true,
  adblock: false,
  mute_audio: false,
  hide_scrollbars: false,
  proxy: { ...DEFAULT_PROXY }
};

const DEFAULT_APP_CONFIG = {
  global: {
    close_to_tray: true,
    save_window_state: true,
    download_path: "",
    proxy: { ...DEFAULT_PROXY }
  },
  profiles: {
    "Основной аккаунт": { ...DEFAULT_PROFILE_CONFIG }
  }
};

const AVATAR_COLORS = [
  ["#6c7bf2", "#8b5cf6"],
  ["#34d399", "#10b981"],
  ["#f87171", "#ef4444"],
  ["#fbbf24", "#f59e0b"],
  ["#60a5fa", "#3b82f6"],
  ["#f472b6", "#ec4899"],
  ["#a78bfa", "#8b5cf6"],
  ["#2dd4bf", "#14b8a6"]
];

module.exports = {
  APP_NAME,
  APP_VERSION,
  DEFAULT_URL,
  Colors,
  MASKS_DB,
  THEMES,
  OFFLINE_HTML,
  DEFAULT_PROXY,
  DEFAULT_PROFILE_CONFIG,
  DEFAULT_APP_CONFIG,
  AVATAR_COLORS
};
