"""作业要求 T01–T06 及关卡可解性测试。"""

from __future__ import annotations

import pytest

from game_logic import (
    ClickResult,
    GameState,
    GameStatus,
    board_snapshot,
    is_path_clear,
    solve_board,
)
from levels import LEVELS, Level


def make_level(*rows: str, mistakes: int = 3) -> Level:
    return Level("测试关卡", tuple(rows), mistakes)


def test_t01_clear_arrow_flies_out_and_count_decreases() -> None:
    level = make_level(".....R", "......", "......", "......", "......", "......")
    game = GameState((level,))

    outcome = game.click(0, 5)

    assert outcome.result is ClickResult.CLEARED
    assert game.board[0][5] is None
    assert outcome.remaining_arrows == 0


def test_t02_blocked_arrow_stays_and_costs_one_mistake() -> None:
    level = make_level("R...D.", "......", "......", "......", "......", "......")
    game = GameState((level,))

    outcome = game.click(0, 0)

    assert outcome.result is ClickResult.BLOCKED
    assert outcome.blocker == (0, 4)
    assert game.board[0][0] == "R"
    assert game.mistakes_left == 2
    assert game.remaining == 2


@pytest.mark.parametrize(
    ("rows", "position"),
    [
        (("..U...", "......", "......", "......", "......", "......"), (0, 2)),
        (("......", "......", "......", "......", "......", "..D..."), (5, 2)),
        (("......", "......", "L.....", "......", "......", "......"), (2, 0)),
        (("......", "......", ".....R", "......", "......", "......"), (2, 5)),
    ],
)
def test_t03_edge_arrow_facing_outside_never_overflows(
    rows: tuple[str, ...], position: tuple[int, int]
) -> None:
    level = make_level(*rows)
    game = GameState((level,))

    assert is_path_clear(game.board, *position)
    assert game.click(*position).result is ClickResult.CLEARED


def test_t04_clearing_level_allows_next_level_and_final_completion() -> None:
    first = make_level(".....R", "......", "......", "......", "......", "......")
    second = make_level("U.....", "......", "......", "......", "......", "......")
    game = GameState((first, second))

    game.click(0, 5)
    assert game.status is GameStatus.LEVEL_CLEAR
    assert game.next_level()
    assert game.level_index == 1
    assert game.status is GameStatus.PLAYING

    game.click(0, 0)
    assert game.status is GameStatus.LEVEL_CLEAR
    assert not game.next_level()
    assert game.status is GameStatus.ALL_CLEAR


def test_t05_mistakes_exhausted_enters_failure_and_can_restart() -> None:
    level = make_level("R...D.", "......", "......", "......", "......", "......")
    game = GameState((level,))

    for _ in range(3):
        game.click(0, 0)

    assert game.status is GameStatus.GAME_OVER
    assert game.mistakes_left == 0

    game.restart_current()
    assert game.status is GameStatus.PLAYING
    assert game.mistakes_left == 3
    assert game.board[0][0] == "R"


def test_t06_restart_restores_layout_count_and_mistakes() -> None:
    game = GameState((LEVELS[0],))
    initial_board = board_snapshot(game.board)
    initial_count = game.remaining

    assert game.click(2, 2).result is ClickResult.CLEARED
    assert game.click(0, 0).result is ClickResult.BLOCKED
    assert game.remaining < initial_count
    assert game.mistakes_left == 2

    game.restart_current()

    assert board_snapshot(game.board) == initial_board
    assert game.remaining == initial_count
    assert game.mistakes_left == 3
    assert game.status is GameStatus.PLAYING


@pytest.mark.parametrize("level", LEVELS, ids=lambda level: level.name)
def test_every_official_level_has_and_replays_a_solution(level: Level) -> None:
    board = level.create_board()
    order = solve_board(board)

    assert order is not None
    assert len(order) == sum(cell is not None for row in board for cell in row)

    for row, col in order:
        assert is_path_clear(board, row, col)
        board[row][col] = None
    assert all(cell is None for row in board for cell in row)


def test_empty_cell_does_not_change_game_state() -> None:
    game = GameState((LEVELS[0],))
    before = board_snapshot(game.board)

    outcome = game.click(1, 1)

    assert outcome.result is ClickResult.EMPTY
    assert board_snapshot(game.board) == before
    assert game.mistakes_left == 3

