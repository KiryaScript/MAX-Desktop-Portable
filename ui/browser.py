import os
import json
import mimetypes
import time
from pathlib import Path

from PyQt6.QtCore import QUrl, Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QMainWindow, QProgressBar, QSystemTrayIcon
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import (
    QWebEngineProfile, QWebEngineScript, QWebEnginePage
)

try:
    from PyQt6.QtWebEngineCore import QWebEngineDownloadRequest
except ImportError:
    QWebEngineDownloadRequest = None

from core.constants import (
    APP_NAME, Colors, MASKS_DB, THEMES, OFFLINE_HTML,
    resource_path, get_app_dir, profile_storage_id, unique_path,
    get_windows_downloads_folder, CONFIG_FILE
)
from core.network import apply_qt_proxy, safe_set_web_setting


class CustomWebView(QWebEngineView):
    """WebView с поддержкой Ctrl+Scroll зума."""

    def wheelEvent(self, event):
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            current_zoom = self.zoomFactor()
            if delta > 0:
                self.setZoomFactor(min(current_zoom + 0.1, 3.0))
            else:
                self.setZoomFactor(max(current_zoom - 0.1, 0.5))
            event.accept()
        else:
            super().wheelEvent(event)


class CustomWebPage(QWebEnginePage):
    """Страница с поддержкой popup-окон."""

    def __init__(self, profile, parent=None):
        super().__init__(profile, parent)
        self._popups = []
        self.created_at = time.time()
        self.is_loaded = False
        self.loadFinished.connect(lambda ok: setattr(self, 'is_loaded', True))

    def createWindow(self, windowType):
        popup = QMainWindow()
        popup.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        popup._is_valid_popup = True
        popup.setWindowTitle(APP_NAME)
        popup.resize(1000, 800)
        popup.setStyleSheet(f"QMainWindow {{ background-color: {Colors.BG_PRIMARY}; }}")

        icon_path = resource_path("max.ico")
        if os.path.exists(icon_path):
            popup.setWindowIcon(QIcon(icon_path))

        view = QWebEngineView(popup)
        page = CustomWebPage(self.profile(), view)
        view.setPage(page)

        popup.setCentralWidget(view)
        
        self._popups.append(popup)

        def safe_show():
            try:
                if getattr(popup, '_is_valid_popup', False):
                    popup.show()
            except Exception:
                pass

        # Задерживаем показ окна на 1.5 секунды.
        # Если это скачивание файла, то окно будет уничтожено 
        # до истечения таймера, и пользователь вообще ничего не увидит.
        QTimer.singleShot(1500, safe_show)

        return page


class ProfileBrowser(QWidget):
    """Браузерный виджет для отдельного профиля."""

    url_changed = pyqtSignal(str)
    zoom_changed = pyqtSignal(float)
    connection_changed = pyqtSignal(bool)

    def __init__(self, profile_name: str, config: dict):
        super().__init__()
        self.profile_name = profile_name
        self.config = config
        self.active_downloads = []
        self.current_download = None
        self._is_connected = True

        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)

        pid = profile_storage_id(profile_name)

        storage_root = get_app_dir() / "storage" / pid
        persistent_dir = storage_root / "persistent"
        cache_dir = storage_root / "cache"

        storage_root.mkdir(parents=True, exist_ok=True)
        persistent_dir.mkdir(parents=True, exist_ok=True)
        cache_dir.mkdir(parents=True, exist_ok=True)

        self.profile = QWebEngineProfile(f"max_{pid}", self)
        self.profile.setPersistentStoragePath(str(persistent_dir))
        self.profile.setCachePath(str(cache_dir))

        try:
            self.profile.setPersistentCookiesPolicy(
                QWebEngineProfile.PersistentCookiesPolicy.AllowPersistentCookies
            )
        except Exception:
            pass

        self.profile.downloadRequested.connect(self.handle_download)

        self.browser = CustomWebView(self)
        self.page = CustomWebPage(self.profile, self.browser)
        self.browser.setPage(self.page)
        self.browser.loadFinished.connect(self.on_load_finished)
        self.browser.loadStarted.connect(self._on_load_started)
        self.browser.urlChanged.connect(self._on_url_changed)

        # Панель загрузок
        self.download_panel = QWidget()
        self.download_panel.setFixedHeight(62)
        self.download_panel.setStyleSheet(f"""
            QWidget {{ background-color: {Colors.BG_DARKER}; border-top: 1px solid {Colors.BORDER}; }}
            QLabel {{ border: none; background: transparent; }}
        """)

        dl_layout = QVBoxLayout(self.download_panel)
        dl_layout.setContentsMargins(20, 8, 20, 8)
        dl_layout.setSpacing(6)

        top_row = QHBoxLayout()
        self.dl_label = QLabel("📥 Скачивание...")
        self.dl_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: 12px; font-weight: 600;")
        self.dl_stats = QLabel("0%")
        self.dl_stats.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px;")
        top_row.addWidget(self.dl_label)
        top_row.addStretch()
        top_row.addWidget(self.dl_stats)
        dl_layout.addLayout(top_row)

        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(0, 0, 0, 0)
        bottom_row.setSpacing(10)

        self.dl_progress = QProgressBar()
        self.dl_progress.setFixedHeight(6)
        self.dl_progress.setTextVisible(False)
        self.dl_progress.setStyleSheet(f"""
            QProgressBar {{ border: none; border-radius: 3px; background-color: {Colors.BG_SECONDARY}; }}
            QProgressBar::chunk {{
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {Colors.ACCENT_GRADIENT_START}, stop:1 {Colors.ACCENT_GRADIENT_END});
                border-radius: 3px;
            }}
        """)

        self.btn_cancel_dl = QPushButton("✕")
        self.btn_cancel_dl.setFixedSize(22, 22)
        self.btn_cancel_dl.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel_dl.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; color: {Colors.TEXT_MUTED};
                border-radius: 11px; font-weight: bold; font-size: 11px;
                border: 1px solid {Colors.BORDER};
            }}
            QPushButton:hover {{ background-color: {Colors.DANGER}; color: white; border-color: {Colors.DANGER}; }}
        """)
        self.btn_cancel_dl.clicked.connect(self.cancel_download)

        bottom_row.addWidget(self.dl_progress)
        bottom_row.addWidget(self.btn_cancel_dl)
        dl_layout.addLayout(bottom_row)
        self.download_panel.hide()

        # Индикатор загрузки страницы
        self.loading_bar = QProgressBar()
        self.loading_bar.setFixedHeight(2)
        self.loading_bar.setTextVisible(False)
        self.loading_bar.setMaximum(0)
        self.loading_bar.setStyleSheet(f"""
            QProgressBar {{ border: none; background-color: transparent; }}
            QProgressBar::chunk {{ background-color: {Colors.ACCENT}; }}
        """)
        self.loading_bar.hide()

        self._main_layout.addWidget(self.loading_bar)
        self._main_layout.addWidget(self.browser)
        self._main_layout.addWidget(self.download_panel)

        self.apply_all_settings()
        self.browser.setUrl(QUrl("https://web.max.ru/login"))

    def _settings(self):
        for obj in (self.page, self.profile, self.browser):
            try:
                return obj.settings()
            except Exception:
                pass
        return None

    def _on_load_started(self):
        self.loading_bar.show()

    def _on_url_changed(self, url):
        self.url_changed.emit(url.toString())

    def on_load_finished(self, ok: bool):
        self.loading_bar.hide()
        self._is_connected = ok
        self.connection_changed.emit(ok)
        if not ok:
            self.browser.setHtml(OFFLINE_HTML, self.browser.url())

    def handle_download(self, download_item):
        try:
            # Уничтожаем все недавно созданные popup-окна (созданные менее 5 сек назад),
            # так как они были открыты только ради этого скачивания (target="_blank").
            if hasattr(self.page, '_popups'):
                for popup in list(self.page._popups):
                    try:
                        view = popup.centralWidget()
                        if view:
                            p = view.page()
                            if hasattr(p, 'created_at') and time.time() - p.created_at < 5.0:
                                popup._is_valid_popup = False
                                popup.close()
                                popup.deleteLater()
                                self.page._popups.remove(popup)
                    except Exception:
                        pass
        except Exception:
            pass

        self.active_downloads.append(download_item)
        self.current_download = download_item

        file_name = download_item.downloadFileName() or "download"
        mime_type = download_item.mimeType()

        if "." not in file_name:
            ext = mimetypes.guess_extension(mime_type)
            if not ext and mime_type and "webp" in mime_type:
                ext = ".webp"
            if ext:
                file_name += ext

        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                custom_download_path = json.load(f).get("global", {}).get("download_path", "")
        except Exception:
            custom_download_path = ""

        if custom_download_path and os.path.isdir(custom_download_path):
            downloads_dir = Path(custom_download_path)
        else:
            downloads_dir = Path(get_windows_downloads_folder())
            
        downloads_dir.mkdir(parents=True, exist_ok=True)
        target_path = unique_path(downloads_dir, file_name)

        download_item.setDownloadDirectory(str(downloads_dir))
        download_item.setDownloadFileName(target_path.name)

        download_item.receivedBytesChanged.connect(
            lambda: self.update_download_progress(download_item)
        )
        download_item.isFinishedChanged.connect(
            lambda: self.on_download_finished(download_item, str(target_path))
        )

        display_name = target_path.name if len(target_path.name) < 40 else target_path.name[:37] + "…"
        self.dl_label.setText(f"📥 {display_name}")
        self.dl_stats.setText("Подключение…")
        self.dl_progress.setMaximum(100)
        self.dl_progress.setValue(0)
        self.download_panel.show()
        download_item.accept()

    def cancel_download(self):
        if self.current_download:
            try:
                self.current_download.cancel()
            except Exception:
                pass
        if not self.active_downloads:
            self.download_panel.hide()

    def update_download_progress(self, download_item):
        try:
            received = download_item.receivedBytes()
            total = download_item.totalBytes()
            mb_recv = received / (1024 * 1024)
            if total > 0:
                mb_total = total / (1024 * 1024)
                percent = int((received / total) * 100)
                self.dl_progress.setMaximum(total)
                self.dl_progress.setValue(received)
                self.dl_stats.setText(f"{percent}%  ({mb_recv:.1f} / {mb_total:.1f} МБ)")
            else:
                self.dl_progress.setMaximum(0)
                self.dl_progress.setValue(0)
                self.dl_stats.setText(f"Скачано: {mb_recv:.1f} МБ")
        except Exception:
            pass

    def on_download_finished(self, download_item, full_path: str):
        if download_item in self.active_downloads:
            self.active_downloads.remove(download_item)
        if not self.active_downloads:
            self.download_panel.hide()

        completed = False
        try:
            if QWebEngineDownloadRequest is not None:
                completed = download_item.state() == QWebEngineDownloadRequest.DownloadState.DownloadCompleted
            else:
                completed = download_item.state() == download_item.DownloadState.DownloadCompleted
        except Exception:
            try:
                completed = bool(download_item.isFinished())
            except Exception:
                completed = False

        if completed:
            main_win = self.window()
            if main_win and hasattr(main_win, "tray_icon"):
                main_win.tray_icon.showMessage(
                    "Загрузка завершена",
                    f"Файл сохранён: {os.path.basename(full_path)}",
                    QSystemTrayIcon.MessageIcon.Information, 3000
                )
            if main_win and hasattr(main_win, "show_toast"):
                main_win.show_toast(
                    f"Файл сохранён: {os.path.basename(full_path)}",
                    icon="✅", toast_type="success"
                )

    def apply_all_settings(self):
        apply_qt_proxy(self.config.get("proxy", {}))

        settings = self._settings()
        safe_set_web_setting(settings, "WebRTCPublicInterfacesOnly", bool(self.config.get("webrtc_leak", False)))
        safe_set_web_setting(settings, "JavascriptCanOpenWindows", True)
        safe_set_web_setting(settings, "JavascriptEnabled", True)
        safe_set_web_setting(settings, "LocalStorageEnabled", True)

        try:
            self.page.setAudioMuted(bool(self.config.get("mute_audio", False)))
        except Exception:
            pass

        try:
            zoom_text = str(self.config.get("zoom", "100%")).replace("%", "").strip()
            zoom_val = float(zoom_text) / 100.0
            self.browser.setZoomFactor(zoom_val)
            self.zoom_changed.emit(zoom_val)
        except Exception:
            self.browser.setZoomFactor(1.0)

        mask = MASKS_DB.get(self.config.get("mask", "Windows 11 (Chrome)"))
        if not mask:
            mask = MASKS_DB["Windows 11 (Chrome)"]

        try:
            self.profile.setHttpUserAgent(mask.ua)
            self.profile.setHttpAcceptLanguage("ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7")
        except Exception:
            pass

        css_inject = THEMES.get(self.config.get("theme", "Telegram Dark"), "")

        if self.config.get("hide_scrollbars", False):
            css_inject += " ::-webkit-scrollbar { display: none !important; }"

        if self.config.get("adblock", False):
            css_inject += """
                .ads, .advertisement, [id*='yandex_rtb'], .banner {
                    display: none !important;
                }
            """

        canvas_noise = "true" if self.config.get("canvas_noise", True) else "false"
        audio_noise = "true" if self.config.get("audio_noise", True) else "false"
        css_js = json.dumps(css_inject)

        js_code = f"""
        (function() {{
            const config = {json.dumps(mask.to_dict())};
            try {{
                Object.defineProperty(navigator, 'userAgent', {{ get: () => config.ua }});
                Object.defineProperty(navigator, 'platform', {{ get: () => config.platform }});
                Object.defineProperty(navigator, 'vendor', {{ get: () => config.vendor }});
                Object.defineProperty(navigator, 'hardwareConcurrency', {{ get: () => 8 }});
                Object.defineProperty(navigator, 'deviceMemory', {{ get: () => 8 }});
                Object.defineProperty(navigator, 'languages', {{ get: () => ['ru-RU', 'ru', 'en-US', 'en'] }});
                Object.defineProperty(navigator, 'webdriver', {{ get: () => false }});
            }} catch (e) {{}}
            if ({canvas_noise}) {{
                try {{
                    const origTDU = HTMLCanvasElement.prototype.toDataURL;
                    HTMLCanvasElement.prototype.toDataURL = function(type) {{
                        try {{
                            const ctx = this.getContext('2d');
                            if (ctx && type && type.includes('image/png')) {{
                                const prev = ctx.fillStyle;
                                ctx.fillStyle = 'rgba(255,255,255,0.01)';
                                ctx.fillRect(0, 0, 1, 1);
                                ctx.fillStyle = prev;
                            }}
                        }} catch (e) {{}}
                        return origTDU.apply(this, arguments);
                    }};
                }} catch (e) {{}}
            }}
            if ({audio_noise}) {{
                try {{
                    const origGCD = AudioBuffer.prototype.getChannelData;
                    AudioBuffer.prototype.getChannelData = function(channel) {{
                        const data = origGCD.call(this, channel);
                        try {{
                            for (let i = 0; i < 64; i++) {{
                                const idx = Math.floor(Math.random() * data.length);
                                data[idx] += (Math.random() * 0.0001 - 0.00005);
                            }}
                        }} catch (e) {{}}
                        return data;
                    }};
                }} catch (e) {{}}
            }}
            window.addEventListener('DOMContentLoaded', () => {{
                try {{
                    const style = document.createElement('style');
                    style.textContent = {css_js};
                    document.head.appendChild(style);
                }} catch (e) {{}}
            }});
        }})();
        """

        try:
            self.profile.scripts().clear()
            script = QWebEngineScript()
            script.setSourceCode(js_code)
            script.setName("stealth_and_style")
            script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
            try:
                script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
            except Exception:
                pass
            self.profile.scripts().insert(script)
        except Exception:
            pass
