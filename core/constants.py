import hashlib
import datetime
import os
import sys
import json
import winreg
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, Any


# ─────────────────────────────────────────────
# Версия и константы
# ─────────────────────────────────────────────
APP_VERSION = "2.5.0"
APP_NAME = "MAX Desktop"


def resource_path(relative_path: str) -> str:
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def get_app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent


def get_windows_downloads_folder() -> str:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders") as key:
            downloads_path, _ = winreg.QueryValueEx(key, "{374DE290-123F-4565-9164-39C4925E467B}")
            if os.path.exists(downloads_path):
                return downloads_path
    except Exception:
        pass
    return str(Path.home() / "Downloads")


CONFIG_FILE = get_app_dir() / "config.json"
WINDOW_STATE_FILE = get_app_dir() / ".window_state.json"
DEFAULT_PROXY = {"type": "Нет", "host": "", "port": ""}


# Цветовая палитра приложения
class Colors:
    # Основные фоны
    BG_DARKEST = "#0a0e14"
    BG_DARKER = "#0f1923"
    BG_DARK = "#141e2b"
    BG_PRIMARY = "#1a2332"
    BG_SECONDARY = "#1f2b3d"
    BG_ELEVATED = "#243147"
    BG_HOVER = "#2a3a52"

    # Акценты
    ACCENT = "#6c7bf2"
    ACCENT_HOVER = "#5865f2"
    ACCENT_ACTIVE = "#4752c4"
    ACCENT_GLOW = "rgba(108, 123, 242, 0.15)"
    ACCENT_GRADIENT_START = "#6c7bf2"
    ACCENT_GRADIENT_END = "#8b5cf6"

    # Текст
    TEXT_PRIMARY = "#e8edf3"
    TEXT_SECONDARY = "#8899aa"
    TEXT_MUTED = "#5c6e80"

    # Состояния
    SUCCESS = "#34d399"
    SUCCESS_HOVER = "#10b981"
    DANGER = "#f87171"
    DANGER_HOVER = "#ef4444"
    WARNING = "#fbbf24"

    # Границы
    BORDER = "#1e2d40"
    BORDER_HOVER = "#2a3f5a"

    # Прозрачные оверлеи
    OVERLAY = "rgba(10, 14, 20, 0.85)"
    GLASS = "rgba(26, 35, 50, 0.65)"


# Глобальный стиль QToolTip
GLOBAL_TOOLTIP_STYLE = f"""
    QToolTip {{
        background-color: {Colors.BG_ELEVATED};
        color: {Colors.TEXT_PRIMARY};
        border: 1px solid {Colors.BORDER_HOVER};
        border-radius: 8px;
        padding: 8px 12px;
        font-size: 12px;
        font-family: 'Segoe UI', system-ui, sans-serif;
    }}
"""


# ─────────────────────────────────────────────
# Утилиты
# ─────────────────────────────────────────────
def safe_dir_name(name: str) -> str:
    cleaned = "".join(
        c if c.isalnum() or c in ("-", "_", " ") else "_"
        for c in name.strip()
    ).strip()
    return cleaned or "profile"


def profile_storage_id(name: str) -> str:
    return hashlib.sha1(name.encode("utf-8")).hexdigest()[:16]


def unique_path(directory: Path, filename: str) -> Path:
    target = directory / filename
    if not target.exists():
        return target

    stem = target.stem
    suffix = target.suffix
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    return directory / f"{stem}_{timestamp}{suffix}"


# ─────────────────────────────────────────────
# Маски устройств
# ─────────────────────────────────────────────
@dataclass
class DeviceMask:
    ua: str
    platform: str
    vendor: str
    renderer: str
    touch: int
    width: int
    height: int
    timezone: str
    locale: str

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__


MASKS_DB = {
    "Windows 11 (Chrome)": DeviceMask(
        ua="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        platform="Win32",
        vendor="Google Inc.",
        renderer="ANGLE (NVIDIA, RTX 3060, D3D11)",
        touch=0,
        width=1920,
        height=1080,
        timezone="Europe/Moscow",
        locale="ru-RU"
    ),
    "macOS (Safari)": DeviceMask(
        ua="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        platform="MacIntel",
        vendor="Apple Computer, Inc.",
        renderer="Apple GPU",
        touch=0,
        width=2560,
        height=1600,
        timezone="Europe/London",
        locale="en-GB"
    ),
    "Linux (Firefox)": DeviceMask(
        ua="Mozilla/5.0 (X11; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",
        platform="Linux x86_64",
        vendor="Mozilla",
        renderer="Mesa",
        touch=0,
        width=1920,
        height=1080,
        timezone="Europe/Moscow",
        locale="ru-RU"
    )
}


# ─────────────────────────────────────────────
# Темы для веб-контента
# ─────────────────────────────────────────────
THEMES = {
    "MAX Original": "",
    "Telegram Dark": """
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
    """,
    "AMOLED Black": """
        body, .main-container, .sidebar, .chat-list, .message-item, .app-container {
            background-color: #000000 !important;
            color: #ffffff !important;
        }
        .message-in, .incoming-message { background-color: #111111 !important; }
        .message-out, .outgoing-message { background-color: #1e1e1e !important; }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-thumb { background: #333333; border-radius: 3px; }
        ::-webkit-scrollbar-track { background: transparent; }
    """,
    "Nord": """
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
    """,
    "Monokai": """
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
    """
}


# ─────────────────────────────────────────────
# HTML для оффлайн-режима
# ─────────────────────────────────────────────
OFFLINE_HTML = """
<!DOCTYPE html>
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
</html>
"""
