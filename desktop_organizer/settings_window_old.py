from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional, List

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
    QInputDialog,
)

from .config import save_config
from .models import AppConfig, GridCell, DesktopGroup
from .auto_sort import get_desktop_path


class CellEditDialog(QDialog):
    """编辑单个格子的对话框."""

    def __init__(self, cell: GridCell, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("编辑格子")
        self._cell = cell

        layout = QFormLayout(self)

        self.title_edit = QLineEdit(self)
        self.title_edit.setText(cell.title)
        layout.addRow("名称：", self.title_edit)

        self.path_edit = QLineEdit(self)
        self.path_edit.setText(cell.target_path or "")
        btn_browse = QPushButton("选择...")
        btn_browse.clicked.connect(self._on_browse)  # type: ignore[arg-type]
        path_layout = QHBoxLayout()
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(btn_browse)
        path_container = QWidget(self)
        path_container.setLayout(path_layout)
        layout.addRow("目标路径：", path_container)

        self.icon_edit = QLineEdit(self)
        self.icon_edit.setText(cell.icon_path or "")
        btn_icon = QPushButton("选择...")
        btn_icon.clicked.connect(self._on_browse_icon)  # type: ignore[arg-type]
        icon_layout = QHBoxLayout()
        icon_layout.addWidget(self.icon_edit)
        icon_layout.addWidget(btn_icon)
        icon_container = QWidget(self)
        icon_container.setLayout(icon_layout)
        layout.addRow("图标路径：", icon_container)

        btn_box = QHBoxLayout()
        btn_ok = QPushButton("确定")
        btn_cancel = QPushButton("取消")
        btn_ok.clicked.connect(self.accept)  # type: ignore[arg-type]
        btn_cancel.clicked.connect(self.reject)  # type: ignore[arg-type]
        btn_box.addStretch(1)
        btn_box.addWidget(btn_ok)
        btn_box.addWidget(btn_cancel)
        layout.addRow(btn_box)

    def _on_browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择目标文件")
        if path:
            self.path_edit.setText(path)

    def _on_browse_icon(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择图标文件")
        if path:
            self.icon_edit.setText(path)

    def apply_changes(self) -> None:
        self._cell.title = self.title_edit.text().strip()
        self._cell.target_path = self.path_edit.text().strip() or None
        self._cell.icon_path = self.icon_edit.text().strip() or None


class SettingsWindow(QWidget):
    """主页设置界面."""

    def __init__(
        self,
        app_config: AppConfig,
        on_config_changed: Callable[[AppConfig], None],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("桌面整理设置")
        self._config = app_config
        self._on_config_changed = on_config_changed

        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)

        # 最上方：分组选择与管理
        group_layout = QHBoxLayout()
        group_layout.addWidget(QLabel("当前分组："))
        self.group_combo = QComboBox()
        group_layout.addWidget(self.group_combo)

        btn_add_group = QPushButton("新增分组")
        btn_rename_group = QPushButton("重命名")
        btn_delete_group = QPushButton("删除")
        btn_add_group.clicked.connect(self._on_add_group)  # type: ignore[arg-type]
        btn_rename_group.clicked.connect(self._on_rename_group)  # type: ignore[arg-type]
        btn_delete_group.clicked.connect(self._on_delete_group)  # type: ignore[arg-type]
        group_layout.addWidget(btn_add_group)
        group_layout.addWidget(btn_rename_group)
        group_layout.addWidget(btn_delete_group)

        layout.addLayout(group_layout)

        if not self._config.groups:
            self._config.groups.append(DesktopGroup(name="默认分组"))

        self._refresh_group_combo()
        self.group_combo.currentIndexChanged.connect(self._on_group_changed)  # type: ignore[arg-type]

        # 顶部：当前分组的行列设置
        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("行数："))
        self.rows_spin = QSpinBox()
        self.rows_spin.setRange(1, 10)
        self.rows_spin.setValue(self._current_group().grid.rows)
        top_layout.addWidget(self.rows_spin)

        top_layout.addWidget(QLabel("列数："))
        self.cols_spin = QSpinBox()
        self.cols_spin.setRange(1, 10)
        self.cols_spin.setValue(self._current_group().grid.cols)
        top_layout.addWidget(self.cols_spin)

        btn_apply_layout = QPushButton("应用布局并预览")
        btn_apply_layout.clicked.connect(self._on_apply_layout)  # type: ignore[arg-type]
        top_layout.addWidget(btn_apply_layout)

        btn_import_desktop = QPushButton("从桌面导入图标")
        btn_import_desktop.clicked.connect(self._on_import_desktop)  # type: ignore[arg-type]
        top_layout.addWidget(btn_import_desktop)

        layout.addLayout(top_layout)

        # 中部：网格预览与编辑按钮
        self.grid_widget = QWidget(self)
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setContentsMargins(4, 4, 4, 4)
        self.grid_layout.setSpacing(4)
        layout.addWidget(self.grid_widget)

        # 底部：保存与关闭
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch(1)
        btn_save = QPushButton("保存并应用")
        btn_close = QPushButton("关闭")
        btn_save.clicked.connect(self._on_save)  # type: ignore[arg-type]
        btn_close.clicked.connect(self.close)  # type: ignore[arg-type]
        bottom_layout.addWidget(btn_save)
        bottom_layout.addWidget(btn_close)
        layout.addLayout(bottom_layout)

        self._rebuild_grid_preview()

    def _on_import_desktop(self) -> None:
        """扫描当前桌面，将桌面图标自动填充到格子里."""

        desktop = get_desktop_path()
        if not desktop.exists():
            QMessageBox.warning(self, "提示", f"未找到桌面目录：{desktop}")
            return

        files: List[Path] = []
        for entry in desktop.iterdir():
            # 只取文件（含快捷方式），不进入子文件夹
            if entry.is_file():
                files.append(entry)

        if not files:
            QMessageBox.information(self, "提示", "桌面上没有可导入的文件图标。")
            return

        # 根据数量自动设置行列（尽量接近方阵）
        import math

        count = len(files)
        cols = min(8, max(1, int(math.ceil(math.sqrt(count)))))
        rows = min(10, max(1, int(math.ceil(count / cols))))

        group = self._current_group()
        group.grid.rows = rows
        group.grid.cols = cols

        cells: List[GridCell] = []
        for f in files[: rows * cols]:
            cells.append(GridCell(title=f.stem, target_path=str(f)))

        group.grid.cells = cells
        group.grid.ensure_size()

        self.rows_spin.setValue(rows)
        self.cols_spin.setValue(cols)
        self._rebuild_grid_preview()

    def _on_apply_layout(self) -> None:
        group = self._current_group()
        group.grid.rows = self.rows_spin.value()
        group.grid.cols = self.cols_spin.value()
        group.grid.ensure_size()
        self._rebuild_grid_preview()

    def _rebuild_grid_preview(self) -> None:
        # 清空旧的按钮
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        grid = self._current_group().grid
        grid.ensure_size()

        for row in range(grid.rows):
            for col in range(grid.cols):
                index = row * grid.cols + col
                cell = grid.cells[index]
                btn = QPushButton(cell.title or f"格子 {index + 1}")
                btn.clicked.connect(lambda _checked=False, i=index: self._edit_cell(i))  # type: ignore[arg-type]
                self.grid_layout.addWidget(btn, row, col)

    def _edit_cell(self, index: int) -> None:
        cell = self._current_group().grid.cells[index]
        dlg = CellEditDialog(cell, self)
        if dlg.exec() == QDialog.Accepted:
            dlg.apply_changes()
            self._rebuild_grid_preview()

    def _on_save(self) -> None:
        # 更新当前分组行列以防用户修改但未点“应用布局”
        group = self._current_group()
        group.grid.rows = self.rows_spin.value()
        group.grid.cols = self.cols_spin.value()
        group.grid.ensure_size()

        save_config(self._config)
        self._on_config_changed(self._config)

        QMessageBox.information(self, "已保存", "配置已保存并应用。")

    # --------- group helpers ---------
    def _current_group_index(self) -> int:
        idx = self.group_combo.currentIndex()
        if idx < 0 and self._config.groups:
            return 0
        return idx

    def _current_group(self) -> DesktopGroup:
        if not self._config.groups:
            self._config.groups.append(DesktopGroup(name="默认分组"))
        idx = self._current_group_index()
        return self._config.groups[idx]

    def _refresh_group_combo(self) -> None:
        self.group_combo.blockSignals(True)
        self.group_combo.clear()
        for g in self._config.groups:
            self.group_combo.addItem(g.name)
        self.group_combo.blockSignals(False)
        if self._config.groups:
            self.group_combo.setCurrentIndex(0)

    def _on_group_changed(self, index: int) -> None:  # noqa: ARG002
        group = self._current_group()
        self.rows_spin.setValue(group.grid.rows)
        self.cols_spin.setValue(group.grid.cols)
        self._rebuild_grid_preview()

    def _on_add_group(self) -> None:
        name = f"分组{len(self._config.groups) + 1}"
        self._config.groups.append(DesktopGroup(name=name))
        self._refresh_group_combo()
        self.group_combo.setCurrentIndex(len(self._config.groups) - 1)
        self._rebuild_grid_preview()

    def _on_rename_group(self) -> None:
        idx = self._current_group_index()
        if idx < 0:
            return
        group = self._config.groups[idx]
        text, ok = QInputDialog.getText(self, "重命名分组", "新的分组名称：", text=group.name)
        if ok and text.strip():
            group.name = text.strip()
            self._refresh_group_combo()
            self.group_combo.setCurrentIndex(idx)

    def _on_delete_group(self) -> None:
        if len(self._config.groups) <= 1:
            QMessageBox.information(self, "提示", "至少保留一个分组。")
            return
        idx = self._current_group_index()
        if idx < 0:
            return
        del self._config.groups[idx]
        self._refresh_group_combo()
        self._rebuild_grid_preview()
