"""不依赖 Pygame 的游戏规则和状态。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Sequence

from levels import LEVELS, Level


Board = list[list[str | None]]

DIRECTION_STEPS: dict[str, tuple[int, int]] = {
    "U": (-1, 0),
    "D": (1, 0),
    "L": (0, -1),
    "R": (0, 1),
}


class ClickResult(str, Enum):
    """一次点击的逻辑结果。"""

    EMPTY = "empty"
    CLEARED = "cleared"
    BLOCKED = "blocked"
    IGNORED = "ignored"


class GameStatus(str, Enum):
    """与界面无关的游戏流程状态。"""

    PLAYING = "playing"
    LEVEL_CLEAR = "level_clear"
    GAME_OVER = "game_over"
    ALL_CLEAR = "all_clear"


@dataclass(frozen=True, slots=True)
class ActionOutcome:
    """提供给界面层的点击结果。"""

    result: ClickResult
    row: int | None
    col: int | None
    direction: str | None
    blocker: tuple[int, int] | None
    mistakes_left: int
    remaining_arrows: int


def in_bounds(board: Board, row: int, col: int) -> bool:
    return bool(board) and 0 <= row < len(board) and 0 <= col < len(board[0])


def first_blocker(board: Board, row: int, col: int) -> tuple[int, int] | None:
    """返回箭头前方射线上最近的阻挡坐标。"""

    if not in_bounds(board, row, col):
        return None
    direction = board[row][col]
    if direction not in DIRECTION_STEPS:
        return None

    row_step, col_step = DIRECTION_STEPS[direction]
    next_row = row + row_step
    next_col = col + col_step

    # 先检查边界，再访问棋盘。这能避免向上/向左时误用负下标。
    while in_bounds(board, next_row, next_col):
        if board[next_row][next_col] is not None:
            return next_row, next_col
        next_row += row_step
        next_col += col_step
    return None


def is_path_clear(board: Board, row: int, col: int) -> bool:
    """判断指定箭头到棋盘边界的前方路径是否为空。"""

    return (
        in_bounds(board, row, col)
        and board[row][col] in DIRECTION_STEPS
        and first_blocker(board, row, col) is None
    )


def remaining_arrows(board: Board) -> int:
    return sum(cell is not None for row in board for cell in row)


def board_snapshot(board: Board) -> tuple[tuple[str | None, ...], ...]:
    """返回不可变快照，用于测试和状态比较。"""

    return tuple(tuple(row) for row in board)


def solve_board(board: Board) -> list[tuple[int, int]] | None:
    """返回一个可行消除顺序；死局返回 None。

    移除箭头只会减少阻挡，不会新增阻挡，因此每轮移除任意一个
    当前可飞出的箭头都是安全的。
    """

    working = [row.copy() for row in board]
    order: list[tuple[int, int]] = []

    while remaining_arrows(working):
        removable: tuple[int, int] | None = None
        for row_index, row in enumerate(working):
            for col_index, tile in enumerate(row):
                if tile is not None and is_path_clear(working, row_index, col_index):
                    removable = row_index, col_index
                    break
            if removable is not None:
                break

        if removable is None:
            return None
        row_index, col_index = removable
        working[row_index][col_index] = None
        order.append(removable)

    return order


def all_levels_solvable(levels: Iterable[Level] = LEVELS) -> bool:
    return all(solve_board(level.create_board()) is not None for level in levels)


class GameState:
    """负责关卡、机会、点击和胜负状态。"""

    def __init__(self, levels: Sequence[Level] = LEVELS) -> None:
        if not levels:
            raise ValueError("至少需要一个关卡")
        self.levels = tuple(levels)
        self.level_index = 0
        self.board: Board = []
        self.mistakes_left = 0
        self.status = GameStatus.PLAYING
        self._load_level(0)

    @property
    def current_level(self) -> Level:
        return self.levels[self.level_index]

    @property
    def remaining(self) -> int:
        return remaining_arrows(self.board)

    def _load_level(self, index: int) -> None:
        self.level_index = index
        self.board = self.levels[index].create_board()
        self.mistakes_left = self.levels[index].max_mistakes
        self.status = GameStatus.PLAYING

    def restart_current(self) -> None:
        self._load_level(self.level_index)

    def restart_game(self) -> None:
        self._load_level(0)

    def next_level(self) -> bool:
        """从通关页进入下一关，返回是否真正加载了新关卡。"""

        if self.status is not GameStatus.LEVEL_CLEAR:
            return False
        if self.level_index + 1 >= len(self.levels):
            self.status = GameStatus.ALL_CLEAR
            return False
        self._load_level(self.level_index + 1)
        return True

    def click(self, row: int, col: int) -> ActionOutcome:
        if self.status is not GameStatus.PLAYING:
            return self._outcome(ClickResult.IGNORED, None, None, None, None)
        if not in_bounds(self.board, row, col) or self.board[row][col] is None:
            return self._outcome(ClickResult.EMPTY, row, col, None, None)

        direction = self.board[row][col]
        blocker = first_blocker(self.board, row, col)
        if blocker is None:
            # 逻辑上立即移除，界面另存一份动画快照。
            self.board[row][col] = None
            if self.remaining == 0:
                self.status = GameStatus.LEVEL_CLEAR
            return self._outcome(ClickResult.CLEARED, row, col, direction, None)

        self.mistakes_left -= 1
        if self.mistakes_left <= 0:
            self.mistakes_left = 0
            self.status = GameStatus.GAME_OVER
        return self._outcome(ClickResult.BLOCKED, row, col, direction, blocker)

    def _outcome(
        self,
        result: ClickResult,
        row: int | None,
        col: int | None,
        direction: str | None,
        blocker: tuple[int, int] | None,
    ) -> ActionOutcome:
        return ActionOutcome(
            result=result,
            row=row,
            col=col,
            direction=direction,
            blocker=blocker,
            mistakes_left=self.mistakes_left,
            remaining_arrows=self.remaining,
        )

