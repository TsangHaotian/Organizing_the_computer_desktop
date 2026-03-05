from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Callable, Optional, List, Tuple

from PySide6.QtCore import Qt, QPoint, QFileInfo, QObject, QEvent
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QIcon
from PySide6.QtWidgets import (
    QGridLayout,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QFileIconProvider,
    QMenu,
    QPushButton,
    QWidget,
    QSizePolicy,
    QScrollArea,
    QScrollBar,
)

from .models import AppConfig, GridCell, DesktopGroup


class FloatGridWindow(QWidget):
    """桌面悬浮格子窗口."""

    def __init__(
        self,
        app_config: AppConfig,
        on_request_edit_cell: Optional[Callable[[int], None]] = None,
        on_request_open_settings: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__()

        self._config = app_config
        self._on_request_edit_cell = on_request_edit_cell
        self._on_request_open_settings = on_request_open_settings
        self._dragging = False
        self._drag_offset = QPoint(0, 0)
        self._resizing = False
        self._resize_start_pos = QPoint(0, 0)

        self.setWindowTitle("桌面整理格子")
        self.setWindowFlags(
            Qt.Tool
            | Qt.WindowStaysOnTopHint
            | Qt.FramelessWindowHint
            | Qt.NoDropShadowWindowHint
        )
        self.setAcceptDrops(True)
        # 整个悬浮窗支持自定义右键菜单
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_window_context_menu)  # type: ignore[arg-type]

        # 主垂直布局：标题 + 导航条 + 滚动区域
        self._main_layout = QVBoxLayout()
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)
        self.setLayout(self._main_layout)
        
        # 创建标题栏
        title_bar = QWidget()
        title_bar.setFixedHeight(40)
        title_bar.setStyleSheet("""
            QWidget {
                background-color: rgba(50, 50, 50, 200);
                border-bottom: 1px solid rgba(100, 100, 100, 150);
            }
            QLabel {
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 0 12px;
            }
        """)
        
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(0, 0, 8, 0)
        title_layout.setSpacing(0)
        
        self._title_label = QLabel(self._config.float_window.title)
        self._title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        title_layout.addWidget(self._title_label, 1)  # 标题靠左拉伸
        
        # 添加导航按钮
        self._create_navigation_buttons(title_layout)
        
        self._main_layout.addWidget(title_bar)
        
        # 创建滚动区域
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._scroll_area.setFrameShape(QFrame.NoFrame)
        
        # 滚动区域内的内容widget
        self._content_widget = QWidget()
        self._content_layout = QVBoxLayout()
        self._content_layout.setContentsMargins(8, 8, 8, 8)
        self._content_layout.setSpacing(8)
        self._content_widget.setLayout(self._content_layout)
        
        self._scroll_area.setWidget(self._content_widget)
        self._main_layout.addWidget(self._scroll_area)

        self._buttons: List[QWidget] = []
        self._button_indices: dict[QWidget, tuple[int, int]] = {}
        self._event_filters: List[QObject] = []  # 保存事件过滤器实例，防止被垃圾回收
        self._icon_provider = QFileIconProvider()
        
        # 图标大小设置
        self._icon_size = self._config.float_window.icon_size  # 从配置中读取图标大小

        self.reload_from_config()

    def _create_navigation_buttons(self, layout: QHBoxLayout) -> None:
        """创建导航按钮."""
        # 添加应用按钮
        add_app_btn = QPushButton("+ 添加应用")
        add_app_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                border: none;
                padding: 8px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: rgba(80, 80, 80, 150);
                border-radius: 4px;
            }
            QPushButton:pressed {
                background-color: rgba(100, 100, 100, 150);
            }
        """)
        add_app_btn.clicked.connect(self._add_new_application)
        layout.addWidget(add_app_btn)
        
        # 设置按钮
        if self._on_request_open_settings:
            settings_btn = QPushButton("⚙️ 设置")
            settings_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: white;
                    border: none;
                    padding: 8px 12px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: rgba(80, 80, 80, 150);
                    border-radius: 4px;
                }
                QPushButton:pressed {
                    background-color: rgba(100, 100, 100, 150);
                }
            """)
            settings_btn.clicked.connect(self._on_request_open_settings)
            layout.addWidget(settings_btn)
        
        # 锁定/解锁按钮
        self._lock_btn = QPushButton("🔒 锁定")
        self._lock_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                border: none;
                padding: 8px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: rgba(80, 80, 80, 150);
                border-radius: 4px;
            }
            QPushButton:pressed {
                background-color: rgba(100, 100, 100, 150);
            }
        """)
        self._lock_btn.clicked.connect(self._toggle_lock)
        layout.addWidget(self._lock_btn)

    # ---------------- window & layout ----------------
    def reload_from_config(self) -> None:
        """根据当前配置刷新格子布局和窗口状态."""
        # 更新窗口标题
        self.setWindowTitle(self._config.float_window.title)
        
        # 更新标题栏标签
        if hasattr(self, '_title_label'):
            self._title_label.setText(self._config.float_window.title)
            
        # 清除旧分组和按钮
        for btn in self._buttons:
            btn.deleteLater()
        self._buttons.clear()
        self._button_indices.clear()
        self._event_filters.clear()  # 清除旧的事件过滤器
        
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        groups = self._config.groups or [DesktopGroup(name="默认分组")]

        any_icon = False
        for gi, group in enumerate(groups):
            # 紧凑模式：每个分组里只保留真正有目标的格子
            group.grid.cells = [c for c in group.grid.cells if c.target_path]
            has_any = bool(group.grid.cells)
            self._add_group_section(gi, group)
            any_icon = any_icon or has_any

        # 如果所有分组里都没有图标，就留一个空白提示
        if not any_icon:
            label = QLabel("暂时没有图标，请直接拖拽应用到此窗口即可添加。")
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("color: #666; font-size: 14px; padding: 20px;")
            self._content_layout.addWidget(label)

        fw_cfg = self._config.float_window
        self.setGeometry(fw_cfg.x, fw_cfg.y, fw_cfg.width, fw_cfg.height)
        self.setWindowOpacity(max(0.1, min(fw_cfg.opacity, 1.0)))
        
        # 更新锁定按钮状态
        self._update_lock_button()

    def _update_lock_button(self) -> None:
        """更新锁定按钮状态."""
        if hasattr(self, '_lock_btn'):
            if self._config.float_window.locked:
                self._lock_btn.setText("🔓 解锁")
            else:
                self._lock_btn.setText("🔒 锁定")

    def _toggle_lock(self) -> None:
        """切换锁定状态."""
        self._config.float_window.locked = not self._config.float_window.locked
        self._update_lock_button()

    def _add_new_application(self) -> None:
        """添加新应用（通过文件选择对话框）."""
        from PySide6.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择应用文件",
            "",
            "所有文件 (*.*)"
        )
        
        if file_path:
            self._add_application_to_grid(file_path)

    def _add_application_to_grid(self, file_path: str) -> None:
        """将应用添加到第一个空格子."""
        p = Path(file_path)
        
        # 查找第一个空格子
        for gi, group in enumerate(self._config.groups):
            for ci, cell in enumerate(group.grid.cells):
                if not cell.target_path:
                    # 找到空格子，添加应用
                    cell.target_path = str(p)
                    cell.title = p.stem
                    self.reload_from_config()
                    return
        
        # 如果没有空格子，在第一个分组添加新格子
        if self._config.groups:
            first_group = self._config.groups[0]
            new_cell = GridCell(target_path=str(p), title=p.stem)
            first_group.grid.cells.append(new_cell)
            self.reload_from_config()

    def _add_group_section(self, group_index: int, group: DesktopGroup) -> None:
        """创建一个分组区域（灰色背景 + 标题 + 图标网格）"""

        section = QFrame(self)
        section.setFrameShape(QFrame.NoFrame)
        section.setStyleSheet(
            """
            QFrame {
                background-color: rgba(40, 40, 40, 180);
                border-radius: 6px;
            }
            """
        )

        vlayout = QVBoxLayout(section)
        vlayout.setContentsMargins(4, 4, 4, 4)
        vlayout.setSpacing(4)

        # 移除分组标题，因为现在标题已经移到窗口顶部

        grid_layout = QGridLayout()
        grid_layout.setContentsMargins(4, 0, 4, 4)
        grid_layout.setSpacing(4)

        # 固定5个一排的布局
        cols = 5
        
        # 获取格子列表
        cells = group.grid.cells
        
        # 如果没有格子，创建默认的空格子
        if not cells:
            cells = [GridCell() for _ in range(10)]  # 默认创建2行，每行5个
            group.grid.cells = cells
        for idx, cell in enumerate(cells):
            row = idx // cols
            col = idx % cols
            btn = self._create_cell_button(group_index, idx, cell)
            grid_layout.addWidget(btn, row, col)
            self._buttons.append(btn)

        vlayout.addLayout(grid_layout)
        self._content_layout.addWidget(section)

    def _create_cell_button(self, group_index: int, cell_index: int, cell: GridCell) -> QWidget:
        """创建一个包含图标和文字的按钮组件，使用事件过滤器确保点击稳定."""
        from PySide6.QtWidgets import QToolButton, QVBoxLayout, QLabel
        
        # 根据窗口宽度计算格子大小
        cell_width, cell_height = self._calculate_cell_size()
        
        # 创建容器widget
        container = QWidget()
        container.setFixedSize(cell_width, cell_height)
        
        # 垂直布局
        layout = QVBoxLayout(container)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        layout.setAlignment(Qt.AlignCenter)
        
        # 若已有绑定目标，默认标题采用文件名
        title = cell.title
        if cell.target_path and not title:
            title = Path(cell.target_path).stem
        title = title or "空"
        
        # 计算图标按钮大小
        icon_size = min(self._icon_size, cell_width - 20, cell_height - 40)
        icon_btn_size = max(icon_size, 32)  # 最小32像素
        
        # 创建工具按钮用于显示图标
        icon_btn = QToolButton()
        icon_btn.setToolButtonStyle(Qt.ToolButtonIconOnly)
        icon_btn.setIconSize(self._get_icon_size())
        icon_btn.setFixedSize(icon_btn_size, icon_btn_size)
        icon_btn.setCursor(Qt.PointingHandCursor)  # 添加手型光标
        
        # 使用图标：优先使用自定义图标，其次使用目标文件的系统图标
        icon = self._get_cell_icon(cell)
        if not icon.isNull():
            icon_btn.setIcon(icon)
        
        # 创建文字标签
        text_label = QLabel(title)
        text_label.setAlignment(Qt.AlignCenter)
        text_label.setWordWrap(True)
        text_label.setMaximumHeight(30)
        text_label.setCursor(Qt.PointingHandCursor)  # 添加手型光标
        text_label.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 11px;
                background-color: transparent;
            }
        """)
        
        # 添加到布局
        layout.addWidget(icon_btn)
        layout.addWidget(text_label)
        
        # 设置容器样式
        container.setStyleSheet("""
            QWidget {
                background-color: rgba(60, 60, 60, 100);
                border-radius: 8px;
                border: 1px solid rgba(100, 100, 100, 50);
            }
            QWidget:hover {
                background-color: rgba(80, 80, 80, 150);
                border: 1px solid rgba(150, 150, 150, 100);
            }
        """)
        
        # 创建事件过滤器来处理点击
        class CellEventFilter(QObject):
            def __init__(self, group_idx, cell_idx, on_click, on_context):
                super().__init__()
                self.group_idx = group_idx
                self.cell_idx = cell_idx
                self.on_click = on_click
                self.on_context = on_context
                
            def eventFilter(self, obj, event):
                if event.type() == QEvent.MouseButtonPress:
                    if event.button() == Qt.LeftButton:
                        if self.on_click:
                            self.on_click(self.group_idx, self.cell_idx)
                        return True
                    elif event.button() == Qt.RightButton:
                        if self.on_context:
                            self.on_context(event.pos())
                        return True
                return False
        
        # 创建事件过滤器
        def create_event_filter(widget):
            event_filter = CellEventFilter(
                group_index, 
                cell_index, 
                self._on_cell_clicked,
                lambda pos: self._on_cell_context_menu(group_index, cell_index, container, pos)
            )
            widget.installEventFilter(event_filter)
            self._event_filters.append(event_filter)  # 保存事件过滤器实例
            return event_filter
            
        # 为容器、图标按钮和文字标签都安装事件过滤器
        create_event_filter(container)
        create_event_filter(icon_btn)
        create_event_filter(text_label)
        
        self._button_indices[container] = (group_index, cell_index)
        return container

    def _get_cell_icon(self, cell: GridCell) -> QIcon:
        # 自定义图标
        if cell.icon_path:
            icon_path = Path(cell.icon_path)
            if icon_path.is_file():
                return QIcon(str(icon_path))

        # 目标文件/文件夹的系统图标
        if cell.target_path:
            p = Path(cell.target_path)
            if p.exists():
                return self._icon_provider.icon(QFileInfo(str(p)))

        return QIcon()

    def _calculate_cell_size(self) -> tuple[int, int]:
        """根据窗口宽度计算格子大小."""
        # 最小宽度：5列 * 最小格子宽度80px + 边距
        min_width = 5 * 80 + 40  # 440px
        current_width = max(self._config.float_window.width, min_width)
        
        # 计算每个格子的可用宽度
        available_width = current_width - 40  # 减去左右边距
        cell_width = available_width // 5  # 5列
        
        # 确保最小宽度
        cell_width = max(cell_width, 80)
        
        # 高度根据宽度比例计算，保持合理的比例
        cell_height = max(100, int(cell_width * 0.9))
        
        return cell_width, cell_height

    def _get_icon_size(self):
        """获取当前图标大小."""
        from PySide6.QtCore import QSize
        return QSize(self._icon_size, self._icon_size)
    
    def set_icon_size(self, size: int):
        """设置图标大小."""
        self._icon_size = max(16, min(128, size))  # 限制在16-128之间
        self.reload_from_config()

    def _guess_icon_size(self):
        """保留原方法以兼容性."""
        return self._get_icon_size()

    # ---------------- cell interactions ----------------
    def _on_cell_clicked(self, group_index: int, cell_index: int) -> None:
        print(f"点击事件触发: group={group_index}, cell={cell_index}")  # 调试信息
        try:
            cell = self._config.groups[group_index].grid.cells[cell_index]
            print(f"目标路径: {cell.target_path}")  # 调试信息
            
            if not cell.target_path:
                print("没有绑定目标，尝试触发编辑")  # 调试信息
                # 若没有绑定，则可以触发编辑
                if self._on_request_edit_cell:
                    print("调用编辑回调")  # 调试信息
                    self._on_request_edit_cell(cell_index)
                return

            path = Path(cell.target_path)
            print(f"尝试打开: {path}")  # 调试信息
            try:
                if path.is_dir():
                    print("打开目录")  # 调试信息
                    os.startfile(str(path))
                else:
                    print("打开文件")  # 调试信息
                    os.startfile(str(path))
                print("打开成功")  # 调试信息
            except Exception as e:
                print(f"os.startfile 失败: {e}")  # 调试信息
                # 回退到 subprocess
                try:
                    print("尝试使用 subprocess 打开")  # 调试信息
                    subprocess.Popen([str(path)])
                    print("subprocess 打开成功")  # 调试信息
                except Exception as e2:
                    print(f"subprocess 也失败: {e2}")  # 调试信息
        except Exception as e:
            print(f"处理点击事件时出错: {e}")  # 调试信息

    def _on_cell_context_menu(self, group_index: int, cell_index: int, widget: QWidget, pos) -> None:
        menu = QMenu(self)

        action_open = menu.addAction("打开目标")
        action_edit = menu.addAction("编辑此格子...")
        action_clear = menu.addAction("清空绑定")
        if self._on_request_open_settings:
            menu.addSeparator()
            action_settings = menu.addAction("打开设置界面")
        else:
            action_settings = None
            
        menu.addSeparator()
        action_close = menu.addAction("关闭悬浮窗")

        cell = self._config.groups[group_index].grid.cells[cell_index]
        if not cell.target_path:
            action_open.setEnabled(False)

        chosen = menu.exec_(widget.mapToGlobal(pos))
        if chosen is None:
            return

        if chosen is action_open and cell.target_path:
            self._on_cell_clicked(group_index, cell_index)
        elif chosen is action_edit and self._on_request_edit_cell:
            self._on_request_edit_cell(cell_index)
        elif chosen is action_clear:
            cell.title = ""
            cell.target_path = None
            cell.icon_path = None
            self.reload_from_config()
        elif action_settings is not None and chosen is action_settings and self._on_request_open_settings:
            self._on_request_open_settings()
        elif chosen is action_close:
            self.close()

    def _on_window_context_menu(self, pos) -> None:
        """悬浮窗任意空白处右键菜单."""
        menu = QMenu(self)
        if self._on_request_open_settings:
            action_settings = menu.addAction("打开设置界面")
        else:
            action_settings = None
            
        menu.addSeparator()
        action_close = menu.addAction("关闭悬浮窗")

        locked = self._config.float_window.locked
        action_lock = menu.addAction("锁定位置" if not locked else "解锁位置")
        action_lock.setCheckable(True)
        action_lock.setChecked(locked)

        chosen = menu.exec_(self.mapToGlobal(pos))
        if chosen is None:
            return

        if chosen is action_lock:
            self._config.float_window.locked = not locked
            self._update_lock_button()
        elif action_settings is not None and chosen is action_settings and self._on_request_open_settings:
            self._on_request_open_settings()
        elif chosen is action_close:
            self.close()

    # ---------------- drag window (pseudo title bar) ----------------
    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.LeftButton:
            pos = event.position().toPoint()
            rect = self.rect()
            # 右下角区域用于调整窗口大小
            if rect.width() - 16 <= pos.x() <= rect.width() and rect.height() - 16 <= pos.y() <= rect.height():
                self._resizing = True
                self._resize_start_pos = event.globalPosition().toPoint()
                event.accept()
                return

            if not self._config.float_window.locked:
                self._dragging = True
                self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                event.accept()
                return

        event.ignore()

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        if self._resizing:
            current_pos = event.globalPosition().toPoint()
            delta = current_pos - self._resize_start_pos
            
            # 设置最小宽度为440px（5列 * 80px + 边距）
            min_width = 440
            new_width = max(min_width, self.width() + delta.x())
            new_height = max(150, self.height() + delta.y())

            # 实时更新配置中的宽高，让内部网格可根据新尺寸重新布局
            self._config.float_window.width = new_width
            self._config.float_window.height = new_height
            self.resize(new_width, new_height)
            self.reload_from_config()

            # 更新起始点，支持连续拖动
            self._resize_start_pos = current_pos
            event.accept()
            return

        if self._dragging and not self._config.float_window.locked:
            new_pos = event.globalPosition().toPoint() - self._drag_offset
            self.move(new_pos)
            event.accept()
        else:
            event.ignore()

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.LeftButton:
            if self._resizing:
                self._resizing = False
                event.accept()
                return

            if self._dragging:
                self._dragging = False
                # 保存当前位置到配置
                geo = self.geometry()
                self._config.float_window.x = geo.x()
                self._config.float_window.y = geo.y()
                event.accept()
                return

        event.ignore()

    # ---------------- drag & drop files to bind cell ----------------
    def dragEnterEvent(self, event: QDragEnterEvent) -> None:  # type: ignore[override]
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:  # type: ignore[override]
        """将拖入的第一个文件添加到格子中（优先空格子）."""

        urls = event.mimeData().urls()
        if not urls:
            event.ignore()
            return

        local_path = urls[0].toLocalFile()
        if not local_path:
            event.ignore()
            return

        # 直接添加到第一个空格子或创建新格子
        self._add_application_to_grid(local_path)
        event.acceptProposedAction()
