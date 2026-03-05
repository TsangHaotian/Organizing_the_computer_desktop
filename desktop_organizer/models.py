from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Optional, Dict, Any


@dataclass
class GridCell:
    """单个格子的配置."""

    title: str = ""
    target_path: Optional[str] = None  # 文件 / 文件夹 / 程序路径
    icon_path: Optional[str] = None  # 自定义图标路径，可选


@dataclass
class GridConfig:
    """悬浮窗中网格布局配置."""

    rows: int = 2
    cols: int = 3
    cells: List[GridCell] = field(default_factory=list)

    def ensure_size(self) -> None:
        """保证 cells 数量至少为 rows * cols."""

        total = self.rows * self.cols
        if len(self.cells) < total:
            self.cells.extend(GridCell() for _ in range(total - len(self.cells)))
        elif len(self.cells) > total:
            self.cells = self.cells[:total]


@dataclass
class DesktopGroup:
    """一个桌面分组（类似 360 中的一个大盒子）."""

    name: str = "默认分组"
    grid: GridConfig = field(default_factory=GridConfig)


@dataclass
class FloatWindowConfig:
    """悬浮窗本身的位置与外观配置."""

    x: int = 200
    y: int = 200
    width: int = 600  # 默认宽度，确保能容纳5列
    height: int = 400
    opacity: float = 0.95  # 透明度 0~1
    locked: bool = False  # 是否锁定位置（禁止拖动）
    icon_size: int = 48  # 图标大小（像素）
    title: str = "我的应用"  # 窗口标题


@dataclass
class AppConfig:
    """应用整体配置."""

    # 支持多个桌面分组
    groups: List[DesktopGroup] = field(default_factory=list)
    float_window: FloatWindowConfig = field(default_factory=FloatWindowConfig)

    def to_dict(self) -> Dict[str, Any]:
        """将配置转换为字典。"""
        return {
            "groups": [
                {
                    "name": group.name,
                    "grid": {
                        "rows": group.grid.rows,
                        "cols": group.grid.cols,
                        "cells": [
                            {
                                "title": cell.title,
                                "target_path": cell.target_path,
                                "icon_path": cell.icon_path,
                            }
                            for cell in group.grid.cells
                        ],
                    },
                }
                for group in self.groups
            ],
            "float_window": {
                "x": self.float_window.x,
                "y": self.float_window.y,
                "width": self.float_window.width,
                "height": self.float_window.height,
                "opacity": self.float_window.opacity,
                "locked": self.float_window.locked,
                "icon_size": self.float_window.icon_size,
                "title": self.float_window.title,
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppConfig":
        # 先尝试新的 groups 结构
        groups_data = data.get("groups")
        fw_data = data.get("float_window", {}) or {}

        groups: List[DesktopGroup] = []

        if isinstance(groups_data, list) and groups_data:
            for g in groups_data:
                g = g or {}
                grid_data = g.get("grid", {}) or {}
                grid = GridConfig(
                    rows=int(grid_data.get("rows", 2)),
                    cols=int(grid_data.get("cols", 3)),
                    cells=[
                        GridCell(
                            title=str(c.get("title", "")),
                            target_path=c.get("target_path"),
                            icon_path=c.get("icon_path"),
                        )
                        for c in grid_data.get("cells", []) or []
                    ],
                )
                grid.ensure_size()
                groups.append(
                    DesktopGroup(
                        name=str(g.get("name", "分组")),
                        grid=grid,
                    )
                )
        else:
            # 向后兼容：旧版本只有一个 grid 时，自动转换成一个分组
            grid_data = data.get("grid", {}) or {}
            grid = GridConfig(
                rows=int(grid_data.get("rows", 2)),
                cols=int(grid_data.get("cols", 3)),
                cells=[
                    GridCell(
                        title=str(c.get("title", "")),
                        target_path=c.get("target_path"),
                        icon_path=c.get("icon_path"),
                    )
                    for c in grid_data.get("cells", []) or []
                ],
            )
            grid.ensure_size()
            groups.append(DesktopGroup(name="默认分组", grid=grid))

        fw = FloatWindowConfig(
            x=int(fw_data.get("x", 200)),
            y=int(fw_data.get("y", 200)),
            width=int(fw_data.get("width", 600)),
            height=int(fw_data.get("height", 400)),
            opacity=float(fw_data.get("opacity", 0.95)),
            locked=bool(fw_data.get("locked", False)),
            icon_size=int(fw_data.get("icon_size", 48)),
        )

        return cls(groups=groups, float_window=fw)

    def to_dict(self) -> Dict[str, Any]:
        # dataclasses.asdict 足够满足这里的嵌套结构
        return asdict(self)


def get_default_config() -> AppConfig:
    """生成一个默认配置."""

    grid = GridConfig(rows=4, cols=5)  # 4行5列，共20个格子
    grid.ensure_size()
    default_group = DesktopGroup(name="我的应用", grid=grid)
    return AppConfig(groups=[default_group], float_window=FloatWindowConfig())


def get_user_config_path() -> Path:
    """
    获取用户级配置文件路径.

    例如：%APPDATA%/DesktopOrganizer/config.json
    在非 Windows 或没有 APPDATA 时，退回到用户家目录下的 .desktop_organizer/config.json。
    """

    import os

    appdata = os.getenv("APPDATA")
    if appdata:
        base = Path(appdata) / "DesktopOrganizer"
    else:
        base = Path.home() / ".desktop_organizer"

    base.mkdir(parents=True, exist_ok=True)
    return base / "config.json"

