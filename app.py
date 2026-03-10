import sys
import mimetypes
import os
import json
import platform
import datetime
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, Any
import ctypes
import shutil

from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtGui import QIcon, QAction, QDesktopServices
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QStackedWidget, QInputDialog, QLabel, QDialog, 
    QComboBox, QFormLayout, QTabWidget, QCheckBox, QSystemTrayIcon, QMenu,
    QMessageBox, QProgressBar
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import (
    QWebEngineProfile, QWebEngineScript, QWebEngineSettings, QWebEnginePage
)

def resource_path(relative_path: str) -> str:
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def get_app_dir() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent

CONFIG_FILE = get_app_dir() / "config.json"

@dataclass
class DeviceMask:
    ua: str; platform: str; vendor: str; renderer: str
    touch: int; width: int; height: int; timezone: str; locale: str

    def to_dict(self) -> Dict[str, Any]:
        return self.__dict__

MASKS_DB = {
    "Windows 11 (Chrome)": DeviceMask(
        ua="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        platform="Win32", vendor="Google Inc.", renderer="ANGLE (NVIDIA, RTX 3060, D3D11)",
        touch=0, width=1920, height=1080, timezone="Europe/Moscow", locale="ru-RU"
    ),
    "macOS (Safari)": DeviceMask(
        ua="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        platform="MacIntel", vendor="Apple Computer, Inc.", renderer="Apple GPU",
        touch=0, width=2560, height=1600, timezone="Europe/London", locale="en-GB"
    )
}

THEMES = {
    "Стандартная": "",
    "Темная (Telegram)": """
        body { background-color: #1e1e24 !important; color: #e4e4e4 !important; }
        .cell { background-color: #2b2d31 !important; border-bottom: 1px solid #1e1e24 !important; }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-thumb { background: #3c3f41; border-radius: 3px; }
        ::-webkit-scrollbar-track { background: transparent; }
    """,
    "AMOLED Черная": """
        body { background-color: #000000 !important; color: #ffffff !important; }
        .cell { background-color: #0a0a0a !important; border-bottom: 1px solid #111 !important; }
    """
}

OFFLINE_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ожидание сети...</title>
    <style>
        body {
            margin: 0; padding: 0; background-color: #1e1e24; color: #e4e4e4;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            display: flex; flex-direction: column; justify-content: center; align-items: center;
            height: 100vh; text-align: center; user-select: none;
        }
        .icon-container { margin-bottom: 25px; position: relative; }
        .offline-icon { width: 80px; height: 80px; stroke: #8e9297; }
        h1 { font-size: 22px; margin: 0 0 10px 0; font-weight: 600; letter-spacing: 0.5px; }
        p { color: #8e9297; font-size: 14px; max-width: 320px; margin: 0 0 40px 0; line-height: 1.5; }
        .spinner {
            width: 30px; height: 30px; border: 3px solid #2b2d31; border-top: 3px solid #5865f2;
            border-radius: 50%; animation: spin 1s linear infinite;
        }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
    <script>
        setTimeout(() => { window.location.reload(); }, 5000);
    </script>
</head>
<body>
    <div class="icon-container">
        <svg class="offline-icon" viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="2" y1="2" x2="22" y2="22"></line>
            <path d="M8.5 16.5a5 5 0 0 1 7 0"></path>
            <path d="M2 8.82a15 15 0 0 1 4.17-2.65"></path>
            <path d="M10.66 5c4.01-.36 8.14.9 11.34 3.82"></path>
        </svg>
    </div>
    <h1>Ожидание сети...</h1>
    <p>Нет подключения к интернету. Приложение автоматически восстановит связь, когда появится сеть.</p>
    <div class="spinner"></div>
</body>
</html>
"""

class CustomWebPage(QWebEnginePage):
    def __init__(self, profile, parent=None):
        super().__init__(profile, parent)

    def createWindow(self, windowType):
        self.temp_view = QWebEngineView()
        self.temp_page = CustomWebPage(self.profile(), self.temp_view)
        self.temp_view.setPage(self.temp_page)
        return self.temp_page

class ProfileBrowser(QWidget):
    def __init__(self, profile_name: str, config: dict):
        super().__init__()
        self.profile_name = profile_name
        self.config = config 
        self.active_downloads = [] 
        self.current_download = None
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        storage_path = str(get_app_dir() / f"storage_{profile_name}")
        self.profile = QWebEngineProfile(storage_path, self)
        self.profile.setPersistentStoragePath(storage_path)
        self.profile.setCachePath(storage_path)
        
        self.profile.downloadRequested.connect(self.handle_download)
        
        self.browser = QWebEngineView()
        self.page = CustomWebPage(self.profile, self.browser)
        self.browser.setPage(self.page)
        self.browser.loadFinished.connect(self.on_load_finished)
        
        self.download_panel = QWidget()
        self.download_panel.setFixedHeight(65)
        self.download_panel.setStyleSheet("QWidget { background-color: #1e1e24; border-top: 1px solid #3c3f41; } QLabel { border: none; }")
        
        dl_layout = QVBoxLayout(self.download_panel)
        dl_layout.setContentsMargins(20, 10, 20, 10)
        dl_layout.setSpacing(8)

        top_row = QHBoxLayout()
        self.dl_label = QLabel("📥 Скачивание...")
        self.dl_label.setStyleSheet("color: #e4e4e4; font-size: 13px; font-weight: bold;")
        self.dl_stats = QLabel("0%")
        self.dl_stats.setStyleSheet("color: #8e9297; font-size: 12px; font-weight: normal;")
        top_row.addWidget(self.dl_label)
        top_row.addStretch()
        top_row.addWidget(self.dl_stats)
        dl_layout.addLayout(top_row)

        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(0, 0, 0, 0)
        self.dl_progress = QProgressBar()
        self.dl_progress.setFixedHeight(8)
        self.dl_progress.setTextVisible(False)
        self.dl_progress.setStyleSheet("QProgressBar { border: none; border-radius: 4px; background-color: #2b2d31; } QProgressBar::chunk { background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #5865f2, stop:1 #4752c4); border-radius: 4px; }")
        
        self.btn_cancel_dl = QPushButton("✖")
        self.btn_cancel_dl.setFixedSize(20, 20)
        self.btn_cancel_dl.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_cancel_dl.setStyleSheet("QPushButton { background-color: #ed4245; color: white; border-radius: 10px; font-weight: bold; font-size: 10px; border: none; } QPushButton:hover { background-color: #c9383b; }")
        self.btn_cancel_dl.clicked.connect(self.cancel_download)

        bottom_row.addWidget(self.dl_progress)
        bottom_row.addWidget(self.btn_cancel_dl)
        dl_layout.addLayout(bottom_row)
        
        self.download_panel.hide()
        self.layout.addWidget(self.browser)
        self.layout.addWidget(self.download_panel)

        self.apply_all_settings()
        self.browser.setUrl(QUrl("https://web.max.ru/login"))

    def on_load_finished(self, ok: bool):
        if not ok:
            self.browser.setHtml(OFFLINE_HTML, self.browser.url())

    def handle_download(self, download_item):
        self.active_downloads.append(download_item) 
        self.current_download = download_item
        
        file_name = download_item.downloadFileName()
        mime_type = download_item.mimeType()
        
        if "." not in file_name:
            ext = mimetypes.guess_extension(mime_type)
            if not ext and "webp" in mime_type: 
                ext = ".webp"
            if ext:
                file_name += ext

        downloads_dir = get_app_dir() / "Downloads"
        downloads_dir.mkdir(exist_ok=True)
        
        download_item.setDownloadDirectory(str(downloads_dir))
        download_item.setDownloadFileName(file_name)
        
        download_item.receivedBytesChanged.connect(lambda: self.update_download_progress(download_item))
        download_item.isFinishedChanged.connect(lambda: self.on_download_finished(download_item, str(downloads_dir / file_name)))
        
        display_name = file_name if len(file_name) < 40 else file_name[:37] + "..."
        self.dl_label.setText(f"📥 Скачивание: {display_name}")
        self.dl_stats.setText("Подключение...")
        self.dl_progress.setMaximum(100)
        self.dl_progress.setValue(0)
        
        self.download_panel.show()
        download_item.accept()

    def cancel_download(self):
        if self.current_download:
            self.current_download.cancel()
            self.download_panel.hide()

    def update_download_progress(self, download_item):
        bytes_received = download_item.receivedBytes()
        bytes_total = download_item.totalBytes()
        mb_received = bytes_received / (1024 * 1024)
        
        if bytes_total > 0:
            mb_total = bytes_total / (1024 * 1024)
            percent = int((bytes_received / bytes_total) * 100)
            self.dl_progress.setMaximum(bytes_total)
            self.dl_progress.setValue(bytes_received)
            self.dl_stats.setText(f"{percent}%  ({mb_received:.1f} MB / {mb_total:.1f} MB)")
        else:
            self.dl_progress.setMaximum(0) 
            self.dl_progress.setValue(0)
            self.dl_stats.setText(f"Скачано: {mb_received:.1f} MB")

    def on_download_finished(self, download_item, full_path: str):
        self.download_panel.hide()
        if download_item in self.active_downloads:
            self.active_downloads.remove(download_item)
            
        if download_item.state() == download_item.DownloadState.DownloadCompleted:
            self.main_window().tray_icon.showMessage("Загрузка завершена", "Файл успешно сохранен", QSystemTrayIcon.MessageIcon.Information, 3000)

    def main_window(self):
        window = self.window()
        return window if hasattr(window, 'tray_icon') else None

    def apply_all_settings(self):
        settings = self.profile.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.WebRTCPublicInterfacesOnly, self.config.get("webrtc_leak", False))
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanOpenWindows, True)
        
        self.page.setAudioMuted(self.config.get("mute_audio", False))
        zoom_val = float(self.config.get("zoom", "100%").replace("%", "")) / 100.0
        self.browser.setZoomFactor(zoom_val)

        mask = MASKS_DB.get(self.config.get("mask", "Windows 11 (Chrome)"))
        if mask:
            self.profile.setHttpUserAgent(mask.ua)
            css_inject = THEMES.get(self.config.get("theme", "Темная (Telegram)"), "")
            if self.config.get("hide_scrollbars", False):
                css_inject += " ::-webkit-scrollbar { display: none !important; }"
            if self.config.get("adblock", False):
                css_inject += " .ads, .advertisement, [id*='yandex_rtb'] { display: none !important; }"

            js_code = f"""
            (function() {{
                const config = {json.dumps(mask.to_dict())};
                Object.defineProperty(navigator, 'userAgent', {{ get: () => config.ua }});
                Object.defineProperty(navigator, 'platform', {{ get: () => config.platform }});
                if ({str(self.config.get("canvas_noise", True)).lower()}) {{
                    const toDataURL = HTMLCanvasElement.prototype.toDataURL;
                    HTMLCanvasElement.prototype.toDataURL = function() {{ return toDataURL.apply(this, arguments); }};
                }}
                window.addEventListener('DOMContentLoaded', () => {{
                    const style = document.createElement('style');
                    style.type = 'text/css';
                    style.innerHTML = `{css_inject.replace('`', '')}`;
                    document.head.appendChild(style);
                }});
            }})();
            """
            self.profile.scripts().clear()
            script = QWebEngineScript()
            script.setSourceCode(js_code)
            script.setName("stealth_and_style")
            script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
            script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
            self.profile.scripts().insert(script)

class SettingsDialog(QDialog):
    def __init__(self, main_app):
        super().__init__(main_app)
        self.main_app = main_app
        self.setWindowTitle("Настройки MAX")

        self.setFixedSize(600, 550) 
        
        icon_path = resource_path("max.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.setStyleSheet("""
            QDialog { 
                background-color: #313338; 
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            }
            
            /* --- ВКЛАДКИ --- */
            QTabWidget::pane { 
                border: none; 
                background-color: #313338; 
            }
            QTabBar::tab { 
                background: transparent; 
                color: #a3a6aa; 
                padding: 12px 20px; 
                font-size: 14px; 
                font-weight: 600; 
                border-bottom: 3px solid transparent; 
            }
            QTabBar::tab:hover { 
                color: #dbdee1; 
                background-color: #35373c;
            }
            QTabBar::tab:selected { 
                color: #ffffff; 
                border-bottom: 3px solid #5865f2; 
            }
            
            /* --- ТЕКСТ И ОТСТУПЫ --- */
            QLabel { 
                color: #dbdee1; 
                font-size: 14px; 
                font-weight: 600; 
            }
            
            /* --- ВЫПАДАЮЩИЕ СПИСКИ --- */
            QComboBox { 
                background-color: #1e1f22; 
                color: #dbdee1; 
                font-size: 14px; 
                padding: 10px 15px; 
                border-radius: 6px; 
                border: 1px solid #1e1f22; 
            }
            QComboBox:hover { 
                background-color: #2b2d31; 
            }
            QComboBox::drop-down { 
                border: none; 
                width: 30px; 
            }
            QComboBox::down-arrow { 
                image: none; /* Убираем дефолтную страшную стрелку */
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #a3a6aa;
                margin-right: 10px;
            }
            QComboBox QAbstractItemView { 
                background-color: #2b2d31; 
                color: #dbdee1; 
                border: 1px solid #1e1f22; 
                border-radius: 6px; 
                selection-background-color: #5865f2; 
                outline: none;
            }
            
            /* --- ЧЕКБОКСЫ --- */
            QCheckBox { 
                color: #dbdee1; 
                font-size: 14px; 
                spacing: 12px; 
            }
            QCheckBox::indicator { 
                width: 20px; 
                height: 20px; 
                border-radius: 6px; 
                border: 2px solid #80848e; 
                background: transparent; 
            }
            QCheckBox::indicator:hover { 
                border: 2px solid #dbdee1; 
            }
            QCheckBox::indicator:checked { 
                background-color: #5865f2; 
                border: 2px solid #5865f2; 
            }
            
            /* --- КНОПКИ --- */
            QPushButton { 
                background-color: #5865f2; 
                color: white; 
                padding: 12px; 
                border-radius: 6px; 
                font-size: 14px; 
                font-weight: bold; 
                border: none;
            }
            QPushButton:hover { 
                background-color: #4752c4; 
            }
            QPushButton:pressed {
                background-color: #3c45a5;
            }
            
            /* --- КНОПКА ПОДДЕРЖКИ И ДОБАВЛЕНИЯ ПРОФИЛЯ --- */
            .SupportBtn { background-color: #da373c; margin-top: 10px; }
            .SupportBtn:hover { background-color: #c92c31; }
            .AddProfileBtn { background-color: #23a559; }
            .AddProfileBtn:hover { background-color: #1e8f4c; }
        """)

        active_browser = self.main_app.get_active_browser()
        config = active_browser.config if active_browser else {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 20)
        tabs = QTabWidget()

        def create_padded_form():
            w = QWidget()
            f = QFormLayout()
            f.setContentsMargins(30, 30, 30, 30)
            f.setVerticalSpacing(25)
            f.setHorizontalSpacing(20)
            w.setLayout(f)
            return w, f

        tab_prof, form_prof = create_padded_form()
        tab_priv, form_priv = create_padded_form()
        tab_look, form_look = create_padded_form()
        tab_sys,  form_sys  = create_padded_form()
        
        tab_support = QWidget()
        form_support = QVBoxLayout()
        form_support.setContentsMargins(30, 30, 30, 30)
        form_support.setSpacing(15)
        tab_support.setLayout(form_support)

        self.profile_combo = QComboBox()
        self.profile_combo.addItems(self.main_app.app_data["profiles"].keys())
        self.profile_combo.setCurrentIndex(self.main_app.browser_stack.currentIndex())
        self.profile_combo.currentIndexChanged.connect(self.main_app.switch_profile)
        form_prof.addRow("Текущий аккаунт:", self.profile_combo)

        btn_add = QPushButton("+ Добавить новый профиль")
        btn_add.setProperty("class", "AddProfileBtn")
        btn_add.clicked.connect(self.add_profile_dialog)
        form_prof.addRow("Мультиаккаунт:", btn_add)

        self.mask_combo = QComboBox()
        self.mask_combo.addItems(MASKS_DB.keys())
        self.mask_combo.setCurrentText(config.get("mask", "Windows 11 (Chrome)"))
        form_priv.addRow("Подмена ОС:", self.mask_combo)

        self.cb_webrtc = QCheckBox("Запретить утечку IP (WebRTC Strict)")
        self.cb_webrtc.setChecked(config.get("webrtc_leak", False))
        form_priv.addRow("Защита сети:", self.cb_webrtc)

        self.cb_canvas = QCheckBox("Шум на Canvas (Анти-трекинг)")
        self.cb_canvas.setChecked(config.get("canvas_noise", True))
        form_priv.addRow("Защита графики:", self.cb_canvas)

        self.cb_adblock = QCheckBox("Встроенный AdBlock")
        self.cb_adblock.setChecked(config.get("adblock", False))
        form_priv.addRow("Реклама:", self.cb_adblock)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(THEMES.keys())
        self.theme_combo.setCurrentText(config.get("theme", "Темная (Telegram)"))
        form_look.addRow("Тема сайта:", self.theme_combo)

        self.zoom_combo = QComboBox()
        self.zoom_combo.addItems(["80%", "90%", "100%", "110%", "125%", "150%"])
        self.zoom_combo.setCurrentText(config.get("zoom", "100%"))
        form_look.addRow("Масштаб:", self.zoom_combo)

        self.cb_scroll = QCheckBox("Скрыть полосы прокрутки")
        self.cb_scroll.setChecked(config.get("hide_scrollbars", False))
        form_look.addRow("Интерфейс:", self.cb_scroll)

        self.cb_mute = QCheckBox("Отключить звуки вкладки")
        self.cb_mute.setChecked(config.get("mute_audio", False))
        form_sys.addRow("Звук:", self.cb_mute)

        self.cb_tray = QCheckBox("Сворачивать в трей при закрытии")
        self.cb_tray.setChecked(self.main_app.app_data["global"].get("close_to_tray", True))
        form_sys.addRow("Фон:", self.cb_tray)

        lbl_support = QLabel("Возникли ошибки или баги в работе клиента?\n\nВы можете создать диагностический файл. Он соберет базовую информацию о вашей ОС и текущих настройках программы (без личных данных).\n\nОтправьте этот файл разработчику в Telegram для быстрого решения проблемы.")
        lbl_support.setWordWrap(True)
        lbl_support.setStyleSheet("color: #a3a6aa; font-weight: normal; font-size: 14px; line-height: 1.5;")
        
        btn_report = QPushButton("🛠 Создать отчет и открыть Telegram")
        btn_report.setProperty("class", "SupportBtn")
        btn_report.clicked.connect(self.generate_support_report)

        form_support.addWidget(lbl_support)
        form_support.addWidget(btn_report)
        form_support.addStretch()

        tabs.addTab(tab_prof, "👤 Профиль")
        tabs.addTab(tab_priv, "🛡️ Приватность")
        tabs.addTab(tab_look, "🎨 Вид")
        tabs.addTab(tab_sys, "⚙️ Система")
        tabs.addTab(tab_support, "🛠 Поддержка")
        layout.addWidget(tabs)

        bottom_widget = QWidget()
        bottom_layout = QHBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(30, 0, 30, 0)
        
        btn_apply = QPushButton("Сохранить настройки")
        btn_apply.clicked.connect(self.save_and_apply)
        bottom_layout.addWidget(btn_apply)
        
        layout.addWidget(bottom_widget)

    def get_ram_info(self):
        """Получает информацию об ОЗУ средствами Windows API без сторонних библиотек"""
        try:
            if platform.system() == "Windows":
                kernel32 = ctypes.windll.kernel32
                c_ulonglong = ctypes.c_ulonglong
                class MEMORYSTATUSEX(ctypes.Structure):
                    _fields_ = [
                        ('dwLength', ctypes.c_ulong),
                        ('dwMemoryLoad', ctypes.c_ulong),
                        ('ullTotalPhys', c_ulonglong),
                        ('ullAvailPhys', c_ulonglong),
                        ('ullTotalPageFile', c_ulonglong),
                        ('ullAvailPageFile', c_ulonglong),
                        ('ullTotalVirtual', c_ulonglong),
                        ('ullAvailVirtual', c_ulonglong),
                        ('sullAvailExtendedVirtual', c_ulonglong),
                    ]
                memoryStatus = MEMORYSTATUSEX()
                memoryStatus.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
                kernel32.GlobalMemoryStatusEx(ctypes.byref(memoryStatus))
                
                total_ram = memoryStatus.ullTotalPhys / (1024**3)
                avail_ram = memoryStatus.ullAvailPhys / (1024**3)
                return f"{total_ram:.1f} ГБ (Доступно прямо сейчас: {avail_ram:.1f} ГБ)"
            else:
                return "Недоступно (не Windows)"
        except Exception as e:
            return f"Ошибка чтения RAM: {e}"

    def generate_support_report(self):
        report = []
        report.append("=== MAX Desktop Diagnostic Report ===")
        report.append(f"Дата создания: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        report.append("\n--- СИСТЕМА ---")
        report.append(f"ОС: {platform.system()} {platform.release()} (Версия: {platform.version()})")
        report.append(f"Платформа: {platform.platform()}")
        report.append(f"Архитектура: {platform.machine()}")
        
        report.append("\n--- ЖЕЛЕЗО ---")
        report.append(f"Процессор: {platform.processor()}")
        report.append(f"Количество ядер: {os.cpu_count()}")
        report.append(f"Оперативная память: {self.get_ram_info()}")
        
        try:
            screen = QApplication.primaryScreen().size()
            report.append(f"Разрешение экрана: {screen.width()}x{screen.height()}")
        except Exception:
            pass

        report.append("\n--- ПРИЛОЖЕНИЕ И ДИСК ---")
        app_dir = get_app_dir()
        is_portable = getattr(sys, 'frozen', False)
        
        try:
            total, used, free = shutil.disk_usage(app_dir)
            report.append(f"Диск (где лежит программа): Свободно {free // (1024**3)} ГБ из {total // (1024**3)} ГБ")
        except Exception:
            report.append("Диск: Ошибка доступа")
            
        report.append(f"Тип запуска: {'Compiled (.exe)' if is_portable else 'Python Script'}")
        report.append(f"Рабочая папка: {app_dir}")
        report.append(f"Python: {platform.python_version()}")
        
        active_browser = self.main_app.get_active_browser()
        if active_browser:
            report.append(f"Базовый движок (Chromium): {active_browser.profile.httpUserAgent()}")

        report.append("\n=== APP CONFIGURATION (JSON) ===")
        safe_config = json.dumps(self.main_app.app_data, indent=4, ensure_ascii=False)
        report.append(safe_config)
        
        try:
            desktop = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop')
        except KeyError:
            desktop = os.path.expanduser("~/Desktop")
            
        report_path = os.path.join(desktop, "MAX_Support_Report.txt")
        
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(report))
            
        QMessageBox.information(
            self, 
            "Отчет успешно создан", 
            f"Файл диагностики сохранен на рабочем столе:\n\n{report_path}\n\nСейчас откроется Telegram. Пожалуйста, прикрепите этот файл к вашему сообщению в поддержку."
        )
        QDesktopServices.openUrl(QUrl("https://t.me/devjijlk")) 

    def add_profile_dialog(self):
        text, ok = QInputDialog.getText(self, "Новый аккаунт", "Название:")
        if ok and text and text not in self.main_app.app_data["profiles"]:
            self.main_app.add_profile(text)
            self.profile_combo.addItem(text)
            self.profile_combo.setCurrentText(text)

    def save_and_apply(self):
        self.main_app.app_data["global"]["close_to_tray"] = self.cb_tray.isChecked()
        active_browser = self.main_app.get_active_browser()
        if active_browser:
            active_browser.config.update({
                "mask": self.mask_combo.currentText(),
                "webrtc_leak": self.cb_webrtc.isChecked(),
                "canvas_noise": self.cb_canvas.isChecked(),
                "adblock": self.cb_adblock.isChecked(),
                "theme": self.theme_combo.currentText(),
                "zoom": self.zoom_combo.currentText(),
                "hide_scrollbars": self.cb_scroll.isChecked(),
                "mute_audio": self.cb_mute.isChecked()
            })
            active_browser.apply_all_settings()
            active_browser.browser.reload()
        self.main_app.save_config()
        self.accept()

    def add_profile_dialog(self):
        text, ok = QInputDialog.getText(self, "Новый аккаунт", "Название:")
        if ok and text and text not in self.main_app.app_data["profiles"]:
            self.main_app.add_profile(text)
            self.profile_combo.addItem(text)
            self.profile_combo.setCurrentText(text)

    def save_and_apply(self):
        self.main_app.app_data["global"]["close_to_tray"] = self.cb_tray.isChecked()

        active_browser = self.main_app.get_active_browser()
        if active_browser:
            active_browser.config.update({
                "mask": self.mask_combo.currentText(),
                "webrtc_leak": self.cb_webrtc.isChecked(),
                "canvas_noise": self.cb_canvas.isChecked(),
                "adblock": self.cb_adblock.isChecked(),
                "theme": self.theme_combo.currentText(),
                "zoom": self.zoom_combo.currentText(),
                "hide_scrollbars": self.cb_scroll.isChecked(),
                "mute_audio": self.cb_mute.isChecked()
            })
            active_browser.apply_all_settings()
            active_browser.browser.reload()
            
        self.main_app.save_config()
        self.accept()

class MaxApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MAX Desktop Portable")
        self.resize(1300, 800)
        
        icon_path = resource_path("max.ico")
        if os.path.exists(icon_path):
            self.app_icon = QIcon(icon_path)
            self.setWindowIcon(self.app_icon)
        else:
            self.app_icon = None
        
        self.setStyleSheet("QMainWindow { background-color: #1e1e24; }")
        
        self.profile_browsers = {}
        self.browser_stack = QStackedWidget()
        self.load_config()

        self._setup_tray()
        self._setup_ui()

        if not self.app_data["profiles"]:
            self.add_profile("Основной аккаунт")
        else:
            for name in self.app_data["profiles"].keys():
                self.add_profile(name, is_loading=True)

    def load_config(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    self.app_data = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._create_default_config()
        else:
            self._create_default_config()

    def _create_default_config(self):
        self.app_data = {
            "global": {"close_to_tray": True},
            "profiles": {}
        }

    def save_config(self):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.app_data, f, ensure_ascii=False, indent=4)

    def _setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        nav_bar = QWidget()
        nav_bar.setFixedWidth(65)
        nav_bar.setStyleSheet("background-color: #1e1e24; border-right: 1px solid #2b2d31;")
        nav_layout = QVBoxLayout(nav_bar)
        nav_layout.setContentsMargins(5, 15, 5, 15)

        btn_settings = QPushButton("⚙️")
        btn_settings.setFixedSize(50, 50)
        btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_settings.setStyleSheet("QPushButton { background-color: transparent; font-size: 26px; border-radius: 12px; } QPushButton:hover { background-color: #2b2d31; }")
        btn_settings.clicked.connect(self.open_settings)

        nav_layout.addStretch()
        nav_layout.addWidget(btn_settings)

        main_layout.addWidget(nav_bar)
        main_layout.addWidget(self.browser_stack)

    def _setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        if self.app_icon:
            self.tray_icon.setIcon(self.app_icon)
        
        tray_menu = QMenu()
        show_action = QAction("Развернуть", self)
        show_action.triggered.connect(self.showNormal)
        quit_action = QAction("Выход", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        
        tray_menu.addAction(show_action)
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_activated)
        self.tray_icon.show()

    def tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.showNormal()

    def closeEvent(self, event):
        if self.app_data["global"].get("close_to_tray", True):
            event.ignore()
            self.hide()
            self.tray_icon.showMessage("MAX Portable", "Приложение свернуто в фоновый режим.", QSystemTrayIcon.MessageIcon.Information, 2000)
        else:
            event.accept()

    def add_profile(self, name: str, is_loading=False):
        if name not in self.app_data["profiles"]:
            self.app_data["profiles"][name] = {
                "mask": "Windows 11 (Chrome)", "theme": "Темная (Telegram)", "zoom": "100%",
                "webrtc_leak": False, "canvas_noise": True, "adblock": False, "mute_audio": False, "hide_scrollbars": False
            }
            if not is_loading: self.save_config()

        browser_widget = ProfileBrowser(name, self.app_data["profiles"][name])
        self.profile_browsers[name] = browser_widget
        self.browser_stack.addWidget(browser_widget)
        self.switch_profile(self.browser_stack.count() - 1)

    def switch_profile(self, index: int):
        if 0 <= index < self.browser_stack.count():
            self.browser_stack.setCurrentIndex(index)

    def get_active_browser(self) -> ProfileBrowser:
        return self.browser_stack.currentWidget()

    def open_settings(self):
        SettingsDialog(self).exec()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MaxApp()
    window.show()
    sys.exit(app.exec())