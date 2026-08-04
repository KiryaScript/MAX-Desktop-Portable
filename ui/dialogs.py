import os
import json
import platform
import datetime
import shutil
import ctypes
import sys
from pathlib import Path

from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtGui import QIcon, QDesktopServices
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QComboBox, QFormLayout, QTabWidget, QCheckBox, QMessageBox,
    QLineEdit, QInputDialog, QWidget, QScrollArea, QApplication, QFileDialog
)

from core.constants import (
    APP_NAME, APP_VERSION, Colors, GLOBAL_TOOLTIP_STYLE,
    MASKS_DB, THEMES, DEFAULT_PROXY,
    resource_path, get_app_dir, get_windows_downloads_folder
)
from core.network import apply_qt_proxy


class SettingsDialog(QDialog):
    """Диалог настроек — полностью переработанный."""

    def __init__(self, main_app):
        super().__init__(main_app)
        self.main_app = main_app
        self.setWindowTitle(f"Настройки — {APP_NAME}")
        self.setMinimumSize(760, 700)
        self.resize(760, 700)

        icon_path = resource_path("max.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {Colors.BG_PRIMARY};
                font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            }}
            QTabWidget::pane {{ border: none; background-color: {Colors.BG_PRIMARY}; }}
            QTabBar {{ background: {Colors.BG_DARKEST}; }}
            QTabBar::tab {{
                background: transparent; color: {Colors.TEXT_MUTED};
                padding: 14px 20px; font-size: 13px; font-weight: 600;
                border: none; border-bottom: 2px solid transparent; min-width: 80px;
            }}
            QTabBar::tab:hover {{ color: {Colors.TEXT_SECONDARY}; background-color: {Colors.BG_DARK}; }}
            QTabBar::tab:selected {{ color: {Colors.TEXT_PRIMARY}; border-bottom: 2px solid {Colors.ACCENT}; }}
            QLabel {{ color: {Colors.TEXT_PRIMARY}; font-size: 13px; font-weight: 500; }}
            QComboBox, QLineEdit {{
                background-color: {Colors.BG_SECONDARY}; color: {Colors.TEXT_PRIMARY};
                font-size: 13px; padding: 10px 14px; border-radius: 8px;
                border: 1px solid {Colors.BORDER}; selection-background-color: {Colors.ACCENT};
            }}
            QComboBox:hover, QLineEdit:hover {{ border-color: {Colors.BORDER_HOVER}; }}
            QComboBox:focus, QLineEdit:focus {{ border-color: {Colors.ACCENT}; }}
            QComboBox::drop-down {{ border: none; width: 30px; }}
            QComboBox::down-arrow {{
                border-left: 4px solid transparent; border-right: 4px solid transparent;
                border-top: 5px solid {Colors.TEXT_MUTED}; margin-right: 10px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {Colors.BG_ELEVATED}; color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER}; selection-background-color: {Colors.ACCENT};
                outline: none; border-radius: 8px; padding: 4px;
            }}
            QCheckBox {{ color: {Colors.TEXT_PRIMARY}; font-size: 13px; spacing: 10px; }}
            QCheckBox::indicator {{
                width: 18px; height: 18px; border-radius: 4px;
                border: 2px solid {Colors.TEXT_MUTED}; background: transparent;
            }}
            QCheckBox::indicator:hover {{ border: 2px solid {Colors.TEXT_SECONDARY}; }}
            QCheckBox::indicator:checked {{ background-color: {Colors.ACCENT}; border: 2px solid {Colors.ACCENT}; }}
            QPushButton {{
                background-color: {Colors.ACCENT}; color: white; padding: 10px 20px;
                border-radius: 8px; font-size: 13px; font-weight: 600; border: none;
            }}
            QPushButton:hover {{ background-color: {Colors.ACCENT_HOVER}; }}
            QPushButton:pressed {{ background-color: {Colors.ACCENT_ACTIVE}; }}
            QPushButton#danger {{
                background-color: transparent; color: {Colors.DANGER}; border: 1px solid {Colors.DANGER};
            }}
            QPushButton#danger:hover {{ background-color: {Colors.DANGER}; color: white; }}
            QPushButton#success {{
                background-color: transparent; color: {Colors.SUCCESS}; border: 1px solid {Colors.SUCCESS};
            }}
            QPushButton#success:hover {{ background-color: {Colors.SUCCESS}; color: white; }}
            QPushButton#ghost {{
                background-color: transparent; color: {Colors.TEXT_SECONDARY}; border: 1px solid {Colors.BORDER};
            }}
            QPushButton#ghost:hover {{
                background-color: {Colors.BG_HOVER}; color: {Colors.TEXT_PRIMARY}; border-color: {Colors.BORDER_HOVER};
            }}
            {GLOBAL_TOOLTIP_STYLE}
        """)

        active_browser = self.main_app.get_active_browser()
        config = active_browser.config if active_browser else {}
        global_config = self.main_app.app_data.get("global", {})
        proxy_cfg = global_config.get("proxy", config.get("proxy", DEFAULT_PROXY))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Заголовок
        header = QWidget()
        header.setFixedHeight(56)
        header.setStyleSheet(f"background-color: {Colors.BG_DARKEST};")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 0, 24, 0)

        header_title = QLabel("⚙  Настройки")
        header_title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: 16px; font-weight: 700;")
        header_layout.addWidget(header_title)
        header_layout.addStretch()

        header_version = QLabel(f"v{APP_VERSION}")
        header_version.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 12px; font-weight: 400;")
        header_layout.addWidget(header_version)
        layout.addWidget(header)

        tabs = QTabWidget()

        def create_padded_form():
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setStyleSheet(f"""
                QScrollArea {{ border: none; background: transparent; }}
                QScrollArea > QWidget > QWidget {{ background: transparent; }}
            """)
            widget = QWidget()
            form = QFormLayout(widget)
            form.setContentsMargins(32, 28, 32, 28)
            form.setVerticalSpacing(18)
            form.setHorizontalSpacing(24)
            scroll.setWidget(widget)
            return scroll, widget, form

        tab_prof_scroll, tab_prof, form_prof = create_padded_form()
        tab_priv_scroll, tab_priv, form_priv = create_padded_form()
        tab_proxy_scroll, tab_proxy, form_proxy = create_padded_form()
        tab_look_scroll, tab_look, form_look = create_padded_form()
        tab_sys_scroll, tab_sys, form_sys = create_padded_form()

        tab_support = QWidget()
        form_support = QVBoxLayout(tab_support)
        form_support.setContentsMargins(32, 28, 32, 28)
        form_support.setSpacing(16)

        # ── ПРОФИЛЬ ──
        self.profile_combo = QComboBox()
        self.profile_combo.blockSignals(True)
        self.profile_combo.addItems(self.main_app.app_data["profiles"].keys())
        if self.main_app.app_data["profiles"]:
            self.profile_combo.setCurrentIndex(max(0, self.main_app.browser_stack.currentIndex()))
        self.profile_combo.blockSignals(False)
        self.profile_combo.currentIndexChanged.connect(self.main_app.switch_profile)
        form_prof.addRow("Текущий аккаунт:", self.profile_combo)

        btn_add = QPushButton("＋  Добавить профиль")
        btn_add.setObjectName("success")
        btn_add.clicked.connect(self.add_profile_dialog)
        form_prof.addRow("Мультиаккаунт:", btn_add)

        btn_delete = QPushButton("🗑  Удалить профиль")
        btn_delete.setObjectName("danger")
        btn_delete.clicked.connect(self.delete_profile_dialog)
        form_prof.addRow("", btn_delete)

        # ── ПРИВАТНОСТЬ ──
        self._add_section_header(form_priv, "🎭 Маскировка устройства")

        self.mask_combo = QComboBox()
        self.mask_combo.addItems(MASKS_DB.keys())
        self.mask_combo.setCurrentText(config.get("mask", "Windows 11 (Chrome)"))
        form_priv.addRow("Подмена ОС:", self.mask_combo)

        self._add_section_header(form_priv, "🛡 Защита")

        self.cb_webrtc = QCheckBox("Запретить утечку IP (WebRTC Strict)")
        self.cb_webrtc.setChecked(config.get("webrtc_leak", False))
        form_priv.addRow("Сеть:", self.cb_webrtc)

        self.cb_canvas = QCheckBox("Шум на Canvas (Анти-трекинг)")
        self.cb_canvas.setChecked(config.get("canvas_noise", True))
        form_priv.addRow("Графика:", self.cb_canvas)

        self.cb_audio = QCheckBox("Шум AudioContext (Анти-трекинг)")
        self.cb_audio.setChecked(config.get("audio_noise", True))
        form_priv.addRow("Звук:", self.cb_audio)

        self.cb_adblock = QCheckBox("Встроенный AdBlock")
        self.cb_adblock.setChecked(config.get("adblock", False))
        form_priv.addRow("Реклама:", self.cb_adblock)

        # ── ПРОКСИ ──
        self.proxy_type = QComboBox()
        self.proxy_type.addItems(["Нет", "HTTP", "SOCKS5"])
        self.proxy_type.setCurrentText(proxy_cfg.get("type", "Нет"))

        self.proxy_host = QLineEdit()
        self.proxy_host.setText(proxy_cfg.get("host", ""))
        self.proxy_host.setPlaceholderText("IP / Host")

        self.proxy_port = QLineEdit()
        self.proxy_port.setText(str(proxy_cfg.get("port", "")))
        self.proxy_port.setPlaceholderText("Port")

        proxy_note = QLabel("Прокси сохраняется глобально. Для QtWebEngine может потребоваться перезапуск.")
        proxy_note.setWordWrap(True)
        proxy_note.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-weight: 400; font-size: 12px;")

        form_proxy.addRow("Тип прокси:", self.proxy_type)
        form_proxy.addRow("Хост / IP:", self.proxy_host)
        form_proxy.addRow("Порт:", self.proxy_port)
        form_proxy.addRow("", proxy_note)

        # ── ВИД ──
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(THEMES.keys())
        self.theme_combo.setCurrentText(config.get("theme", "Telegram Dark"))
        form_look.addRow("Тема MAX:", self.theme_combo)

        self.zoom_combo = QComboBox()
        self.zoom_combo.addItems(["80%", "90%", "100%", "110%", "125%", "150%"])
        self.zoom_combo.setCurrentText(config.get("zoom", "100%"))
        form_look.addRow("Масштаб:", self.zoom_combo)

        self.cb_scroll = QCheckBox("Скрыть полосы прокрутки")
        self.cb_scroll.setChecked(config.get("hide_scrollbars", False))
        form_look.addRow("Скроллбары:", self.cb_scroll)

        # ── СИСТЕМА ──
        self.cb_mute = QCheckBox("Отключить звуки вкладки")
        self.cb_mute.setChecked(config.get("mute_audio", False))
        form_sys.addRow("Звук:", self.cb_mute)

        self.cb_tray = QCheckBox("Сворачивать в трей при закрытии")
        self.cb_tray.setChecked(global_config.get("close_to_tray", True))
        form_sys.addRow("Фон:", self.cb_tray)

        self.cb_save_window = QCheckBox("Запоминать размер и положение окна")
        self.cb_save_window.setChecked(global_config.get("save_window_state", True))
        form_sys.addRow("Окно:", self.cb_save_window)

        self._add_section_header(form_sys, "🗑 Данные")

        self.dl_path_edit = QLineEdit(global_config.get("download_path", ""))
        self.dl_path_edit.setPlaceholderText("По умолчанию (системная папка Загрузки)")
        btn_dl_browse = QPushButton("...")
        btn_dl_browse.setFixedWidth(40)
        btn_dl_browse.clicked.connect(self.browse_download_path)
        
        dl_layout = QHBoxLayout()
        dl_layout.setContentsMargins(0, 0, 0, 0)
        dl_layout.addWidget(self.dl_path_edit)
        dl_layout.addWidget(btn_dl_browse)
        form_sys.addRow("Папка загрузок:", dl_layout)

        btn_clear_cache = QPushButton("Очистить кэш и историю")
        btn_clear_cache.setObjectName("danger")
        btn_clear_cache.clicked.connect(self.clear_cache)
        form_sys.addRow("Кэш:", btn_clear_cache)

        btn_open_downloads = QPushButton("📁  Открыть папку загрузок")
        btn_open_downloads.setObjectName("ghost")
        btn_open_downloads.clicked.connect(self.open_downloads_folder)
        form_sys.addRow("Открыть:", btn_open_downloads)

        btn_open_appdir = QPushButton("📂  Открыть папку приложения")
        btn_open_appdir.setObjectName("ghost")
        btn_open_appdir.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(get_app_dir()))))
        form_sys.addRow("Каталог:", btn_open_appdir)

        # ── ПОДДЕРЖКА ──
        lbl_support = QLabel(
            "Возникли ошибки или баги в работе клиента?\n\n"
            "Создайте диагностический файл. Он соберёт базовую информацию о системе, "
            "версии Python, диске и текущих настройках программы.\n\n"
            "После создания файла откроется Telegram."
        )
        lbl_support.setWordWrap(True)
        lbl_support.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-weight: 400; font-size: 13px;")

        btn_report = QPushButton("🛠  Создать отчёт и открыть Telegram")
        btn_report.setObjectName("danger")
        btn_report.clicked.connect(self.generate_support_report)

        about_label = QLabel(
            f"\n{APP_NAME} v{APP_VERSION}\n"
            f"Python {platform.python_version()}\n"
            f"{platform.system()} {platform.release()}"
        )
        about_label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 12px; font-weight: 400;")

        form_support.addWidget(lbl_support)
        form_support.addWidget(btn_report)
        form_support.addStretch()
        form_support.addWidget(about_label)

        tabs.addTab(tab_prof_scroll, "  Профиль  ")
        tabs.addTab(tab_priv_scroll, "  Приватность  ")
        tabs.addTab(tab_proxy_scroll, "  Прокси  ")
        tabs.addTab(tab_look_scroll, "  Вид  ")
        tabs.addTab(tab_sys_scroll, "  Система  ")
        tabs.addTab(tab_support, "  Поддержка  ")
        layout.addWidget(tabs)

        # Нижняя панель
        bottom_widget = QWidget()
        bottom_widget.setFixedHeight(64)
        bottom_widget.setStyleSheet(f"""
            QWidget {{ background-color: {Colors.BG_DARKEST}; border-top: 1px solid {Colors.BORDER}; }}
        """)
        bottom_layout = QHBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(24, 0, 24, 0)

        btn_cancel = QPushButton("Отмена")
        btn_cancel.setObjectName("ghost")
        btn_cancel.clicked.connect(self.reject)
        bottom_layout.addWidget(btn_cancel)
        bottom_layout.addStretch()

        btn_apply = QPushButton("✓  Сохранить и применить")
        btn_apply.setMinimumWidth(200)
        btn_apply.clicked.connect(self.save_and_apply)
        bottom_layout.addWidget(btn_apply)
        layout.addWidget(bottom_widget)

    def _add_section_header(self, form, text: str):
        label = QLabel(text)
        label.setStyleSheet(f"""
            color: {Colors.TEXT_MUTED}; font-size: 11px; font-weight: 700;
            letter-spacing: 1px; padding-top: 12px;
        """)
        form.addRow(label)

    def refresh_profile_combo(self, selected: str = None):
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        self.profile_combo.addItems(self.main_app.app_data["profiles"].keys())
        if selected and selected in self.main_app.app_data["profiles"]:
            self.profile_combo.setCurrentText(selected)
        else:
            self.profile_combo.setCurrentIndex(max(0, self.main_app.browser_stack.currentIndex()))
        self.profile_combo.blockSignals(False)

    def add_profile_dialog(self):
        text, ok = QInputDialog.getText(self, "Новый аккаунт", "Название профиля:")
        if not ok or not text.strip():
            return
        text = text.strip()
        if text not in self.main_app.app_data["profiles"]:
            self.main_app.add_profile(text)
        self.refresh_profile_combo(text)

    def delete_profile_dialog(self):
        names = list(self.main_app.app_data["profiles"].keys())
        if len(names) <= 1:
            QMessageBox.warning(self, "Удаление", "Нельзя удалить единственный профиль.")
            return
        current_name = self.profile_combo.currentText()
        reply = QMessageBox.question(
            self, "Удалить профиль",
            f"Удалить профиль «{current_name}»?\n\nВсе данные профиля будут удалены безвозвратно.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.main_app.delete_profile(current_name)
            self.refresh_profile_combo()

    def open_downloads_folder(self):
        custom_path = self.dl_path_edit.text().strip()
        downloads_dir = Path(custom_path) if custom_path else Path(get_windows_downloads_folder())
        downloads_dir.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(downloads_dir)))

    def browse_download_path(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку загрузок", self.dl_path_edit.text() or get_windows_downloads_folder())
        if folder:
            self.dl_path_edit.setText(folder)

    def clear_cache(self):
        active_browser = self.main_app.get_active_browser()
        if not active_browser:
            QMessageBox.information(self, "Кэш", "Активный профиль не найден.")
            return
        try:
            active_browser.profile.clearHttpCache()
        except Exception:
            pass
        try:
            active_browser.profile.clearAllVisitedHistory()
        except Exception:
            pass
        QMessageBox.information(self, "Готово", "Кэш и история успешно очищены.")

    def save_and_apply(self):
        self.main_app.app_data.setdefault("global", {})["close_to_tray"] = self.cb_tray.isChecked()
        self.main_app.app_data.setdefault("global", {})["save_window_state"] = self.cb_save_window.isChecked()
        self.main_app.app_data.setdefault("global", {})["download_path"] = self.dl_path_edit.text().strip()

        old_proxy = self.main_app.app_data.get("global", {}).get("proxy", {}).copy()
        new_proxy = {
            "type": self.proxy_type.currentText(),
            "host": self.proxy_host.text().strip(),
            "port": self.proxy_port.text().strip()
        }
        self.main_app.app_data.setdefault("global", {})["proxy"] = new_proxy
        apply_qt_proxy(new_proxy)

        active_browser = self.main_app.get_active_browser()
        if active_browser:
            active_browser.config.update({
                "mask": self.mask_combo.currentText(),
                "webrtc_leak": self.cb_webrtc.isChecked(),
                "canvas_noise": self.cb_canvas.isChecked(),
                "audio_noise": self.cb_audio.isChecked(),
                "adblock": self.cb_adblock.isChecked(),
                "theme": self.theme_combo.currentText(),
                "zoom": self.zoom_combo.currentText(),
                "hide_scrollbars": self.cb_scroll.isChecked(),
                "mute_audio": self.cb_mute.isChecked(),
                "proxy": new_proxy
            })
            active_browser.apply_all_settings()
            try:
                active_browser.browser.reload()
            except Exception:
                pass

        self.main_app.save_config()

        if json.dumps(old_proxy, sort_keys=True) != json.dumps(new_proxy, sort_keys=True):
            QMessageBox.information(
                self, "Прокси",
                "Прокси сохранён.\n\nДля полного применения может потребоваться перезапуск."
            )
        self.accept()

    def get_ram_info(self):
        try:
            if platform.system() == "Windows":
                kernel32 = ctypes.windll.kernel32
                c_ulonglong = ctypes.c_ulonglong

                class MEMORYSTATUSEX(ctypes.Structure):
                    _fields_ = [
                        ("dwLength", ctypes.c_ulong),
                        ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", c_ulonglong),
                        ("ullAvailPhys", c_ulonglong),
                        ("ullTotalPageFile", c_ulonglong),
                        ("ullAvailPageFile", c_ulonglong),
                        ("ullTotalVirtual", c_ulonglong),
                        ("ullAvailVirtual", c_ulonglong),
                        ("sullAvailExtendedVirtual", c_ulonglong),
                    ]

                memory_status = MEMORYSTATUSEX()
                memory_status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
                kernel32.GlobalMemoryStatusEx(ctypes.byref(memory_status))
                total_ram = memory_status.ullTotalPhys / (1024 ** 3)
                avail_ram = memory_status.ullAvailPhys / (1024 ** 3)
                return f"{total_ram:.1f} ГБ (Доступно: {avail_ram:.1f} ГБ)"
            return "Недоступно (не Windows)"
        except Exception as e:
            return f"Ошибка чтения RAM: {e}"

    def generate_support_report(self):
        report = []
        report.append(f"=== {APP_NAME} v{APP_VERSION} — Diagnostic Report ===")
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
            report.append("Разрешение экрана: недоступно")

        report.append("\n--- ПРИЛОЖЕНИЕ И ДИСК ---")
        app_dir = get_app_dir()
        is_portable = getattr(sys, "frozen", False)
        try:
            total, used, free = shutil.disk_usage(app_dir)
            report.append(f"Диск: Свободно {free // (1024 ** 3)} ГБ из {total // (1024 ** 3)} ГБ")
        except Exception:
            report.append("Диск: Ошибка доступа")

        report.append(f"Тип запуска: {'Compiled (.exe)' if is_portable else 'Python Script'}")
        report.append(f"Рабочая папка: {app_dir}")
        report.append(f"Python: {platform.python_version()}")

        active_browser = self.main_app.get_active_browser()
        if active_browser:
            try:
                report.append(f"UserAgent: {active_browser.profile.httpUserAgent()}")
            except Exception:
                pass

        report.append("\n=== APP CONFIGURATION (JSON) ===")
        report.append(json.dumps(self.main_app.app_data, indent=4, ensure_ascii=False))

        try:
            desktop = Path.home() / "Desktop"
            if not desktop.exists():
                desktop = Path.home()
            report_path = desktop / "MAX_Support_Report.txt"
            report_path.write_text("\n".join(report), encoding="utf-8")
            QMessageBox.information(
                self, "Отчёт создан",
                f"Файл сохранён:\n\n{report_path}\n\nСейчас откроется Telegram."
            )
            QDesktopServices.openUrl(QUrl("https://t.me/devjijlk"))
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить отчёт:\n{e}")


class ShortcutsOverlay(QDialog):
    """Оверлей с горячими клавишами."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Горячие клавиши")
        self.setFixedSize(420, 380)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {Colors.BG_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 12px;
            }}
            QLabel {{ color: {Colors.TEXT_PRIMARY}; font-size: 13px; }}
        """)

        icon_path = resource_path("max.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(8)

        title = QLabel("⌨  Горячие клавиши")
        title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-size: 16px; font-weight: 700;")
        layout.addWidget(title)
        layout.addSpacing(12)

        shortcuts = [
            ("Ctrl + T", "Новый профиль"),
            ("Ctrl + W", "Закрыть окно"),
            ("Ctrl + R / F5", "Обновить страницу"),
            ("Ctrl + Shift + S", "Настройки"),
            ("Ctrl + колесо", "Масштаб страницы"),
            ("Alt + ←", "Назад"),
            ("Alt + →", "Вперёд"),
            ("Ctrl + 1-9", "Переключение профилей"),
            ("F1", "Горячие клавиши"),
        ]

        for key, desc in shortcuts:
            row = QHBoxLayout()
            key_label = QLabel(key)
            key_label.setFixedWidth(160)
            key_label.setStyleSheet(f"""
                color: {Colors.ACCENT};
                font-family: 'Consolas', 'Courier New', monospace;
                font-weight: 600; font-size: 12px;
                background-color: {Colors.BG_SECONDARY};
                padding: 4px 10px; border-radius: 4px;
            """)
            desc_label = QLabel(desc)
            desc_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 13px;")
            row.addWidget(key_label)
            row.addWidget(desc_label)
            row.addStretch()
            layout.addLayout(row)
        layout.addStretch()
