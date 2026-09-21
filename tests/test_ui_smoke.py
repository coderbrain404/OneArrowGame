"""Pygame 无窗口渲染和基本交互冒烟测试。"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from game_logic import GameStatus, solve_board
from save_manager import Progress
from ui import ArrowGame, WINDOW_HEIGHT, WINDOW_WIDTH


def make_app() -> ArrowGame:
    pygame.init()
    return ArrowGame(surface=pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT)))


def test_all_main_scenes_render_without_error() -> None:
    app = make_app()
    for scene in ("start", "level_select", "playing", "level_clear", "game_over", "all_clear"):
        app.scene = scene
        rendered = app.render(1.0)
        assert rendered.get_size() == (WINDOW_WIDTH, WINDOW_HEIGHT)


def test_successful_board_click_creates_animation_and_reaches_clear_scene(monkeypatch) -> None:
    monkeypatch.setattr("ui.save_progress", lambda progress: True)
    app = make_app()
    app.start_new_game()
    solution = solve_board(app.game.board)
    assert solution is not None

    for row, col in solution[:-1]:
        app.game.click(row, col)
    final_row, final_col = solution[-1]
    app._click_board(final_row, final_col, now=1.0)

    assert app.animation is not None
    assert app.game.status is GameStatus.LEVEL_CLEAR
    app.update(now=2.0)
    assert app.animation is None
    assert app.scene == "level_clear"


def test_restart_button_restores_current_level() -> None:
    app = make_app()
    app.start_new_game()
    app.game.click(2, 2)
    assert app.game.remaining < 8

    app.handle_click(app._playing_buttons()["restart"].center, now=1.0)

    assert app.game.remaining == 8
    assert app.game.mistakes_left == 3


def test_locked_level_card_is_ignored_and_unlocked_card_opens() -> None:
    app = make_app()
    app.progress = Progress(unlocked_level=0)
    app.scene = "level_select"

    app.handle_click(app._level_cards()[1].center, now=1.0)
    assert app.scene == "level_select"

    app.progress.unlocked_level = 1
    app.handle_click(app._level_cards()[1].center, now=2.0)
    assert app.scene == "playing"
    assert app.game.level_index == 1


def test_hint_is_once_per_attempt_and_restart_restores_it() -> None:
    app = make_app()
    app.start_level(0, now=0.0)

    app.use_hint(now=1.0)
    first_hint = app.hint_cell
    app.use_hint(now=1.1)

    assert first_hint is not None
    assert app.hint_cell == first_hint
    assert app.hint_used

    app.restart_current(now=2.0)
    assert not app.hint_used
    assert app.hint_cell is None
