"""固定关卡数据。

U / D / L / R 分别表示上、下、左、右，句点表示空格。
关卡与游戏逻辑分离，便于阅读、调整和自动验证。
"""

from __future__ import annotations

from dataclasses import dataclass


BOARD_SIZE = 6
VALID_TILES = frozenset(".UDLR")


@dataclass(frozen=True, slots=True)
class Level:
    """不可变的关卡配置。"""

    name: str
    rows: tuple[str, ...]
    max_mistakes: int = 3

    def create_board(self) -> list[list[str | None]]:
        """创建一份可修改的棋盘副本。"""

        return [[None if tile == "." else tile for tile in row] for row in self.rows]


LEVELS: tuple[Level, ...] = (
    Level(
        "第 1 关 · 认识方向",
        (
            "R...D.",
            "......",
            "..U..L",
            ".R..D.",
            "......",
            ".U...U",
        ),
    ),
    Level(
        "第 2 关 · 解开链条",
        (
            "R.RD..",
            ".R...R",
            "......",
            "..U..L",
            "LU.L..",
            "U....U",
        ),
    ),
    Level(
        "第 3 关 · 密集箭阵",
        (
            "L..UR.",
            ".LUL.U",
            "D.DRDR",
            "....LR",
            "..L.R.",
            "......",
        ),
    ),
)


def validate_levels(levels: tuple[Level, ...] = LEVELS) -> None:
    """在程序启动时尽早发现关卡数据格式错误。"""

    if not levels:
        raise ValueError("至少需要一个关卡")
    for level in levels:
        if len(level.rows) != BOARD_SIZE:
            raise ValueError(f"{level.name}: 棋盘必须有 {BOARD_SIZE} 行")
        if level.max_mistakes <= 0:
            raise ValueError(f"{level.name}: 失误机会必须大于 0")
        arrow_count = 0
        for row in level.rows:
            if len(row) != BOARD_SIZE:
                raise ValueError(f"{level.name}: 每行必须有 {BOARD_SIZE} 格")
            invalid = set(row) - VALID_TILES
            if invalid:
                raise ValueError(f"{level.name}: 包含未知字符 {sorted(invalid)}")
            arrow_count += sum(tile != "." for tile in row)
        if arrow_count == 0:
            raise ValueError(f"{level.name}: 关卡不能为空")


validate_levels()
