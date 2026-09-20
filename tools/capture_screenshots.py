"""在无窗口模式下生成博客所需的界面截图。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pygame

from game_logic import GameStatus, solve_board
from ui import ArrowAnimation, ArrowGame, WINDOW_HEIGHT, WINDOW_WIDTH


OUTPUT_DIR = PROJECT_ROOT / "assets" / "screenshots"


def save(game: ArrowGame, name: str, now: float = 10.0) -> None:
    game.render(now)
    pygame.image.save(game.surface, OUTPUT_DIR / name)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pygame.init()
    surface = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
    app = ArrowGame(surface=surface)

    app.scene = "start"
    save(app, "01_start.png")

    app.start_new_game()
    save(app, "02_game.png")

    outcome = app.game.click(0, 0)
    app.notice = "前方有阻挡，机会 -1"
    app.animation = ArrowAnimation(
        "blocked", 0, 0, "R", 9.75, 0.55, outcome.blocker
    )
    save(app, "03_blocked.png")

    app.animation = None
    app.game.restart_current()
    solution = solve_board(app.game.board)
    assert solution is not None
    for row, col in solution:
        app.game.click(row, col)
    assert app.game.status is GameStatus.LEVEL_CLEAR
    app.scene = "level_clear"
    app.notice = ""
    save(app, "04_level_clear.png")

    app.game.restart_current()
    for _ in range(3):
        app.game.click(0, 0)
    assert app.game.status is GameStatus.GAME_OVER
    app.scene = "game_over"
    save(app, "05_game_over.png")

    app.start_new_game()
    while True:
        solution = solve_board(app.game.board)
        assert solution is not None
        for row, col in solution:
            app.game.click(row, col)
        assert app.game.status is GameStatus.LEVEL_CLEAR
        if not app.game.next_level():
            break
    assert app.game.status is GameStatus.ALL_CLEAR
    app.scene = "all_clear"
    save(app, "06_all_clear.png")
    pygame.quit()
    print(f"Generated screenshots in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
