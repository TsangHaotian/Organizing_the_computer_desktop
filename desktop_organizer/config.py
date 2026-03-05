from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from .models import AppConfig, get_default_config, get_user_config_path


def load_config(path: Path | None = None) -> AppConfig:
    """从 JSON 文件加载配置，若不存在或损坏则返回默认配置。"""

    if path is None:
        path = get_user_config_path()

    if not path.exists():
        return get_default_config()

    try:
        with path.open("r", encoding="utf-8") as f:
            data: Dict[str, Any] = json.load(f)
    except Exception:  # noqa: BLE001
        # 文件损坏或无法解析时，回退到默认配置
        return get_default_config()

    try:
        return AppConfig.from_dict(data)
    except Exception:  # noqa: BLE001
        return get_default_config()


def save_config(config: AppConfig, path: Path | None = None) -> None:
    """将配置保存到 JSON 文件."""

    if path is None:
        path = get_user_config_path()

    path.parent.mkdir(parents=True, exist_ok=True)
    data = config.to_dict()
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

