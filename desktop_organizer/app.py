from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from .config import load_config, save_config
from .float_window import FloatGridWindow
from .models import AppConfig
from .settings_window import SettingsWindow
from .tray import TrayIcon


class OrganizerApplication:
    """PySide6 桌面整理应用的整体封装."""

    def __init__(self) -> None:
        self.qt_app = QApplication(sys.argv)
        self.qt_app.setApplicationName("DesktopOrganizer")

        self.config: AppConfig = load_config()

        # 悬浮窗
        self.float_window = FloatGridWindow(
            self.config,
            on_request_edit_cell=self._on_request_edit_cell,
            on_request_open_settings=self.show_settings,
        )

        # 设置窗口（按需创建）
        self.settings_window: SettingsWindow | None = None

        # 托盘图标
        icon = self._load_default_icon()
        self.tray = TrayIcon(
            icon=icon,
            on_show_settings=self.show_settings,
            on_toggle_float=self.toggle_float_window,
            on_quit=self.quit,
        )
        self.tray.setToolTip("桌面整理工具")
        self.tray.show()

        # 默认显示悬浮窗
        self.float_window.show()

    def _load_default_icon(self) -> QIcon:
        # 暂时使用 Qt 自带的默认图标；后续可以换成项目图标文件
        return QIcon()

    # ---------------- settings & config ----------------
    def show_settings(self) -> None:
        if self.settings_window is None:
            self.settings_window = SettingsWindow(
                app_config=self.config,
                on_config_changed=self._on_config_changed,
            )
        self.settings_window.show()
        self.settings_window.raise_()
        self.settings_window.activateWindow()

    def _on_config_changed(self, config: AppConfig) -> None:
        self.config = config
        save_config(self.config)
        # 更新悬浮窗的图标大小设置
        self.float_window._icon_size = self.config.float_window.icon_size
        self.float_window.reload_from_config()

    def _on_request_edit_cell(self, index: int) -> None:
        # 从悬浮窗触发编辑时，打开设置界面并让用户在其中调整
        self.show_settings()

    # ---------------- float window ----------------
    def toggle_float_window(self) -> None:
        if self.float_window.isVisible():
            self.float_window.hide()
        else:
            self.float_window.show()
            self.float_window.raise_()

    # ---------------- lifecycle ----------------
    def run(self) -> int:
        return self.qt_app.exec()

    def quit(self) -> None:
        # 退出前保存一次位置等信息
        save_config(self.config)
        self.tray.hide()
        self.qt_app.quit()


def main() -> None:
    app = OrganizerApplication()
    sys.exit(app.run())


if __name__ == "__main__":
    main()

