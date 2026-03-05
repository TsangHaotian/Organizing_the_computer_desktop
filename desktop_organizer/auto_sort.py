from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List


@dataclass
class CategoryRule:
    """文件分类规则：一个分类名对应多个扩展名."""

    name: str
    extensions: List[str] = field(default_factory=list)


DEFAULT_RULES: List[CategoryRule] = [
    CategoryRule("文档", [".doc", ".docx", ".pdf", ".txt", ".ppt", ".pptx", ".xls", ".xlsx"]),
    CategoryRule("图片", [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp"]),
    CategoryRule("视频", [".mp4", ".avi", ".mkv", ".mov", ".flv"]),
    CategoryRule("音乐", [".mp3", ".wav", ".flac", ".aac", ".ogg"]),
    CategoryRule("压缩包", [".zip", ".rar", ".7z", ".tar", ".gz"]),
    CategoryRule("安装包", [".exe", ".msi"]),
]


def get_desktop_path() -> Path:
    """获取当前用户的桌面路径（适配大多数 Win10/Win11 情况）."""

    home = Path.home()
    desktop = home / "Desktop"
    if desktop.exists():
        return desktop
    # 兼容中文路径，例如“桌面”
    chinese_desktop = home / "桌面"
    if chinese_desktop.exists():
        return chinese_desktop
    return home


def build_extension_map(rules: List[CategoryRule]) -> Dict[str, str]:
    """将分类规则展开成 {扩展名: 目标文件夹名}."""

    mapping: Dict[str, str] = {}
    for rule in rules:
        for ext in rule.extensions:
            mapping[ext.lower()] = rule.name
    return mapping


def organize_directory(
    target_dir: Path,
    rules: List[CategoryRule] | None = None,
    log: List[str] | None = None,
) -> None:
    """
    按规则整理目录中的文件：根据扩展名移动到子文件夹中。

    - 不会递归子目录，只整理当前目录下的文件；
    - 已在对应目标文件夹中的文件会被跳过；
    - 若存在同名文件，会在文件名后加数字后缀避免覆盖。
    """

    if rules is None:
        rules = DEFAULT_RULES

    if log is None:
        log = []

    if not target_dir.exists():
        raise FileNotFoundError(f"目录不存在: {target_dir}")

    ext_map = build_extension_map(rules)

    def add_log(message: str) -> None:
        log.append(message)
        # 同时打印到控制台，方便命令行模式查看
        print(message)

    add_log(f"开始整理目录: {target_dir}")
    files_moved = 0

    for entry in target_dir.iterdir():
        if entry.is_dir():
            # 跳过已经是我们创建的分类目录（防止无限嵌套）
            if any(entry.name == rule.name for rule in rules):
                continue
            # 也跳过常见系统文件夹
            continue

        if not entry.is_file():
            continue

        ext = entry.suffix.lower()
        if not ext:
            add_log(f"跳过无扩展名文件: {entry.name}")
            continue

        category = ext_map.get(ext)
        if not category:
            add_log(f"未匹配到分类规则: {entry.name} ({ext})")
            continue

        target_folder = target_dir / category
        target_folder.mkdir(exist_ok=True)

        # 如果原本就已经在目标目录中，则跳过
        if entry.parent == target_folder:
            add_log(f"已在目标文件夹中，跳过: {entry.name}")
            continue

        target_path = target_folder / entry.name

        # 处理同名文件：文件名_1.ext、_2.ext ...
        if target_path.exists():
            stem = entry.stem
            counter = 1
            while True:
                new_name = f"{stem}_{counter}{ext}"
                candidate = target_folder / new_name
                if not candidate.exists():
                    target_path = candidate
                    break
                counter += 1

        shutil.move(str(entry), str(target_path))
        files_moved += 1
        add_log(f"移动: {entry.name} -> {target_folder.name}/")

    add_log(f"整理完成，共移动 {files_moved} 个文件。")


def run_cli_mode(args: List[str] | None = None) -> None:
    """
    命令行模式，方便脚本调用：

    - 无参数：整理默认桌面目录；
    - 有一个路径参数：整理指定目录。
    """

    if args is None:
        args = sys.argv[1:]

    if args:
        target = Path(args[0]).expanduser()
    else:
        target = get_desktop_path()

    log_buffer: List[str] = []
    try:
        organize_directory(target, DEFAULT_RULES, log=log_buffer)
    except Exception as exc:  # noqa: BLE001
        print(f"整理失败: {exc}")
        sys.exit(1)

