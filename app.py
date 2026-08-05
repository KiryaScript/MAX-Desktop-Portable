import sys
import os
import json
import shutil
import platform
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import (
    QIcon, QAction, QShortcut, QKeySequence, QColor, QFont, QPalette
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QInputDialog, QSystemTrayIcon, QMenu, QFrame
)

from core.constants import (
    APP_NAME, APP_VERSION, Colors, GLOBAL_TOOLTIP_STYLE,
    DEFAULT_PROXY, CONFIG_FILE, WINDOW_STATE_FILE,
    resource_path, get_app_dir, profile_storage_id
)
from core.network import apply_startup_proxy_env, apply_qt_proxy
from ui.widgets import TopBar, Sidebar, StatusBar, ToastNotification
from ui.browser import ProfileBrowser
from ui.dialogs import SettingsDialog, ShortcutsOverlay


class MaxApp(QMainWindow):
    """Главное окно приложения MAX Desktop."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1340, 880)
        self.setMinimumSize(800, 500)

        icon_path = resource_path("max.ico")
        if os.path.exists(icon_path):
            self.app_icon = QIcon(icon_path)
            self.setWindowIcon(self.app_icon)
        else:
            self.app_icon = None

        self.setStyleSheet(f"""
            QMainWindow {{ background-color: {Colors.BG_DARKEST}; }}
            {GLOBAL_TOOLTIP_STYLE}
        """)

        self.profile_browsers = {}
        self.browser_stack = QStackedWidget()
        self.browser_stack.setStyleSheet(f"background-color: {Colors.BG_PRIMARY};")

        self.load_config()

        self._setup_tray()
        self._setup_ui()
        self._setup_shortcuts()

        if not self.app_data["profiles"]:
            self.add_profile("Основной аккаунт")
        else:
            for name in list(self.app_data["profiles"].keys()):
                self.add_profile(name, is_loading=True)

        if self.browser_stack.count() > 0:
            self.switch_profile(0)

        self._restore_window_state()

    # ── Конфигурация ──

    def _default_profile(self):
        return {
            "mask": "Windows 11 (Chrome)",
            "theme": "Telegram Dark",
            "zoom": "100%",
            "webrtc_leak": False,
            "canvas_noise": True,
            "audio_noise": True,
            "adblock": False,
            "mute_audio": False,
            "hide_scrollbars": False,
            "proxy": self.app_data.get("global", {}).get("proxy", DEFAULT_PROXY).copy()
        }

    def load_config(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    self.app_data = json.load(f)
                self._migrate_config()
            except Exception:
                self._create_default_config()
        else:
            self._create_default_config()

    def _create_default_config(self):
        self.app_data = {
            "global": {
                "close_to_tray": True,
                "save_window_state": True,
                "proxy": DEFAULT_PROXY.copy()
            },
            "profiles": {}
        }

    def _migrate_config(self):
        g = self.app_data.setdefault("global", {})
        g.setdefault("close_to_tray", True)
        g.setdefault("save_window_state", True)

        if "proxy" not in g:
            first_profile = next(iter(self.app_data.get("profiles", {}).values()), None)
            if first_profile and isinstance(first_profile.get("proxy"), dict):
                g["proxy"] = first_profile["proxy"].copy()
            else:
                g["proxy"] = DEFAULT_PROXY.copy()

        self.app_data.setdefault("profiles", {})

        old_theme_map = {
            "Стандартная": "MAX Original",
            "Темная (Telegram)": "Telegram Dark",
            "AMOLED Черная": "AMOLED Black"
        }

        defaults = self._default_profile()
        for profile in self.app_data["profiles"].values():
            if profile.get("theme") in old_theme_map:
                profile["theme"] = old_theme_map[profile["theme"]]
            for key, value in defaults.items():
                if key not in profile:
                    profile[key] = value.copy() if isinstance(value, dict) else value

    def save_config(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.app_data, f, ensure_ascii=False, indent=4)
        except Exception:
            pass

    # ── Состояние окна ──

    def _save_window_state(self):
        if not self.app_data.get("global", {}).get("save_window_state", True):
            return
        try:
            state = {
                "x": self.x(), "y": self.y(),
                "width": self.width(), "height": self.height(),
                "maximized": self.isMaximized()
            }
            with open(WINDOW_STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f)
        except Exception:
            pass

    def _restore_window_state(self):
        if not self.app_data.get("global", {}).get("save_window_state", True):
            return
        try:
            if WINDOW_STATE_FILE.exists():
                with open(WINDOW_STATE_FILE, "r", encoding="utf-8") as f:
                    state = json.load(f)
                if state.get("maximized"):
                    self.showMaximized()
                else:
                    self.setGeometry(
                        state.get("x", 100), state.get("y", 100),
                        state.get("width", 1340), state.get("height", 880)
                    )
        except Exception:
            pass

    # ── UI ──

    def _setup_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)

        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.top_bar = TopBar(self)
        main_layout.addWidget(self.top_bar)

        separator = QFrame()
        separator.setFixedHeight(1)
        separator.setStyleSheet(f"background-color: {Colors.BORDER};")
        main_layout.addWidget(separator)

        content_area = QWidget()
        content_layout = QHBoxLayout(content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.sidebar = Sidebar(self)
        self.sidebar.profile_clicked.connect(self.switch_profile)
        self.sidebar.settings_clicked.connect(self.open_settings)
        self.sidebar.add_profile_clicked.connect(self.add_new_profile)

        sidebar_sep = QFrame()
        sidebar_sep.setFixedWidth(1)
        sidebar_sep.setStyleSheet(f"background-color: {Colors.BORDER};")

        content_layout.addWidget(self.sidebar)
        content_layout.addWidget(sidebar_sep)
        content_layout.addWidget(self.browser_stack)

        main_layout.addWidget(content_area)

        self.status_bar = StatusBar(self)
        main_layout.addWidget(self.status_bar)

        self._refresh_sidebar()

    def _setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        if self.app_icon:
            self.tray_icon.setIcon(self.app_icon)

        tray_menu = QMenu()
        tray_menu.setStyleSheet(f"""
            QMenu {{
                background-color: {Colors.BG_ELEVATED}; color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER}; border-radius: 8px; padding: 4px;
            }}
            QMenu::item {{ padding: 8px 24px; border-radius: 4px; }}
            QMenu::item:selected {{ background-color: {Colors.ACCENT}; }}
        """)

        show_action = QAction("Показать", self)
        show_action.triggered.connect(self._show_from_tray)

        settings_action = QAction("Настройки", self)
        settings_action.triggered.connect(lambda: (self._show_from_tray(), self.open_settings()))

        quit_action = QAction("Выход", self)
        quit_action.triggered.connect(QApplication.instance().quit)

        tray_menu.addAction(show_action)
        tray_menu.addAction(settings_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.tray_activated)
        self.tray_icon.show()

    def _show_from_tray(self):
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl+T"), self, self.add_new_profile)
        QShortcut(QKeySequence("Ctrl+W"), self, self.close)
        QShortcut(QKeySequence("Alt+Left"), self, self.go_back)
        QShortcut(QKeySequence("Alt+Right"), self, self.go_forward)
        QShortcut(QKeySequence("Ctrl+R"), self, self.reload_page)
        QShortcut(QKeySequence("F5"), self, self.reload_page)
        QShortcut(QKeySequence("Ctrl+Shift+S"), self, self.open_settings)
        QShortcut(QKeySequence("F1"), self, self._show_shortcuts)

        for i in range(1, 10):
            QShortcut(
                QKeySequence(f"Ctrl+{i}"), self,
                lambda idx=i - 1: self.switch_profile(idx)
            )

    def _show_shortcuts(self):
        ShortcutsOverlay(self).exec()

    def _refresh_sidebar(self):
        names = list(self.profile_browsers.keys())
        self.sidebar.rebuild(names, self.browser_stack.currentIndex())
        self._update_top_profile_label()

    def _update_top_profile_label(self):
        index = self.browser_stack.currentIndex()
        names = list(self.profile_browsers.keys())
        if 0 <= index < len(names):
            name = names[index]
            self.top_bar.profile_label.setText(name)
            self.status_bar.update_profile(name)
        else:
            self.top_bar.profile_label.setText("")
            self.status_bar.update_profile("")

    # ── Трей ──

    def tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_from_tray()

    def closeEvent(self, event):
        self._save_window_state()
        if self.app_data.get("global", {}).get("close_to_tray", True):
            event.ignore()
            self.hide()
            try:
                self.tray_icon.showMessage(
                    APP_NAME, "Приложение свёрнуто в фоновый режим.",
                    QSystemTrayIcon.MessageIcon.Information, 2000
                )
            except Exception:
                pass
        else:
            event.accept()

    # ── Профили ──

    def add_profile(self, name: str, is_loading=False):
        name = name.strip()
        if not name:
            return

        if name in self.profile_browsers:
            index = list(self.profile_browsers.keys()).index(name)
            self.switch_profile(index)
            return

        if name not in self.app_data["profiles"]:
            self.app_data["profiles"][name] = self._default_profile()
            if not is_loading:
                self.save_config()
        else:
            defaults = self._default_profile()
            for key, value in defaults.items():
                if key not in self.app_data["profiles"][name]:
                    self.app_data["profiles"][name][key] = (
                        value.copy() if isinstance(value, dict) else value
                    )

        browser_widget = ProfileBrowser(name, self.app_data["profiles"][name])
        browser_widget.url_changed.connect(self.status_bar.update_url)
        browser_widget.zoom_changed.connect(self.status_bar.update_zoom)
        browser_widget.connection_changed.connect(self.top_bar.set_connection_status)

        self.profile_browsers[name] = browser_widget
        self.browser_stack.addWidget(browser_widget)
        self.browser_stack.setCurrentWidget(browser_widget)
        self._refresh_sidebar()

    def delete_profile(self, name: str):
        if name not in self.profile_browsers:
            return

        browser_widget = self.profile_browsers.pop(name)
        self.browser_stack.removeWidget(browser_widget)
        browser_widget.deleteLater()

        if name in self.app_data["profiles"]:
            del self.app_data["profiles"][name]

        pid = profile_storage_id(name)
        storage_path = get_app_dir() / "storage" / pid
        try:
            if storage_path.exists():
                shutil.rmtree(storage_path, ignore_errors=True)
        except Exception:
            pass

        self.save_config()
        if self.browser_stack.count() > 0:
            self.switch_profile(0)
        self._refresh_sidebar()

    def add_new_profile(self):
        text, ok = QInputDialog.getText(self, "Новый аккаунт", "Название профиля:")
        if ok and text.strip():
            self.add_profile(text.strip())

    def switch_profile(self, index: int):
        if 0 <= index < self.browser_stack.count():
            self.browser_stack.setCurrentIndex(index)
            self.sidebar.set_active(index)
            self._update_top_profile_label()

            browser = self.get_active_browser()
            if browser:
                try:
                    self.status_bar.update_url(browser.browser.url().toString())
                    self.status_bar.update_zoom(browser.browser.zoomFactor())
                except Exception:
                    pass

    def get_active_browser(self) -> Optional[ProfileBrowser]:
        return self.browser_stack.currentWidget()

    # ── Действия ──

    def open_settings(self):
        SettingsDialog(self).exec()

    def show_toast(self, message: str, icon: str = "ℹ️",
                   duration: int = 3000, toast_type: str = "info"):
        try:
            ToastNotification(self, message, icon, duration, toast_type)
        except Exception:
            pass

    def go_back(self):
        active = self.get_active_browser()
        if active:
            try:
                if active.browser.history().canGoBack():
                    active.browser.back()
            except Exception:
                pass

    def go_forward(self):
        active = self.get_active_browser()
        if active:
            try:
                if active.browser.history().canGoForward():
                    active.browser.forward()
            except Exception:
                pass

    def reload_page(self):
        active = self.get_active_browser()
        if active:
            try:
                active.browser.reload()
            except Exception:
                pass


# ─────────────────────────────────────────────
# Точка входа
# ─────────────────────────────────────────────
if __name__ == "__main__":
    apply_startup_proxy_env()

    try:
        if hasattr(Qt.ApplicationAttribute, "AA_EnableHighDpiScaling"):
            QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    except Exception:
        pass

    try:
        if hasattr(Qt.ApplicationAttribute, "AA_UseHighDpiPixmaps"):
            QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
    except Exception:
        pass

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    if platform.system() == "Windows":
        app.setFont(QFont("Segoe UI", 10))

    # Тёмная палитра
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(Colors.BG_DARKEST))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(Colors.TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Base, QColor(Colors.BG_SECONDARY))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(Colors.BG_ELEVATED))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(Colors.BG_ELEVATED))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(Colors.TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Text, QColor(Colors.TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Button, QColor(Colors.BG_SECONDARY))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(Colors.TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.BrightText, QColor(Colors.DANGER))
    palette.setColor(QPalette.ColorRole.Link, QColor(Colors.ACCENT))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(Colors.ACCENT))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(Colors.TEXT_MUTED))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(Colors.TEXT_MUTED))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(Colors.TEXT_MUTED))
    app.setPalette(palette)

    window = MaxApp()
    apply_qt_proxy(window.app_data.get("global", {}).get("proxy", {}))

    window.show()
    sys.exit(app.exec())
