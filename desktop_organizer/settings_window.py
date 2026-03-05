from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional, List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QLineEdit,
    QSpinBox,
    QTabWidget,
    QGroupBox,
    QFormLayout,
    QSlider,
    QCheckBox,
    QScrollArea,
    QFrame,
)

from .config import save_config
from .models import AppConfig, GridCell, DesktopGroup
from .auto_sort import get_desktop_path


class CellEditDialog(QDialog):
    """编辑单个格子的对话框."""

    def __init__(self, cell: GridCell, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("编辑应用")
        self._cell = cell
        self.setFixedSize(400, 300)

        layout = QVBoxLayout(self)

        # 标题
        title_label = QLabel("编辑应用信息")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title_label)

        form_layout = QFormLayout()

        self.title_edit = QLineEdit(self)
        self.title_edit.setText(cell.title)
        self.title_edit.setPlaceholderText("输入应用名称")
        form_layout.addRow("显示名称：", self.title_edit)

        self.path_edit = QLineEdit(self)
        self.path_edit.setText(cell.target_path or "")
        self.path_edit.setPlaceholderText("选择应用文件路径")
        btn_browse = QPushButton("浏览...")
        btn_browse.clicked.connect(self._on_browse)
        path_layout = QHBoxLayout()
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(btn_browse)
        path_container = QWidget(self)
        path_container.setLayout(path_layout)
        form_layout.addRow("应用路径：", path_container)

        self.icon_edit = QLineEdit(self)
        self.icon_edit.setText(cell.icon_path or "")
        self.icon_edit.setPlaceholderText("选择自定义图标（可选）")
        btn_icon = QPushButton("浏览...")
        btn_icon.clicked.connect(self._on_browse_icon)
        icon_layout = QHBoxLayout()
        icon_layout.addWidget(self.icon_edit)
        icon_layout.addWidget(btn_icon)
        icon_container = QWidget(self)
        icon_container.setLayout(icon_layout)
        form_layout.addRow("自定义图标：", icon_container)

        layout.addLayout(form_layout)

        # 按钮
        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("保存")
        btn_cancel = QPushButton("取消")
        btn_ok.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)
        
        btn_ok.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_ok)
        layout.addLayout(btn_layout)

    def _on_browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, 
            "选择应用文件", 
            "", 
            "所有文件 (*.*)"
        )
        if path:
            self.path_edit.setText(path)

    def _on_browse_icon(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, 
            "选择图标文件", 
            "", 
            "图标文件 (*.png *.jpg *.ico *.svg)"
        )
        if path:
            self.icon_edit.setText(path)

    def apply_changes(self) -> None:
        self._cell.title = self.title_edit.text().strip()
        self._cell.target_path = self.path_edit.text().strip() or None
        self._cell.icon_path = self.icon_edit.text().strip() or None


class SimpleSettingsWindow(QWidget):
    """简化的设置界面，让普通用户能轻松上手."""

    def __init__(
        self,
        app_config: AppConfig,
        on_config_changed: Callable[[AppConfig], None],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("桌面整理设置")
        self.setMinimumSize(600, 500)
        self._config = app_config
        self._on_config_changed = on_config_changed

        self._init_ui()

    def _close_window(self) -> None:
        """安全关闭设置窗口，不影响主应用."""
        self.hide()
        
    def closeEvent(self, event) -> None:
        """重写关闭事件，只隐藏窗口而不销毁."""
        event.ignore()
        self.hide()

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        
        # 标题
        title_label = QLabel("桌面整理设置")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; margin: 10px;")
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        # 选项卡
        tab_widget = QTabWidget()
        
        # 应用管理选项卡
        app_tab = self._create_app_management_tab()
        tab_widget.addTab(app_tab, "📱 应用管理")
        
        # 外观设置选项卡
        appearance_tab = self._create_appearance_tab()
        tab_widget.addTab(appearance_tab, "🎨 外观设置")
        
        # 高级设置选项卡
        advanced_tab = self._create_advanced_tab()
        tab_widget.addTab(advanced_tab, "⚙️ 高级设置")
        
        main_layout.addWidget(tab_widget)
        
        # 底部按钮
        bottom_layout = QHBoxLayout()
        save_btn = QPushButton("保存设置")
        save_btn.clicked.connect(self._save_config)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self._close_window)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #9E9E9E;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #757575;
            }
        """)
        
        bottom_layout.addStretch()
        bottom_layout.addWidget(close_btn)
        bottom_layout.addWidget(save_btn)
        main_layout.addLayout(bottom_layout)

    def _create_app_management_tab(self) -> QWidget:
        """创建应用管理选项卡."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 说明文字
        info_label = QLabel("在这里管理您的应用快捷方式")
        info_label.setStyleSheet("color: #666; margin-bottom: 10px;")
        layout.addWidget(info_label)

        # 应用列表
        list_frame = QFrame()
        list_frame.setFrameStyle(QFrame.Box)
        list_layout = QVBoxLayout(list_frame)

        self.app_list = QListWidget()
        self._refresh_app_list()
        list_layout.addWidget(self.app_list)

        # 操作按钮
        btn_layout = QHBoxLayout()
        
        add_btn = QPushButton("➕ 添加应用")
        add_btn.clicked.connect(self._add_app)
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        edit_btn = QPushButton("✏️ 编辑")
        edit_btn.clicked.connect(self._edit_app)
        edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                padding: 8px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        
        delete_btn = QPushButton("🗑️ 删除")
        delete_btn.clicked.connect(self._delete_app)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 8px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(edit_btn)
        btn_layout.addWidget(delete_btn)
        btn_layout.addStretch()
        
        list_layout.addLayout(btn_layout)
        layout.addWidget(list_frame)

        # 使用说明
        help_frame = QGroupBox("💡 使用提示")
        help_layout = QVBoxLayout(help_frame)
        
        help_text = QLabel(
            "• 点击'添加应用'选择要添加的程序或文件\n"
            "• 选中列表中的应用后点击'编辑'修改信息\n"
            "• 点击'删除'移除不需要的应用\n"
            "• 您也可以直接拖拽文件到悬浮窗来添加应用"
        )
        help_text.setWordWrap(True)
        help_text.setStyleSheet("color: #666; line-height: 1.5;")
        help_layout.addWidget(help_text)
        
        layout.addWidget(help_frame)
        layout.addStretch()

        return tab

    def _create_appearance_tab(self) -> QWidget:
        """创建外观设置选项卡."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 窗口设置
        window_group = QGroupBox("🪟 窗口设置")
        window_layout = QFormLayout(window_group)

        # 窗口标题
        self.title_edit = QLineEdit(self._config.float_window.title)
        self.title_edit.setPlaceholderText("输入窗口标题")
        window_layout.addRow("窗口标题：", self.title_edit)

        # 透明度
        opacity_slider = QSlider(Qt.Horizontal)
        opacity_slider.setRange(10, 100)
        opacity_slider.setValue(int(self._config.float_window.opacity * 100))
        opacity_label = QLabel(f"{opacity_slider.value()}%")
        opacity_slider.valueChanged.connect(lambda v: opacity_label.setText(f"{v}%"))
        
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(opacity_slider)
        opacity_layout.addWidget(opacity_label)
        window_layout.addRow("窗口透明度：", opacity_layout)

        # 窗口大小
        size_layout = QHBoxLayout()
        width_spin = QSpinBox()
        width_spin.setRange(440, 1200)  # 最小440px确保5列布局
        width_spin.setValue(self._config.float_window.width)
        height_spin = QSpinBox()
        height_spin.setRange(200, 1000)
        height_spin.setValue(self._config.float_window.height)
        size_layout.addWidget(QLabel("宽度："))
        size_layout.addWidget(width_spin)
        size_layout.addWidget(QLabel("高度："))
        size_layout.addWidget(height_spin)
        size_layout.addStretch()
        window_layout.addRow("窗口大小：", size_layout)

        # 图标大小
        icon_size_slider = QSlider(Qt.Horizontal)
        icon_size_slider.setRange(16, 128)
        icon_size_slider.setValue(self._config.float_window.icon_size)
        icon_size_label = QLabel(f"{icon_size_slider.value()}px")
        icon_size_slider.valueChanged.connect(lambda v: icon_size_label.setText(f"{v}px"))
        
        icon_size_layout = QHBoxLayout()
        icon_size_layout.addWidget(icon_size_slider)
        icon_size_layout.addWidget(icon_size_label)
        window_layout.addRow("图标大小：", icon_size_layout)

        layout.addWidget(window_group)

        # 格子设置
        grid_group = QGroupBox("📐 格子设置")
        grid_layout = QFormLayout(grid_group)

        # 固定5列的说明
        cols_label = QLabel("固定5列（不可修改）")
        cols_label.setStyleSheet("color: #666;")
        grid_layout.addRow("每行列数：", cols_label)

        layout.addWidget(grid_group)
        layout.addStretch()

        # 保存引用
        self.opacity_slider = opacity_slider
        self.width_spin = width_spin
        self.height_spin = height_spin
        self.icon_size_slider = icon_size_slider

        return tab

    def _create_advanced_tab(self) -> QWidget:
        """创建高级设置选项卡."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # 高级选项
        advanced_group = QGroupBox("🔧 高级选项")
        advanced_layout = QVBoxLayout(advanced_group)

        # 锁定位置
        self.lock_checkbox = QCheckBox("锁定窗口位置（防止意外移动）")
        self.lock_checkbox.setChecked(self._config.float_window.locked)
        advanced_layout.addWidget(self.lock_checkbox)

        # 重置设置
        reset_btn = QPushButton("🔄 重置所有设置")
        reset_btn.clicked.connect(self._reset_settings)
        reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF5722;
                color: white;
                border: none;
                padding: 8px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #E64A19;
            }
        """)
        advanced_layout.addWidget(reset_btn)

        layout.addWidget(advanced_group)
        layout.addStretch()

        return tab

    def _refresh_app_list(self) -> None:
        """刷新应用列表."""
        self.app_list.clear()
        
        for group in self._config.groups:
            for i, cell in enumerate(group.grid.cells):
                if cell.target_path:
                    item_text = f"{cell.title or '未命名'} - {Path(cell.target_path).name}"
                    item = QListWidgetItem(item_text)
                    item.setData(Qt.UserRole, (group, i))
                    self.app_list.addItem(item)

    def _add_app(self) -> None:
        """添加新应用."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择应用文件", "", "所有文件 (*.*)"
        )
        
        if file_path:
            p = Path(file_path)
            # 添加到第一个分组
            if not self._config.groups:
                self._config.groups.append(DesktopGroup(name="我的应用"))
            
            first_group = self._config.groups[0]
            new_cell = GridCell(target_path=str(p), title=p.stem)
            first_group.grid.cells.append(new_cell)
            
            self._refresh_app_list()
            QMessageBox.information(self, "成功", "应用添加成功！")

    def _edit_app(self) -> None:
        """编辑选中的应用."""
        current_item = self.app_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "提示", "请先选择要编辑的应用")
            return
        
        group, cell_index = current_item.data(Qt.UserRole)
        cell = group.grid.cells[cell_index]
        
        dialog = CellEditDialog(cell, self)
        if dialog.exec_() == QDialog.Accepted:
            dialog.apply_changes()
            self._refresh_app_list()
            QMessageBox.information(self, "成功", "应用信息已更新！")

    def _delete_app(self) -> None:
        """删除选中的应用."""
        current_item = self.app_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "提示", "请先选择要删除的应用")
            return
        
        reply = QMessageBox.question(
            self, "确认删除", "确定要删除这个应用吗？", 
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            group, cell_index = current_item.data(Qt.UserRole)
            group.grid.cells.pop(cell_index)
            self._refresh_app_list()
            QMessageBox.information(self, "成功", "应用已删除！")

    def _save_config(self) -> None:
        """保存配置."""
        # 更新配置
        self._config.float_window.opacity = self.opacity_slider.value() / 100
        self._config.float_window.width = self.width_spin.value()
        self._config.float_window.height = self.height_spin.value()
        self._config.float_window.icon_size = self.icon_size_slider.value()
        self._config.float_window.title = self.title_edit.text().strip() or "我的应用"
        self._config.float_window.locked = self.lock_checkbox.isChecked()
        
        # 保存到文件
        save_config(self._config)
        self._on_config_changed(self._config)
        
        QMessageBox.information(self, "成功", "设置已保存！")

    def _reset_settings(self) -> None:
        """重置所有设置."""
        reply = QMessageBox.question(
            self, "确认重置", "确定要重置所有设置吗？这将清除所有应用配置！", 
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            from .models import get_default_config
            self._config = get_default_config()
            self._refresh_app_list()
            QMessageBox.information(self, "成功", "设置已重置！")


# 为了向后兼容，保留原来的类名
SettingsWindow = SimpleSettingsWindow
