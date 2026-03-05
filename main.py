import sys
from pathlib import Path
from typing import List

from desktop_organizer.app import main as visual_main


def main() -> None:
    """
    入口说明：
    - 默认：启动 PySide6 可视化桌面整理工具（托盘 + 悬浮格子 + 设置界面）；
    - 带 `--cli` 参数：仅使用命令行自动整理（按扩展名分类），兼容旧用法。
    """

    if "--cli" in sys.argv:
        from desktop_organizer.auto_sort import run_cli_mode  # 延迟导入，避免 GUI 依赖

        # 去掉 --cli 再交给 auto_sort 处理路径参数
        args: List[str] = [a for a in sys.argv[1:] if a != "--cli"]
        run_cli_mode(args)
    else:
        visual_main()


if __name__ == "__main__":
    main()

