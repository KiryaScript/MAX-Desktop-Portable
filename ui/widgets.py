from typing import Dict

from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame,
    QScrollArea, QGraphicsDropShadowEffect, QGraphicsOpacityEffect
)

from core.constants import APP_NAME, APP_VERSION, Colors


class ToastNotification(QWidget):
    """Анимированное всплывающее уведомление."""

    def __init__(self, parent, message: str, icon: str = "ℹ️",
                 duration: int = 3000, toast_type: str = "info"):
        super().__init__(parent)
        self.setFixedHeight(52)
        self.setMinimumWidth(280)
        self.setMaximumWidth(450)

        border_color = Colors.ACCENT
        if toast_type == "success":
            border_color = Colors.SUCCESS
        elif toast_type == "error":
            border_color = Colors.DANGER
        elif toast_type == "warning":
            border_color = Colors.WARNING

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {Colors.BG_ELEVATED};
                border: 1px solid {border_color};
                border-radius: 12px;
            }}
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-size: 13px;
                font-weight: 500;
                border: none;
                background: transparent;
            }}
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 100))
        self.setGraphicsEffect(shadow)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(10)

        icon_label = QLabel(icon)
        icon_label.setFixedWidth(24)
        icon_label.setStyleSheet("font-size: 18px;")
        layout.addWidget(icon_label)

        text_label = QLabel(message)
        text_label.setWordWrap(True)
        layout.addWidget(text_label)

        # Позиция — правый нижний угол
        parent_rect = parent.rect()
        x = parent_rect.width() - self.width() - 20
        y = parent_rect.height() - self.height() - 20
        self.move(x, y)

        self.show()
        self.raise_()

        QTimer.singleShot(duration, self._fade_out)

    def _fade_out(self):
        try:
            self.deleteLater()
        except Exception:
            pass


class TopBar(QWidget):
    """Верхняя панель приложения (Title Bar)."""

    def __init__(self, host):
        super().__init__(host)
        self.host = host
        self.setFixedHeight(46)
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {Colors.BG_DARKEST};
                border: none;
            }}
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-weight: 600;
                font-size: 13px;
                border: none;
                background: transparent;
            }}
            QPushButton {{
                background-color: transparent;
                color: {Colors.TEXT_SECONDARY};
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {Colors.BG_HOVER};
                color: {Colors.TEXT_PRIMARY};
            }}
            QPushButton:pressed {{
                background-color: {Colors.BG_ELEVATED};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 12, 0)
        layout.setSpacing(4)

        # Логотип
        self.logo_label = QLabel("✦")
        self.logo_label.setStyleSheet(f"color: {Colors.ACCENT}; font-size: 18px; font-weight: bold;")
        layout.addWidget(self.logo_label)

        self.title = QLabel(APP_NAME)
        self.title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-weight: 700; font-size: 13px; letter-spacing: 0.5px;")
        layout.addWidget(self.title)

        self.version_label = QLabel(f"v{APP_VERSION}")
        self.version_label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-weight: 400; font-size: 11px; margin-left: 4px;")
        layout.addWidget(self.version_label)

        layout.addSpacing(16)

        sep = QFrame()
        sep.setFixedSize(1, 22)
        sep.setStyleSheet(f"background-color: {Colors.BORDER};")
        layout.addWidget(sep)
        layout.addSpacing(8)

        # Навигация
        self.btn_back = self._nav_button("◀", "Назад (Alt+Left)")
        self.btn_forward = self._nav_button("▶", "Вперёд (Alt+Right)")
        self.btn_reload = self._nav_button("⟳", "Обновить (Ctrl+R)")

        self.btn_back.clicked.connect(self.host.go_back)
        self.btn_forward.clicked.connect(self.host.go_forward)
        self.btn_reload.clicked.connect(self.host.reload_page)

        layout.addWidget(self.btn_back)
        layout.addWidget(self.btn_forward)
        layout.addWidget(self.btn_reload)

        layout.addStretch()

        # Профиль
        self.profile_label = QLabel("")
        self.profile_label.setStyleSheet(f"""
            color: {Colors.TEXT_SECONDARY};
            font-weight: 500; font-size: 12px;
            padding: 4px 10px;
            background-color: {Colors.BG_SECONDARY};
            border-radius: 10px;
        """)
        layout.addWidget(self.profile_label)
        layout.addSpacing(8)

        # Индикатор подключения
        self.connection_dot = QLabel("●")
        self.connection_dot.setFixedSize(20, 20)
        self.connection_dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.connection_dot.setStyleSheet(f"color: {Colors.SUCCESS}; font-size: 9px;")
        self.connection_dot.setToolTip("Подключено")
        layout.addWidget(self.connection_dot)

    def _nav_button(self, text: str, tooltip: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setFixedSize(32, 32)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setToolTip(tooltip)
        return btn

    def set_connection_status(self, connected: bool):
        if connected:
            self.connection_dot.setStyleSheet(f"color: {Colors.SUCCESS}; font-size: 9px;")
            self.connection_dot.setToolTip("Подключено")
        else:
            self.connection_dot.setStyleSheet(f"color: {Colors.DANGER}; font-size: 9px;")
            self.connection_dot.setToolTip("Нет соединения")


class Sidebar(QWidget):
    """Боковая панель с аккаунтами."""

    profile_clicked = pyqtSignal(int)
    settings_clicked = pyqtSignal()
    add_profile_clicked = pyqtSignal()

    AVATAR_COLORS = [
        ("#6c7bf2", "#8b5cf6"),
        ("#34d399", "#10b981"),
        ("#f87171", "#ef4444"),
        ("#fbbf24", "#f59e0b"),
        ("#60a5fa", "#3b82f6"),
        ("#f472b6", "#ec4899"),
        ("#a78bfa", "#8b5cf6"),
        ("#2dd4bf", "#14b8a6"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(68)
        self.setStyleSheet(f"QWidget {{ background-color: {Colors.BG_DARKEST}; border: none; }}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 12)
        layout.setSpacing(0)

        # Контейнер профилей с прокруткой
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{ border: none; background: transparent; }}
            QScrollArea > QWidget > QWidget {{ background: transparent; }}
        """)

        self.profile_widget = QWidget()
        self.profile_container = QVBoxLayout(self.profile_widget)
        self.profile_container.setContentsMargins(0, 0, 0, 0)
        self.profile_container.setSpacing(6)
        self.profile_container.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        self.scroll_area.setWidget(self.profile_widget)
        layout.addWidget(self.scroll_area)
        layout.addStretch()

        # Разделитель
        sep_container = QWidget()
        sep_container.setFixedHeight(20)
        sep_layout = QHBoxLayout(sep_container)
        sep_layout.setContentsMargins(16, 0, 16, 0)
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {Colors.BORDER};")
        sep_layout.addWidget(sep)
        layout.addWidget(sep_container)

        # Кнопка добавления
        self.btn_add = QPushButton("+")
        self.btn_add.setFixedSize(42, 42)
        self.btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add.setToolTip("Добавить профиль (Ctrl+T)")
        self.btn_add.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; color: {Colors.TEXT_MUTED};
                border: 2px dashed {Colors.BORDER}; border-radius: 14px;
                font-size: 20px; font-weight: 300;
            }}
            QPushButton:hover {{
                color: {Colors.ACCENT}; border-color: {Colors.ACCENT};
                background-color: {Colors.ACCENT_GLOW};
            }}
        """)
        self.btn_add.clicked.connect(self.add_profile_clicked.emit)
        layout.addWidget(self.btn_add, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addSpacing(8)

        # Кнопка настроек
        self.btn_settings = QPushButton("⚙")
        self.btn_settings.setFixedSize(42, 42)
        self.btn_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_settings.setToolTip("Настройки")
        self.btn_settings.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent; color: {Colors.TEXT_MUTED};
                border: none; border-radius: 14px; font-size: 20px;
            }}
            QPushButton:hover {{
                color: {Colors.TEXT_PRIMARY}; background-color: {Colors.BG_HOVER};
            }}
        """)
        self.btn_settings.clicked.connect(self.settings_clicked.emit)
        layout.addWidget(self.btn_settings, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.profile_buttons: Dict[int, QPushButton] = {}

    def _clear_profile_container(self):
        while self.profile_container.count():
            item = self.profile_container.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        for button in self.profile_buttons.values():
            button.deleteLater()
        self.profile_buttons = {}

    def rebuild(self, names, active_index: int):
        self._clear_profile_container()
        for index, name in enumerate(names):
            label = name.strip()[0].upper() if name.strip() else "M"
            color_pair = self.AVATAR_COLORS[index % len(self.AVATAR_COLORS)]

            button = QPushButton(label)
            button.setFixedSize(42, 42)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setToolTip(name)
            button.clicked.connect(lambda checked=False, i=index: self.profile_clicked.emit(i))
            button.setProperty("color_start", color_pair[0])
            button.setProperty("color_end", color_pair[1])

            self.profile_container.addWidget(button, alignment=Qt.AlignmentFlag.AlignHCenter)
            self.profile_buttons[index] = button
        self.set_active(active_index)

    def set_active(self, active_index: int):
        for index, button in self.profile_buttons.items():
            c1 = button.property("color_start") or Colors.ACCENT
            c2 = button.property("color_end") or Colors.ACCENT_HOVER
            if index == active_index:
                button.setStyleSheet(f"""
                    QPushButton {{
                        background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {c1}, stop:1 {c2});
                        color: white; border-radius: 14px;
                        font-size: 16px; font-weight: 700; border: none;
                    }}
                """)
            else:
                button.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {Colors.BG_SECONDARY}; color: {Colors.TEXT_SECONDARY};
                        border-radius: 14px; font-size: 16px; font-weight: 600; border: none;
                    }}
                    QPushButton:hover {{
                        background-color: {Colors.BG_HOVER}; color: {Colors.TEXT_PRIMARY};
                    }}
                """)


class StatusBar(QWidget):
    """Нижняя статус-панель."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(26)
        self.setStyleSheet(f"""
            QWidget {{ background-color: {Colors.BG_DARKEST}; border-top: 1px solid {Colors.BORDER}; }}
            QLabel {{ color: {Colors.TEXT_MUTED}; font-size: 11px; border: none; background: transparent; }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(16)

        self.url_label = QLabel("")
        layout.addWidget(self.url_label)
        layout.addStretch()

        self.zoom_label = QLabel("100%")
        layout.addWidget(self.zoom_label)

        sep = QLabel("│")
        sep.setStyleSheet(f"color: {Colors.BORDER};")
        layout.addWidget(sep)

        self.profile_label = QLabel("")
        layout.addWidget(self.profile_label)

    def update_url(self, url: str):
        if len(url) > 80:
            url = url[:77] + "…"
        self.url_label.setText(url)

    def update_zoom(self, zoom: float):
        self.zoom_label.setText(f"{int(zoom * 100)}%")

    def update_profile(self, name: str):
        self.profile_label.setText(f"📎 {name}")
