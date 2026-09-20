"""Pygame 界面、鼠标交互和动画。"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from pathlib import Path

import pygame

from game_logic import ClickResult, GameState, GameStatus


WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 760
FPS = 60
BOARD_SIZE = 6
CELL_SIZE = 74
BOARD_PIXEL_SIZE = BOARD_SIZE * CELL_SIZE
BOARD_LEFT = (WINDOW_WIDTH - BOARD_PIXEL_SIZE) // 2
BOARD_TOP = 186

BACKGROUND_TOP = (13, 23, 46)
BACKGROUND_BOTTOM = (24, 44, 76)
CARD = (30, 48, 78)
CARD_LIGHT = (42, 65, 99)
TEXT = (238, 244, 255)
TEXT_MUTED = (154, 177, 207)
ACCENT = (78, 205, 196)
ACCENT_HOVER = (104, 230, 217)
DANGER = (244, 92, 105)
WARNING = (255, 190, 92)
GRID_LINE = (75, 103, 138)

ARROW_COLORS: dict[str, tuple[int, int, int]] = {
    "U": (91, 214, 164),
    "D": (99, 169, 255),
    "L": (255, 176, 94),
    "R": (182, 128, 255),
}
PIXEL_STEPS: dict[str, tuple[int, int]] = {
    "U": (0, -1),
    "D": (0, 1),
    "L": (-1, 0),
    "R": (1, 0),
}


@dataclass(slots=True)
class ArrowAnimation:
    kind: str
    row: int
    col: int
    direction: str
    started_at: float
    duration: float
    blocker: tuple[int, int] | None = None

    def progress(self, now: float) -> float:
        return max(0.0, min(1.0, (now - self.started_at) / self.duration))

    def finished(self, now: float) -> bool:
        return now - self.started_at >= self.duration


class ArrowGame:
    """将已测试的 `GameState` 变成可玩的图形界面。"""

    def __init__(self, surface: pygame.Surface | None = None) -> None:
        pygame.init()
        pygame.font.init()
        pygame.display.set_caption("一箭又一箭")
        self.surface = surface or pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()
        self.fonts = {
            "hero": self._load_font(62, bold=True),
            "title": self._load_font(34, bold=True),
            "large": self._load_font(28, bold=True),
            "body": self._load_font(22),
            "small": self._load_font(17),
            "tiny": self._load_font(14),
        }
        self.game = GameState()
        self.scene = "start"
        self.animation: ArrowAnimation | None = None
        self.running = False
        self.notice = ""

    @staticmethod
    def _load_font(size: int, bold: bool = False) -> pygame.font.Font:
        # Pygame 2.6.1 + Python 3.13 在部分 Windows 机器上枚举字体
        # 注册表时会因异常数值崩溃，因此不使用 SysFont/match_font。
        windows_fonts = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
        if bold:
            names = ("msyhbd.ttc", "msyh.ttc", "simhei.ttf")
        else:
            names = ("msyh.ttc", "msyhbd.ttc", "simhei.ttf")
        candidates = [windows_fonts / name for name in names]
        candidates.extend(
            (
                Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
                Path("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"),
                Path("/System/Library/Fonts/PingFang.ttc"),
            )
        )
        for path in candidates:
            if path.is_file():
                return pygame.font.Font(str(path), size)
        return pygame.font.Font(None, size)

    @staticmethod
    def now() -> float:
        return pygame.time.get_ticks() / 1000.0

    def run(self) -> None:
        self.running = True
        while self.running:
            now = self.now()
            for event in pygame.event.get():
                self.handle_event(event, now)
            self.update(now)
            self.render(now)
            pygame.display.flip()
            self.clock.tick(FPS)
        pygame.quit()

    def start_new_game(self) -> None:
        self.game.restart_game()
        self.scene = "playing"
        self.animation = None
        self.notice = ""

    def handle_event(self, event: pygame.event.Event, now: float) -> None:
        if event.type == pygame.QUIT:
            self.running = False
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.scene == "start":
                    self.running = False
                else:
                    self.scene = "start"
                    self.animation = None
                return
            if self.scene == "start" and event.key in (pygame.K_SPACE, pygame.K_RETURN):
                self.start_new_game()
                return
            if self.scene == "playing" and event.key == pygame.K_r and self.animation is None:
                self.game.restart_current()
                self.notice = "已重新开始本关"
                return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.handle_click(event.pos, now)

    def handle_click(self, position: tuple[int, int], now: float) -> None:
        if self.scene == "start":
            if self._start_button().collidepoint(position):
                self.start_new_game()
            return

        if self.scene == "playing":
            buttons = self._playing_buttons()
            if buttons["restart"].collidepoint(position) and self.animation is None:
                self.game.restart_current()
                self.notice = "已重新开始本关"
                return
            if buttons["home"].collidepoint(position):
                self.scene = "start"
                self.animation = None
                return
            if self.animation is not None:
                return
            cell = self.pixel_to_cell(position)
            if cell is not None:
                self._click_board(*cell, now)
            return

        buttons = self._result_buttons()
        if buttons["primary"].collidepoint(position):
            if self.scene == "level_clear":
                loaded = self.game.next_level()
                self.scene = "playing" if loaded else "all_clear"
            elif self.scene == "game_over":
                self.game.restart_current()
                self.scene = "playing"
            elif self.scene == "all_clear":
                self.start_new_game()
            self.animation = None
            self.notice = ""
            return
        if buttons["secondary"].collidepoint(position):
            self.scene = "start"
            self.animation = None

    def pixel_to_cell(self, position: tuple[int, int]) -> tuple[int, int] | None:
        x, y = position
        if not (
            BOARD_LEFT <= x < BOARD_LEFT + BOARD_PIXEL_SIZE
            and BOARD_TOP <= y < BOARD_TOP + BOARD_PIXEL_SIZE
        ):
            return None
        return (y - BOARD_TOP) // CELL_SIZE, (x - BOARD_LEFT) // CELL_SIZE

    def _click_board(self, row: int, col: int, now: float) -> None:
        outcome = self.game.click(row, col)
        if outcome.result is ClickResult.CLEARED and outcome.direction is not None:
            self.animation = ArrowAnimation(
                "fly", row, col, outcome.direction, now, 0.48
            )
            self.notice = "路径畅通！"
        elif outcome.result is ClickResult.BLOCKED and outcome.direction is not None:
            self.animation = ArrowAnimation(
                "blocked",
                row,
                col,
                outcome.direction,
                now,
                0.55,
                outcome.blocker,
            )
            self.notice = "前方有阻挡，机会 -1"
        elif outcome.result is ClickResult.EMPTY:
            self.notice = "请点击箭头"

    def update(self, now: float) -> None:
        if self.animation is None or not self.animation.finished(now):
            return
        self.animation = None
        if self.game.status is GameStatus.LEVEL_CLEAR:
            self.scene = "level_clear"
        elif self.game.status is GameStatus.GAME_OVER:
            self.scene = "game_over"

    def render(self, now: float | None = None) -> pygame.Surface:
        now = self.now() if now is None else now
        self._draw_background()
        if self.scene == "start":
            self._draw_start_scene()
        else:
            self._draw_game_scene(now)
            if self.scene in {"level_clear", "game_over", "all_clear"}:
                self._draw_result_overlay()
        return self.surface

    def _draw_background(self) -> None:
        for y in range(WINDOW_HEIGHT):
            ratio = y / max(1, WINDOW_HEIGHT - 1)
            color = tuple(
                round(top + (bottom - top) * ratio)
                for top, bottom in zip(BACKGROUND_TOP, BACKGROUND_BOTTOM)
            )
            pygame.draw.line(self.surface, color, (0, y), (WINDOW_WIDTH, y))
        pygame.draw.circle(self.surface, (31, 62, 95), (90, 100), 155, width=2)
        pygame.draw.circle(self.surface, (37, 73, 106), (930, 670), 210, width=2)
        pygame.draw.circle(self.surface, (48, 84, 114), (870, 95), 54, width=1)

    def _draw_start_scene(self) -> None:
        self._draw_center_text("一箭又一箭", self.fonts["hero"], TEXT, 150)
        self._draw_center_text(
            "观察方向 · 找到出口 · 依次清空",
            self.fonts["body"],
            TEXT_MUTED,
            226,
        )

        center_y = 335
        for index, direction in enumerate(("U", "R", "D", "L")):
            center_x = 350 + index * 100
            self._draw_arrow((center_x, center_y), direction, ARROW_COLORS[direction], 1.08)

        panel = pygame.Rect(260, 402, 480, 92)
        self._draw_card(panel, CARD, radius=20)
        lines = (
            "点击箭头，前方无阻挡即可飞出",
            "被阻挡会消耗机会，每共有 3 次机会",
        )
        for index, line in enumerate(lines):
            self._draw_center_text(line, self.fonts["small"], TEXT_MUTED, 430 + index * 30)

        self._draw_button(self._start_button(), "开始游戏", primary=True)
        self._draw_center_text(
            "空格 / Enter 开始   ·   Esc 退出",
            self.fonts["tiny"],
            TEXT_MUTED,
            660,
        )

    def _draw_game_scene(self, now: float) -> None:
        self._draw_hud()
        self._draw_board(now)
        for name, rect in self._playing_buttons().items():
            label = "重新开始  R" if name == "restart" else "返回首页"
            self._draw_button(rect, label, primary=name == "restart")
        if self.notice:
            color = DANGER if "阻挡" in self.notice else TEXT_MUTED
            self._draw_center_text(self.notice, self.fonts["small"], color, 675)

    def _draw_hud(self) -> None:
        panel = pygame.Rect(90, 68, 820, 88)
        self._draw_card(panel, CARD, radius=20)
        self._draw_text(
            self.game.current_level.name,
            self.fonts["large"],
            TEXT,
            (122, 89),
        )
        self._draw_text(
            f"关卡 {self.game.level_index + 1}/{len(self.game.levels)}",
            self.fonts["small"],
            TEXT_MUTED,
            (124, 126),
        )

        self._draw_stat(570, 90, "剩余箭头", str(self.game.remaining), ACCENT)
        self._draw_stat(740, 90, "剩余机会", str(self.game.mistakes_left), WARNING)

    def _draw_stat(
        self, x: int, y: int, label: str, value: str, value_color: tuple[int, int, int]
    ) -> None:
        self._draw_text(label, self.fonts["tiny"], TEXT_MUTED, (x, y))
        self._draw_text(value, self.fonts["title"], value_color, (x, y + 20))

    def _draw_board(self, now: float) -> None:
        shadow = pygame.Rect(
            BOARD_LEFT - 13,
            BOARD_TOP - 13,
            BOARD_PIXEL_SIZE + 26,
            BOARD_PIXEL_SIZE + 26,
        )
        self._draw_card(shadow, (17, 29, 50), radius=24)
        board_rect = pygame.Rect(BOARD_LEFT, BOARD_TOP, BOARD_PIXEL_SIZE, BOARD_PIXEL_SIZE)
        self._draw_card(board_rect, CARD_LIGHT, radius=16)

        animated_cell: tuple[int, int] | None = None
        if self.animation is not None and self.animation.kind == "blocked":
            animated_cell = self.animation.row, self.animation.col

        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                cell = pygame.Rect(
                    BOARD_LEFT + col * CELL_SIZE + 3,
                    BOARD_TOP + row * CELL_SIZE + 3,
                    CELL_SIZE - 6,
                    CELL_SIZE - 6,
                )
                pygame.draw.rect(self.surface, (34, 55, 88), cell, border_radius=12)
                pygame.draw.rect(self.surface, GRID_LINE, cell, width=1, border_radius=12)
                tile = self.game.board[row][col]
                if tile is not None and animated_cell != (row, col):
                    self._draw_arrow(self.cell_center(row, col), tile, ARROW_COLORS[tile])

        if self.animation is not None:
            self._draw_animation(self.animation, now)

    def _draw_animation(self, animation: ArrowAnimation, now: float) -> None:
        progress = animation.progress(now)
        center_x, center_y = self.cell_center(animation.row, animation.col)
        step_x, step_y = PIXEL_STEPS[animation.direction]

        if animation.kind == "fly":
            eased = 1 - (1 - progress) ** 3
            distance = BOARD_PIXEL_SIZE * 0.85
            offset = step_x * distance * eased, step_y * distance * eased
            color = ARROW_COLORS[animation.direction]
            self._draw_arrow(
                (center_x + offset[0], center_y + offset[1]),
                animation.direction,
                color,
                scale=max(0.55, 1 - 0.35 * progress),
                alpha=round(255 * (1 - 0.75 * progress)),
            )
            return

        forward = math.sin(progress * math.pi) * 12
        shake = math.sin(progress * math.pi * 9) * (1 - progress) * 7
        perpendicular_x, perpendicular_y = -step_y, step_x
        offset_x = step_x * forward + perpendicular_x * shake
        offset_y = step_y * forward + perpendicular_y * shake
        self._draw_arrow(
            (center_x + offset_x, center_y + offset_y),
            animation.direction,
            DANGER,
            scale=1.06,
        )

        if animation.blocker is not None:
            blocker_center = self.cell_center(*animation.blocker)
            radius = round(18 + math.sin(progress * math.pi) * 10)
            pygame.draw.circle(self.surface, DANGER, blocker_center, radius, width=3)

    def _draw_result_overlay(self) -> None:
        veil = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        veil.fill((7, 13, 27, 184))
        self.surface.blit(veil, (0, 0))

        panel = pygame.Rect(255, 195, 490, 365)
        self._draw_card(panel, (31, 50, 81), radius=28)
        pygame.draw.rect(self.surface, (77, 104, 139), panel, width=1, border_radius=28)

        if self.scene == "level_clear":
            title = "本关完成！"
            subtitle = f"已清空 {self.game.current_level.name}"
            color = ACCENT
            primary = "下一关" if self.game.level_index + 1 < len(self.game.levels) else "查看结果"
        elif self.scene == "game_over":
            title = "挑战失败"
            subtitle = "失误机会已用尽，再观察一下阻挡关系"
            color = DANGER
            primary = "重新挑战"
        else:
            title = "全部通关！"
            subtitle = "三个箭阵已全部解开"
            color = WARNING
            primary = "再玩一次"

        self._draw_center_text(title, self.fonts["title"], color, 250)
        self._draw_center_text(subtitle, self.fonts["small"], TEXT_MUTED, 310)
        if self.scene == "level_clear":
            self._draw_center_text(
                f"剩余机会：{self.game.mistakes_left}",
                self.fonts["body"],
                TEXT,
                356,
            )
        elif self.scene == "all_clear":
            self._draw_center_text("恭喜完成本次挑战", self.fonts["body"], TEXT, 356)

        buttons = self._result_buttons()
        self._draw_button(buttons["primary"], primary, primary=True)
        self._draw_button(buttons["secondary"], "返回首页", primary=False)

    def _draw_arrow(
        self,
        center: tuple[float, float],
        direction: str,
        color: tuple[int, int, int],
        scale: float = 1.0,
        alpha: int = 255,
    ) -> None:
        size = max(58, round(CELL_SIZE * 1.25 * scale))
        layer = pygame.Surface((size, size), pygame.SRCALPHA)
        layer_center = size // 2, size // 2
        base_alpha = max(0, min(255, round(alpha * 0.22)))
        line_alpha = max(0, min(255, alpha))
        pygame.draw.circle(layer, (*color, base_alpha), layer_center, round(27 * scale))
        pygame.draw.circle(
            layer, (*color, round(line_alpha * 0.7)), layer_center, round(27 * scale), width=2
        )

        step_x, step_y = PIXEL_STEPS[direction]
        tail = (
            layer_center[0] - step_x * round(15 * scale),
            layer_center[1] - step_y * round(15 * scale),
        )
        head = (
            layer_center[0] + step_x * round(18 * scale),
            layer_center[1] + step_y * round(18 * scale),
        )
        width = max(4, round(6 * scale))
        pygame.draw.line(layer, (*color, line_alpha), tail, head, width=width)

        perpendicular_x, perpendicular_y = -step_y, step_x
        wing_length = round(11 * scale)
        wing_back = round(10 * scale)
        for sign in (-1, 1):
            wing = (
                head[0] - step_x * wing_back + perpendicular_x * wing_length * sign,
                head[1] - step_y * wing_back + perpendicular_y * wing_length * sign,
            )
            pygame.draw.line(layer, (*color, line_alpha), head, wing, width=width)

        rect = layer.get_rect(center=(round(center[0]), round(center[1])))
        self.surface.blit(layer, rect)

    def _draw_button(self, rect: pygame.Rect, label: str, primary: bool) -> None:
        mouse_position = pygame.mouse.get_pos()
        hovered = rect.collidepoint(mouse_position)
        if primary:
            color = ACCENT_HOVER if hovered else ACCENT
            text_color = (12, 35, 43)
        else:
            color = (55, 76, 108) if hovered else (44, 64, 94)
            text_color = TEXT
        pygame.draw.rect(self.surface, (9, 17, 32), rect.move(0, 5), border_radius=14)
        pygame.draw.rect(self.surface, color, rect, border_radius=14)
        self._draw_centered_in_rect(label, self.fonts["small"], text_color, rect)

    def _draw_card(
        self,
        rect: pygame.Rect,
        color: tuple[int, int, int],
        radius: int,
    ) -> None:
        pygame.draw.rect(self.surface, (7, 14, 29), rect.move(0, 7), border_radius=radius)
        pygame.draw.rect(self.surface, color, rect, border_radius=radius)

    def _draw_center_text(
        self,
        text: str,
        font: pygame.font.Font,
        color: tuple[int, int, int],
        y: int,
    ) -> None:
        image = font.render(text, True, color)
        self.surface.blit(image, image.get_rect(center=(WINDOW_WIDTH // 2, y)))

    def _draw_text(
        self,
        text: str,
        font: pygame.font.Font,
        color: tuple[int, int, int],
        position: tuple[int, int],
    ) -> None:
        self.surface.blit(font.render(text, True, color), position)

    def _draw_centered_in_rect(
        self,
        text: str,
        font: pygame.font.Font,
        color: tuple[int, int, int],
        rect: pygame.Rect,
    ) -> None:
        image = font.render(text, True, color)
        self.surface.blit(image, image.get_rect(center=rect.center))

    @staticmethod
    def cell_center(row: int, col: int) -> tuple[int, int]:
        return (
            BOARD_LEFT + col * CELL_SIZE + CELL_SIZE // 2,
            BOARD_TOP + row * CELL_SIZE + CELL_SIZE // 2,
        )

    @staticmethod
    def _start_button() -> pygame.Rect:
        return pygame.Rect(350, 535, 300, 66)

    @staticmethod
    def _playing_buttons() -> dict[str, pygame.Rect]:
        return {
            "restart": pygame.Rect(330, 704, 190, 42),
            "home": pygame.Rect(540, 704, 130, 42),
        }

    @staticmethod
    def _result_buttons() -> dict[str, pygame.Rect]:
        return {
            "primary": pygame.Rect(330, 416, 340, 54),
            "secondary": pygame.Rect(330, 486, 340, 48),
        }
