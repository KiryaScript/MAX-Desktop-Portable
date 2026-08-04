import os
import json

from PyQt6.QtNetwork import QNetworkProxy
from PyQt6.QtWebEngineCore import QWebEngineSettings

from core.constants import CONFIG_FILE, DEFAULT_PROXY


def apply_startup_proxy_env():
    """
    QtWebEngine/Chromium лучше всего подхватывает прокси через
    QTWEBENGINE_CHROMIUM_FLAGS до создания QApplication.
    """
    try:
        if not CONFIG_FILE.exists():
            return

        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        proxy = data.get("global", {}).get("proxy", {})
        ptype = proxy.get("type", "Нет")
        host = str(proxy.get("host", "")).strip()
        port = str(proxy.get("port", "")).strip()

        if ptype != "Нет" and host and port.isdigit():
            scheme = "socks5" if ptype == "SOCKS5" else "http"
            proxy_server = f"{scheme}://{host}:{port}"

            flags = os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "").strip()
            if "--proxy-server=" not in flags:
                flags = f"{flags} --proxy-server={proxy_server}".strip()
                os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = flags

    except Exception:
        pass


def apply_qt_proxy(proxy_cfg: dict):
    """
    Глобальный Qt-прокси. Он не всегда полностью покрывает Chromium,
    поэтому выше есть apply_startup_proxy_env.
    """
    try:
        proxy_cfg = proxy_cfg or {}
        ptype = proxy_cfg.get("type", "Нет")
        host = str(proxy_cfg.get("host", "")).strip()
        port_text = str(proxy_cfg.get("port", "")).strip()

        if ptype != "Нет" and host and port_text.isdigit():
            proxy_type = (
                QNetworkProxy.ProxyType.HttpProxy
                if ptype == "HTTP"
                else QNetworkProxy.ProxyType.Socks5Proxy
            )
            QNetworkProxy.setApplicationProxy(
                QNetworkProxy(proxy_type, host, int(port_text))
            )
        else:
            QNetworkProxy.setApplicationProxy(
                QNetworkProxy(QNetworkProxy.ProxyType.NoProxy)
            )
    except Exception:
        pass


def safe_set_web_setting(settings, attr_name: str, value: bool):
    if not settings:
        return
    try:
        attr = getattr(QWebEngineSettings.WebAttribute, attr_name)
        settings.setAttribute(attr, value)
    except Exception:
        pass
