"""Pygame 界面、鼠标交互和武侠主题动画。"""

from __future__ import annotations

import math
import os
import random
from dataclasses import dataclass
from pathlib import Path

import pygame

from game_logic import ClickResult, GameState, GameStatus, find_hint
from save_manager import Progress, load_progress, save_progress

WINDOW_WIDTH, WINDOW_HEIGHT, FPS = 1000, 760, 60
BOARD_SIZE, CELL_SIZE = 6, 74
BOARD_PIXEL_SIZE = BOARD_SIZE * CELL_SIZE
BOARD_LEFT = (WINDOW_WIDTH - BOARD_PIXEL_SIZE) // 2
BOARD_TOP = 186

INK, INK_MUTED = (31, 25, 22), (92, 70, 48)
PAPER, TEXT, TEXT_MUTED = (231, 211, 168), (241, 235, 211), (178, 193, 190)
JADE, CINNABAR, CINNABAR_HOVER = (84, 190, 157), (177, 65, 49), (205, 83, 61)
GOLD, DANGER, GRID_LINE = (222, 174, 76), (211, 69, 60), (102, 133, 137)
ARROW_COLORS = {"U": (82, 205, 155), "D": (88, 164, 224), "L": (232, 168, 77), "R": (179, 122, 213)}
PIXEL_STEPS = {"U": (0, -1), "D": (0, 1), "L": (-1, 0), "R": (1, 0)}


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
    """将已测试的 `GameState` 变成可玩的武侠风图形界面。"""

    def __init__(self, surface: pygame.Surface | None = None) -> None:
        pygame.init()
        pygame.font.init()
        pygame.display.set_caption("一箭又一箭")
        self.surface = surface or pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()
        self.fonts = {
            "hero": self._load_font(68, True, True), "title": self._load_font(36, True),
            "large": self._load_font(28, True), "body": self._load_font(22),
            "small": self._load_font(17), "tiny": self._load_font(14),
        }
        self.assets = self._load_assets()
        self.game = GameState()
        self.progress: Progress = load_progress(level_count=len(self.game.levels))
        self.scene = "start"
        self.animation: ArrowAnimation | None = None
        self.running = False
        self.notice = ""
        self.scene_started_at = self.now()
        self.level_started_at = self.now()
        self.hint_cell: tuple[int, int] | None = None
        self.hint_started_at = 0.0
        self.hint_used = False
        self.entry_duration = 0.0
        rng = random.Random(20260921)
        self.fireflies = [(rng.randrange(35, 965), rng.randrange(65, 700), rng.uniform(0.5, 1.4), rng.random() * math.tau) for _ in range(22)]

    @staticmethod
    def _load_font(size: int, bold: bool = False, calligraphy: bool = False) -> pygame.font.Font:
        windows_fonts = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
        if calligraphy:
            names = ("simkai.ttf", "STKAITI.TTF", "STXINGKA.TTF", "msyhbd.ttc")
        elif bold:
            names = ("msyhbd.ttc", "msyh.ttc", "simhei.ttf")
        else:
            names = ("msyh.ttc", "msyhbd.ttc", "simhei.ttf")
        candidates = [windows_fonts / name for name in names]
        candidates += [Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"), Path("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"), Path("/System/Library/Fonts/PingFang.ttc")]
        for path in candidates:
            if path.is_file():
                return pygame.font.Font(str(path), size)
        return pygame.font.Font(None, size)

    def _load_assets(self) -> dict[str, pygame.Surface | None]:
        asset_dir = Path(__file__).resolve().parent / "assets" / "wuxia"
        sizes = {"bg.png": (WINDOW_WIDTH, WINDOW_HEIGHT), "board.png": (560, 560), "scroll.png": (560, 410)}
        loaded: dict[str, pygame.Surface | None] = {}
        for filename, size in sizes.items():
            try:
                loaded[filename] = pygame.transform.smoothscale(pygame.image.load(str(asset_dir / filename)), size)
            except (FileNotFoundError, pygame.error):
                loaded[filename] = None
        return loaded

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

    def _set_scene(self, scene: str, now: float | None = None) -> None:
        self.scene = scene
        self.scene_started_at = self.now() if now is None else now

    def start_new_game(self) -> None:
        """兼容原有入口：从第一关开始。"""
        self.start_level(0)

    def continue_game(self, now: float | None = None) -> None:
        self.start_level(self.progress.unlocked_level, now)

    def start_level(self, index: int, now: float | None = None) -> None:
        current_time = self.now() if now is None else now
        self.game.load_level(index)
        self._set_scene("playing", current_time)
        self.animation = None
        self.notice = ""
        self.hint_cell = None
        self.hint_used = False
        self.level_started_at = current_time
        self.entry_duration = min(0.58, max(0.18, (self.game.remaining - 1) * 0.03 + 0.10))

    def restart_current(self, now: float) -> None:
        self.start_level(self.game.level_index, now)
        self.notice = "本关箭阵已复原"

    def handle_event(self, event: pygame.event.Event, now: float) -> None:
        if event.type == pygame.QUIT:
            self.running = False
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.scene == "start":
                    self.running = False
                elif self.scene == "level_select":
                    self._set_scene("start", now)
                else:
                    self._set_scene("start", now)
                    self.animation = self.hint_cell = None
                return
            if self.scene == "start" and event.key in (pygame.K_SPACE, pygame.K_RETURN):
                self.continue_game(now)
                return
            if self.scene == "playing" and event.key == pygame.K_r and not self._input_locked(now):
                self.restart_current(now)
                return
            if self.scene == "playing" and event.key == pygame.K_h and not self._input_locked(now):
                self.use_hint(now)
                return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.handle_click(event.pos, now)

    def handle_click(self, position: tuple[int, int], now: float) -> None:
        if self.scene == "start":
            buttons = self._start_buttons()
            if buttons["continue"].collidepoint(position):
                self.continue_game(now)
            elif buttons["select"].collidepoint(position):
                self._set_scene("level_select", now)
            return
        if self.scene == "level_select":
            if self._select_back_button().collidepoint(position):
                self._set_scene("start", now)
                return
            for index, rect in enumerate(self._level_cards()):
                if rect.collidepoint(position) and index <= self.progress.unlocked_level:
                    self.start_level(index, now)
                    return
            return
        if self.scene == "playing":
            buttons = self._playing_buttons()
            if buttons["home"].collidepoint(position):
                self._set_scene("start", now)
                self.animation = self.hint_cell = None
                return
            if self._input_locked(now):
                return
            if buttons["restart"].collidepoint(position):
                self.restart_current(now)
                return
            if buttons["hint"].collidepoint(position):
                self.use_hint(now)
                return
            cell = self.pixel_to_cell(position)
            if cell is not None:
                self._click_board(*cell, now)
            return
        buttons = self._result_buttons()
        if buttons["primary"].collidepoint(position):
            if self.scene == "level_clear":
                if self.game.level_index + 1 < len(self.game.levels):
                    self.start_level(self.game.level_index + 1, now)
                else:
                    self.game.status = GameStatus.ALL_CLEAR
                    self._set_scene("all_clear", now)
            elif self.scene == "game_over":
                self.restart_current(now)
            elif self.scene == "all_clear":
                self._set_scene("level_select", now)
            return
        if buttons["secondary"].collidepoint(position):
            self._set_scene("level_select", now)
            self.animation = self.hint_cell = None

    def pixel_to_cell(self, position: tuple[int, int]) -> tuple[int, int] | None:
        x, y = position
        if not (BOARD_LEFT <= x < BOARD_LEFT + BOARD_PIXEL_SIZE and BOARD_TOP <= y < BOARD_TOP + BOARD_PIXEL_SIZE):
            return None
        return (y - BOARD_TOP) // CELL_SIZE, (x - BOARD_LEFT) // CELL_SIZE

    def use_hint(self, now: float) -> None:
        if self.hint_used:
            self.notice = "本次挑战的锦囊已用过"
            return
        cell = find_hint(self.game.board)
        if cell is None:
            self.notice = "此刻无可提示的箭矢"
            return
        self.hint_used, self.hint_cell, self.hint_started_at = True, cell, now
        self.notice = "锦囊：留意光环所指"

    def _click_board(self, row: int, col: int, now: float) -> None:
        outcome = self.game.click(row, col)
        if outcome.result is ClickResult.CLEARED and outcome.direction is not None:
            self.animation = ArrowAnimation("fly", row, col, outcome.direction, now, 0.48)
            self.notice = "破空而出"
        elif outcome.result is ClickResult.BLOCKED and outcome.direction is not None:
            self.animation = ArrowAnimation("blocked", row, col, outcome.direction, now, 0.55, outcome.blocker)
            self.notice = "被格挡！气力 -1"
        elif outcome.result is ClickResult.EMPTY:
            self.notice = "请点箭矢"

    def _input_locked(self, now: float) -> bool:
        return self.animation is not None or now - self.level_started_at < self.entry_duration or (self.hint_cell is not None and now - self.hint_started_at < 1.2)

    def update(self, now: float) -> None:
        if self.hint_cell is not None and now - self.hint_started_at >= 1.2:
            self.hint_cell = None
        if self.animation is None or not self.animation.finished(now):
            return
        self.animation = None
        if self.game.status is GameStatus.LEVEL_CLEAR:
            self.progress.mark_completed(self.game.level_index, len(self.game.levels))
            if not save_progress(self.progress):
                self.notice = "进度暂时无法写入存档"
            self._set_scene("level_clear", now)
        elif self.game.status is GameStatus.GAME_OVER:
            self._set_scene("game_over", now)

    def render(self, now: float | None = None) -> pygame.Surface:
        now = self.now() if now is None else now
        self._draw_background(now)
        if self.scene == "start":
            self._draw_start_scene()
        elif self.scene == "level_select":
            self._draw_level_select()
        else:
            self._draw_game_scene(now)
            if self.scene in {"level_clear", "game_over", "all_clear"}:
                self._draw_result_overlay(now)
        return self.surface

    def _draw_background(self, now: float) -> None:
        background = self.assets["bg.png"]
        self.surface.blit(background, (0, 0)) if background is not None else self.surface.fill((19, 54, 65))
        veil = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        veil.fill((4, 13, 22, 76))
        for index in range(3):
            x = int(((now * (10 + index * 4) + index * 360) % 1300) - 220)
            pygame.draw.ellipse(veil, (176, 209, 201, 10), (x, 470 + index * 55, 520, 95))
        self.surface.blit(veil, (0, 0))
        for x, y, speed, phase in self.fireflies:
            pulse = (math.sin(now * speed + phase) + 1) / 2
            glow = pygame.Surface((12, 12), pygame.SRCALPHA)
            pygame.draw.circle(glow, (238, 199, 103, round(45 + pulse * 125)), (6, 6), 1 + round(pulse * 2))
            self.surface.blit(glow, (x - 6, y - 6))

    def _draw_start_scene(self) -> None:
        self._draw_center_text("一箭又一箭", self.fonts["hero"], PAPER, 133, (2, 3))
        self._draw_center_text("观箭路 · 破箭阵 · 闯江湖", self.fonts["body"], TEXT_MUTED, 218)
        for index, direction in enumerate(("U", "R", "D", "L")):
            self._draw_arrow((350 + index * 100, 307), direction, ARROW_COLORS[direction], 1.02)
        panel = pygame.Rect(255, 365, 490, 105)
        self._draw_card(panel, (18, 38, 48, 220), 18, GOLD)
        self._draw_center_text("箭矢前方无阻，方可破空而出", self.fonts["small"], TEXT, 397)
        self._draw_center_text("遇阻则耗气力，各关气力见关卡令", self.fonts["small"], TEXT_MUTED, 432)
        buttons = self._start_buttons()
        self._draw_button(buttons["continue"], "继续闯关", True)
        self._draw_button(buttons["select"], "选择关卡", False)
        self._draw_center_text("空格 / Enter 继续   ·   Esc 退出", self.fonts["tiny"], TEXT_MUTED, 708)

    def _draw_level_select(self) -> None:
        self._draw_center_text("江湖六阵", self.fonts["title"], PAPER, 72)
        self._draw_center_text("破前阵，方可启后阵", self.fonts["small"], TEXT_MUTED, 112)
        mouse = pygame.mouse.get_pos()
        for index, (level, rect) in enumerate(zip(self.game.levels, self._level_cards())):
            unlocked, completed = index <= self.progress.unlocked_level, index in self.progress.completed_levels
            color = (43, 69, 67, 236) if unlocked and rect.collidepoint(mouse) else (19, 42, 51, 232)
            self._draw_card(rect, color, 17, GOLD if completed else (100, 133, 127))
            self._draw_text(f"第 {index + 1} 阵", self.fonts["large"], GOLD if unlocked else (101, 113, 111), (rect.x + 24, rect.y + 20))
            self._draw_text(level.name.split("·", 1)[-1].strip(), self.fonts["small"], TEXT if unlocked else (105, 117, 115), (rect.x + 25, rect.y + 62))
            if completed:
                self._draw_text("已破", self.fonts["small"], CINNABAR_HOVER, (rect.right - 65, rect.y + 24))
            elif not unlocked:
                self._draw_text("未解锁", self.fonts["small"], (112, 119, 116), (rect.right - 87, rect.y + 24))
            else:
                self._draw_text(f"气力 {level.max_mistakes}", self.fonts["tiny"], TEXT_MUTED, (rect.right - 75, rect.bottom - 32))
        self._draw_button(self._select_back_button(), "返回首页", False)

    def _draw_game_scene(self, now: float) -> None:
        self._draw_board(now)
        self._draw_hud()
        for name, rect in self._playing_buttons().items():
            label = "重开本关  R" if name == "restart" else ("锦囊已用" if self.hint_used else "锦囊  H") if name == "hint" else "返回首页"
            self._draw_button(rect, label, name == "restart", name == "hint" and self.hint_used)
        if self.notice:
            self._draw_center_text(self.notice, self.fonts["small"], (255, 150, 129) if "格挡" in self.notice else TEXT, 675)

    def _draw_hud(self) -> None:
        panel = pygame.Rect(82, 54, 836, 108)
        self._draw_card(panel, (13, 31, 41, 238), 19, (89, 122, 117))
        self._draw_text(self.game.current_level.name, self.fonts["large"], TEXT, (112, 76))
        self._draw_text(f"江湖第 {self.game.level_index + 1}/{len(self.game.levels)} 阵", self.fonts["small"], TEXT_MUTED, (114, 118))
        self._draw_stat(570, 76, "余箭", str(self.game.remaining), JADE)
        self._draw_stat(710, 76, "气力", str(self.game.mistakes_left), GOLD)
        self._draw_stat(825, 76, "锦囊", "0" if self.hint_used else "1", PAPER)

    def _draw_stat(self, x: int, y: int, label: str, value: str, color: tuple[int, int, int]) -> None:
        self._draw_text(label, self.fonts["tiny"], TEXT_MUTED, (x, y))
        self._draw_text(value, self.fonts["title"], color, (x, y + 19))

    def _draw_board(self, now: float) -> None:
        board_image = self.assets["board.png"]
        if board_image is not None:
            self.surface.blit(board_image, board_image.get_rect(center=(WINDOW_WIDTH // 2, BOARD_TOP + BOARD_PIXEL_SIZE // 2)))
        else:
            self._draw_card(pygame.Rect(BOARD_LEFT - 18, BOARD_TOP - 18, BOARD_PIXEL_SIZE + 36, BOARD_PIXEL_SIZE + 36), (11, 24, 31, 245), 20, (91, 121, 118))
        animated_cell = (self.animation.row, self.animation.col) if self.animation is not None and self.animation.kind == "blocked" else None
        elapsed, tile_index = now - self.level_started_at, 0
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                cell = pygame.Rect(BOARD_LEFT + col * CELL_SIZE + 3, BOARD_TOP + row * CELL_SIZE + 3, CELL_SIZE - 6, CELL_SIZE - 6)
                layer = pygame.Surface(cell.size, pygame.SRCALPHA)
                pygame.draw.rect(layer, (11, 31, 40, 188), layer.get_rect(), border_radius=10)
                pygame.draw.rect(layer, (*GRID_LINE, 185), layer.get_rect(), width=1, border_radius=10)
                self.surface.blit(layer, cell)
                tile = self.game.board[row][col]
                if tile is not None and animated_cell != (row, col):
                    delay = tile_index * 0.03
                    if elapsed >= delay:
                        progress = min(1.0, max(0.0, (elapsed - delay) / 0.10))
                        scale = 0.60 + 0.40 * (1 - (1 - progress) ** 3) + (math.sin(progress * math.pi) * 0.08 if progress < 1 else 0)
                        self._draw_arrow(self.cell_center(row, col), tile, ARROW_COLORS[tile], scale)
                    tile_index += 1
        if self.hint_cell is not None:
            center = self.cell_center(*self.hint_cell)
            pulse = (math.sin((now - self.hint_started_at) * math.tau * 2.2) + 1) / 2
            radius = round(29 + pulse * 9)
            pygame.draw.circle(self.surface, GOLD, center, radius, width=3)
            pygame.draw.circle(self.surface, PAPER, center, radius + 5, width=1)
        if self.animation is not None:
            self._draw_animation(self.animation, now)

    def _draw_animation(self, animation: ArrowAnimation, now: float) -> None:
        progress = animation.progress(now)
        center_x, center_y = self.cell_center(animation.row, animation.col)
        step_x, step_y = PIXEL_STEPS[animation.direction]
        if animation.kind == "fly":
            eased, distance = 1 - (1 - progress) ** 3, BOARD_PIXEL_SIZE * 0.85
            x, y = center_x + step_x * distance * eased, center_y + step_y * distance * eased
            color = ARROW_COLORS[animation.direction]
            for offset, alpha, scale in ((18, 45, 0.78), (9, 90, 0.88)):
                self._draw_arrow((x - step_x * offset, y - step_y * offset), animation.direction, color, scale, alpha)
            self._draw_arrow((x, y), animation.direction, color, max(0.55, 1 - 0.35 * progress), round(255 * (1 - 0.75 * progress)))
            return
        forward, shake = math.sin(progress * math.pi) * 12, math.sin(progress * math.pi * 9) * (1 - progress) * 7
        perpendicular_x, perpendicular_y = -step_y, step_x
        self._draw_arrow((center_x + step_x * forward + perpendicular_x * shake, center_y + step_y * forward + perpendicular_y * shake), animation.direction, DANGER, 1.06)
        for index in range(7):
            angle, distance = index * math.tau / 7 + 0.25, 8 + 25 * math.sin(progress * math.pi)
            pygame.draw.circle(self.surface, DANGER, (round(center_x + math.cos(angle) * distance), round(center_y + math.sin(angle) * distance)), max(1, round(4 * (1 - progress))))
        if animation.blocker is not None:
            pygame.draw.circle(self.surface, DANGER, self.cell_center(*animation.blocker), round(18 + math.sin(progress * math.pi) * 10), width=3)

    def _draw_result_overlay(self, now: float) -> None:
        alpha = round(255 * min(1.0, max(0.0, (now - self.scene_started_at) / 0.20)))
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((3, 10, 15, round(165 * alpha / 255)))
        scroll = self.assets["scroll.png"]
        if scroll is not None:
            scroll_copy = scroll.copy(); scroll_copy.set_alpha(alpha)
            overlay.blit(scroll_copy, scroll_copy.get_rect(center=(WINDOW_WIDTH // 2, 380)))
        else:
            pygame.draw.rect(overlay, (*PAPER, alpha), (225, 176, 550, 410), border_radius=20)
        self.surface.blit(overlay, (0, 0))
        if self.scene == "level_clear":
            title, subtitle, color = "破关成功！", f"已破 {self.game.current_level.name}", CINNABAR
            primary = "前往下一阵" if self.game.level_index + 1 < len(self.game.levels) else "名震江湖"
        elif self.scene == "game_over":
            title, subtitle, color, primary = "力竭而止", "气力耗尽，再察箭路", (145, 45, 37), "重新挑战"
        else:
            title, subtitle, color, primary = "江湖尽破！", "六座箭阵皆已破解", (150, 101, 25), "查看关卡"
        self._draw_center_text(title, self.fonts["title"], color, 257)
        self._draw_center_text(subtitle, self.fonts["small"], INK_MUTED, 311)
        self._draw_center_text(f"余下气力：{self.game.mistakes_left}" if self.scene == "level_clear" else "一箭既出，万阻皆开" if self.scene == "all_clear" else "", self.fonts["body"], INK, 354)
        buttons = self._result_buttons()
        self._draw_button(buttons["primary"], primary, True, parchment=True)
        self._draw_button(buttons["secondary"], "返回选关", False, parchment=True)

    def _draw_arrow(self, center: tuple[float, float], direction: str, color: tuple[int, int, int], scale: float = 1.0, alpha: int = 255) -> None:
        size = max(58, round(CELL_SIZE * 1.25 * scale))
        layer = pygame.Surface((size, size), pygame.SRCALPHA)
        middle = size // 2, size // 2
        pygame.draw.circle(layer, (*color, round(alpha * 0.20)), middle, round(27 * scale))
        pygame.draw.circle(layer, (*color, round(alpha * 0.72)), middle, round(27 * scale), width=2)
        step_x, step_y = PIXEL_STEPS[direction]
        tail = (middle[0] - step_x * round(15 * scale), middle[1] - step_y * round(15 * scale))
        head = (middle[0] + step_x * round(18 * scale), middle[1] + step_y * round(18 * scale))
        width = max(4, round(6 * scale))
        pygame.draw.line(layer, (*color, alpha), tail, head, width)
        px, py = -step_y, step_x
        for sign in (-1, 1):
            wing = (head[0] - step_x * round(10 * scale) + px * round(11 * scale) * sign, head[1] - step_y * round(10 * scale) + py * round(11 * scale) * sign)
            pygame.draw.line(layer, (*color, alpha), head, wing, width)
        self.surface.blit(layer, layer.get_rect(center=(round(center[0]), round(center[1]))))

    def _draw_button(self, rect: pygame.Rect, label: str, primary: bool, disabled: bool = False, parchment: bool = False) -> None:
        hovered = rect.collidepoint(pygame.mouse.get_pos()) and not disabled
        if disabled: color, text_color = (70, 78, 76), (135, 141, 136)
        elif parchment and primary: color, text_color = ((151, 66, 43) if hovered else (126, 54, 38)), (248, 232, 195)
        elif parchment: color, text_color = ((193, 171, 132) if hovered else (177, 155, 119)), INK
        elif primary: color, text_color = (CINNABAR_HOVER if hovered else CINNABAR), (255, 239, 210)
        else: color, text_color = ((52, 83, 83) if hovered else (31, 57, 64)), TEXT
        pygame.draw.rect(self.surface, (5, 13, 17), rect.move(0, 4), border_radius=13)
        pygame.draw.rect(self.surface, color, rect, border_radius=13)
        pygame.draw.rect(self.surface, GOLD, rect, width=1, border_radius=13)
        self._draw_centered_in_rect(label, self.fonts["small"], text_color, rect)

    def _draw_card(self, rect: pygame.Rect, color: tuple[int, ...], radius: int, border: tuple[int, int, int] | None = None) -> None:
        layer = pygame.Surface((rect.width, rect.height + 5), pygame.SRCALPHA)
        pygame.draw.rect(layer, (3, 10, 15, 175), (0, 5, rect.width, rect.height), border_radius=radius)
        pygame.draw.rect(layer, color, (0, 0, rect.width, rect.height), border_radius=radius)
        if border is not None:
            pygame.draw.rect(layer, (*border, 165), (0, 0, rect.width, rect.height), width=1, border_radius=radius)
        self.surface.blit(layer, rect)

    def _draw_center_text(self, text: str, font: pygame.font.Font, color: tuple[int, int, int], y: int, shadow: tuple[int, int] | None = None) -> None:
        image = font.render(text, True, color)
        rect = image.get_rect(center=(WINDOW_WIDTH // 2, y))
        if shadow is not None:
            self.surface.blit(font.render(text, True, (2, 8, 11)), rect.move(*shadow))
        self.surface.blit(image, rect)

    def _draw_text(self, text: str, font: pygame.font.Font, color: tuple[int, int, int], position: tuple[int, int]) -> None:
        self.surface.blit(font.render(text, True, color), position)

    def _draw_centered_in_rect(self, text: str, font: pygame.font.Font, color: tuple[int, int, int], rect: pygame.Rect) -> None:
        image = font.render(text, True, color)
        self.surface.blit(image, image.get_rect(center=rect.center))

    @staticmethod
    def cell_center(row: int, col: int) -> tuple[int, int]:
        return BOARD_LEFT + col * CELL_SIZE + CELL_SIZE // 2, BOARD_TOP + row * CELL_SIZE + CELL_SIZE // 2

    @staticmethod
    def _start_buttons() -> dict[str, pygame.Rect]:
        return {"continue": pygame.Rect(350, 510, 300, 58), "select": pygame.Rect(350, 585, 300, 54)}

    @staticmethod
    def _level_cards() -> list[pygame.Rect]:
        return [pygame.Rect(150 + col * 370, 145 + row * 155, 330, 126) for row in range(3) for col in range(2)]

    @staticmethod
    def _select_back_button() -> pygame.Rect:
        return pygame.Rect(400, 650, 200, 48)

    @staticmethod
    def _playing_buttons() -> dict[str, pygame.Rect]:
        return {"restart": pygame.Rect(245, 704, 190, 42), "hint": pygame.Rect(455, 704, 150, 42), "home": pygame.Rect(625, 704, 130, 42)}

    @staticmethod
    def _result_buttons() -> dict[str, pygame.Rect]:
        return {"primary": pygame.Rect(335, 408, 330, 52), "secondary": pygame.Rect(335, 477, 330, 46)}
