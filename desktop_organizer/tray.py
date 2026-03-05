from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon


class TrayIcon(QSystemTrayIcon):
    """系统托盘图标及其菜单."""

    def __init__(
        self,
        icon: QIcon,
        on_show_settings: Callable[[], None],
        on_toggle_float: Callable[[], None],
        on_quit: Callable[[], None],
    ) -> None:
        super().__init__(icon)

        self._on_show_settings = on_show_settings
        self._on_toggle_float = on_toggle_float
        self._on_quit = on_quit

        self._create_menu()

    def _create_menu(self) -> None:
        menu = QMenu()

        action_show_settings = menu.addAction("打开设置界面")
        action_show_settings.triggered.connect(self._on_show_settings)  # type: ignore[arg-type]

        action_toggle_float = menu.addAction("显示/隐藏悬浮窗")
        action_toggle_float.triggered.connect(self._on_toggle_float)  # type: ignore[arg-type]

        menu.addSeparator()

        action_quit = menu.addAction("退出")
        action_quit.triggered.connect(self._on_quit)  # type: ignore[arg-type]

        self.setContextMenu(menu)

