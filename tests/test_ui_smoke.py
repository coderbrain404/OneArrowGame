"""Pygame 无窗口渲染和基本交互冒烟测试。"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

from game_logic import GameStatus, solve_board
from ui import ArrowGame, WINDOW_HEIGHT, WINDOW_WIDTH


def make_app() -> ArrowGame:
    pygame.init()
    return ArrowGame(surface=pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT)))


def test_all_main_scenes_render_without_error() -> None:
    app = make_app()
    for scene in ("start", "playing", "level_clear", "game_over", "all_clear"):
        app.scene = scene
        rendered = app.render(1.0)
        assert rendered.get_size() == (WINDOW_WIDTH, WINDOW_HEIGHT)


def test_successful_board_click_creates_animation_and_reaches_clear_scene() -> None:
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

