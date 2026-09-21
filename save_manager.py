"""便携式游戏进度存档。"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path


SAVE_VERSION = 1


@dataclass(slots=True)
class Progress:
    """仅保存稳定且与界面无关的闯关进度。"""

    unlocked_level: int = 0
    completed_levels: set[int] = field(default_factory=set)

    def mark_completed(self, level_index: int, level_count: int) -> None:
        if not 0 <= level_index < level_count:
            raise IndexError("关卡下标超出范围")
        self.completed_levels.add(level_index)
        self.unlocked_level = min(
            max(self.unlocked_level, level_index + 1), level_count - 1
        )


def default_save_path() -> Path:
    """源码运行时写项目目录，PyInstaller 运行时写 exe 同目录。"""

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "save.json"
    return Path(__file__).resolve().parent / "save.json"


def load_progress(path: Path | None = None, level_count: int = 6) -> Progress:
    target = path or default_save_path()
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return Progress()
        unlocked = int(payload.get("unlocked_level", 0))
        raw_completed = payload.get("completed_levels", [])
        if not isinstance(raw_completed, list):
            return Progress()
        completed = {int(value) for value in raw_completed}
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return Progress()

    maximum = max(0, level_count - 1)
    completed = {value for value in completed if 0 <= value <= maximum}
    return Progress(max(0, min(unlocked, maximum)), completed)


def save_progress(progress: Progress, path: Path | None = None) -> bool:
    """原子保存；失败时返回 False，让界面决定如何提示。"""

    target = path or default_save_path()
    temporary = target.with_suffix(target.suffix + ".tmp")
    payload = {
        "version": SAVE_VERSION,
        "unlocked_level": progress.unlocked_level,
        "completed_levels": sorted(progress.completed_levels),
    }
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        temporary.replace(target)
    except OSError:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        return False
    return True
