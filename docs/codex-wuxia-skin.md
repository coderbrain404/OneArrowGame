# Codex 任务：武侠风皮肤集成（v2.1）

> 把这份文档和 `assets/wuxia/` 目录一起交给 Codex。
> 目标：把现有"一箭又一箭"的界面从平涂渐变改为水墨武侠风，**不改游戏逻辑、不改关卡、不改测试**。
> 前置：建议先完成 `codex-v2-plan.md` 里的 v2.0 功能，再叠加本皮肤；也可以独立做。

## 0. 美术资源清单

所有资源已生成在 `assets/wuxia/`：

| 文件 | 用途 | 原始尺寸 | 说明 |
| --- | --- | --- | --- |
| `assets/wuxia/bg.png` | 全屏背景 | 1347×1024 | 水墨月夜、竹林、远山；中心水面留白给棋盘 |
| `assets/wuxia/board.png` | 棋盘底纹 | 1024×1024 | 黑檀木 + 四角云纹雕花；**内框约占整张图 72%** |
| `assets/wuxia/title.png` | 开始页标题 | 2389×1024 | "一箭又一箭"书法字（注意：实际是 JPEG 编码，pygame 能读） |
| `assets/wuxia/scroll.png` | 结算浮层面板 | 1536×1024 | 泛黄宣纸卷轴，四角水墨山水；**中心留白放文字** |

> 这些图不要修改、不要裁切。缩放和对齐在代码里做。

## 1. 硬约束

- **只改 `ui.py`**。`game_logic.py` / `levels.py` / `tests/` 一律不动。
- 游戏窗口尺寸保持 `1000×760`，棋盘位置保持 `BOARD_LEFT=278, BOARD_TOP=186, CELL_SIZE=74`。
- 现有 16 个测试必须继续通过（测试不渲染画面，所以改渲染层不影响）。
- 不引入新依赖；`pygame.image.load` 即可。
- 所有资源路径用 `Path(__file__).parent / "assets" / "wuxia" / "xxx.png"`，**不要写死绝对路径**。

## 2. 具体改动

### 2.1 在 `ArrowGame.__init__` 末尾加载资源

在现有 `self.notice = ""` 之后追加：

```python
from pathlib import Path
ASSETS = Path(__file__).parent / "assets" / "wuxia"

self.bg_img = pygame.image.load(ASSETS / "bg.png").convert()
self.bg_img = pygame.transform.smoothscale(
    self.bg_img, (WINDOW_WIDTH, WINDOW_HEIGHT))

self.board_img = pygame.image.load(ASSETS / "board.png").convert()
# 木纹图内框约占 72%，放大到 620×620 让内框刚好填满 444×444
self.board_img = pygame.transform.smoothscale(self.board_img, (620, 620))

self.title_img = pygame.image.load(ASSETS / "title.png").convert_alpha()
self.title_img = pygame.transform.smoothscale(self.title_img, (560, 140))

self.scroll_img = pygame.image.load(ASSETS / "scroll.png").convert_alpha()
self.scroll_img = pygame.transform.smoothscale(self.scroll_img, (520, 380))
```

> `convert()` 在 display set_mode 之后调用；如果加载报错，把 `convert()` 去掉（`convert_alpha()` 对带透明通道的图是必须的）。

### 2.2 背景：替换 `_draw_background`

把当前逐行画渐变 + 画三个圆圈的实现**整个替换**为：

```python
def _draw_background(self) -> None:
    self.surface.blit(self.bg_img, (0, 0))
```

如果叠完图后 HUD/按钮文字可读性变差，在这一行后面追加一层极淡的暗角：

```python
    veil = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
    veil.fill((8, 12, 24, 60))
    self.surface.blit(veil, (0, 0))
```

### 2.3 棋盘底纹：修改 `_draw_board` 开头

当前代码先画一个深色 shadow 圆角矩形，再画 `CARD_LIGHT` 棋盘底。把这两行 `_draw_card(...)` 调用替换为：

```python
# 木纹图 620×620，内框约 444×444，居中对齐到 BOARD_LEFT/BOARD_TOP
offset = (620 - BOARD_PIXEL_SIZE) // 2
self.surface.blit(
    self.board_img,
    (BOARD_LEFT - offset, BOARD_TOP - offset),
)
```

原来的 `shadow` 投影和 `CARD_LIGHT` 卡片**删掉**，不要叠。

网格线（`pygame.draw.rect` 画 cell 那层）和箭头绘制保持不动。

### 2.4 开始页标题：修改 `_draw_start_scene`

把这一行：

```python
self._draw_center_text("一箭又一箭", self.fonts["hero"], TEXT, 150)
```

替换为：

```python
self.surface.blit(
    self.title_img,
    self.title_img.get_rect(center=(WINDOW_WIDTH // 2, 150)),
)
```

下面那行副标题"观察方向 · 找到出口 · 依次清空"保留，位置可下移到 `y=250`（因为书法标题比原文字高）。

开始页那四个方向示例箭头（`_draw_arrow` 循环）保留，它们在水墨背景上仍然清晰。

### 2.5 结算浮层：修改 `_draw_result_overlay`

这是改动最大的一块。原来的深色卡片 + 浅色文字要换成卷轴 + **深色文字**。

**面板替换**：把

```python
panel = pygame.Rect(255, 195, 490, 365)
self._draw_card(panel, (31, 50, 81), radius=28)
pygame.draw.rect(self.surface, (77, 104, 139), panel, width=1, border_radius=28)
```

替换为：

```python
panel = pygame.Rect(240, 190, 520, 380)
self.surface.blit(
    self.scroll_img,
    self.scroll_img.get_rect(center=panel.center),
)
```

**文字颜色**：卷轴是暖米黄底，原来的浅色文字会看不清。在 `_draw_result_overlay` 里把标题、副标题、"剩余机会"等文字的颜色统一改为深墨色：

```python
INK = (45, 30, 18)       # 标题
INK_MUTED = (90, 65, 40) # 副标题
```

- `title` 颜色：成功用 `(120, 40, 30)`（朱砂红），失败用 `(150, 50, 40)`，全部通关用 `(180, 120, 30)`（金）。
- `subtitle` 和"剩余机会"用 `INK_MUTED`。
- 原来的 `TEXT` / `ACCENT` 等浅色不要直接用在卷轴上。

**按钮**：原来两个按钮（primary / secondary）继续用 `_draw_button`，但需要临时换色。最简单做法：给 `_draw_button` 加一个 `dark: bool = False` 参数，当在卷轴上调用时传 `dark=True`：

```python
def _draw_button(self, rect, label, primary, dark=False):
    # ... hover 逻辑不变
    if dark:
        if primary:
            color = (120, 60, 35)      # 深棕红
            text_color = (245, 230, 200)
        else:
            color = (180, 160, 130)     # 浅褐
            text_color = (45, 30, 18)
    else:
        # 原有青色/深灰逻辑
        ...
```

在 `_draw_result_overlay` 里调用时传 `dark=True`。

### 2.6 HUD 和游戏内按钮

HUD 卡片（顶部那栏）、"重新开始/返回首页"按钮、棋盘上的箭头——**全部保持原样**。它们在水墨背景上对比度足够，不要动颜色。

### 2.7 文案武侠化

在 `ui.py` 里做以下字符串替换（搜原文即可）：

| 位置 | 原文 | 改为 |
| --- | --- | --- |
| `_draw_start_scene` 说明卡 | "被阻挡会消耗机会，每共有 3 次机会" | "遇阻则耗气力，每关 3 点"（顺带修掉错字） |
| `_click_board` CLEARED | `"路径畅通！"` | `"破空而出"` |
| `_click_board` BLOCKED | `"前方有阻挡，机会 -1"` | `"被格挡！气力 -1"` |
| `_click_board` EMPTY | `"请点击箭头"` | `"请点箭矢"` |
| `_draw_result_overlay` level_clear | `"本关完成！"` | `"破关成功！"` |
| `_draw_result_overlay` game_over | `"挑战失败"` | `"力竭而止"` |
| `_draw_result_overlay` game_over subtitle | `"失误机会已用尽，再观察一下阻挡关系"` | `"气力耗尽，再察箭路"` |
| `_draw_result_overlay` all_clear | `"全部通关！"` | `"江湖尽破！"` |
| `_draw_game_scene` 按钮 | `"重新开始  R"` | `"重开本关  R"` |
| HUD stat 标签 | `"剩余机会"` | `"气力"` |
| HUD stat 标签 | `"剩余箭头"` | `"余箭"` |

> 关卡名（`levels.py` 里的"第 1 关 · 认识方向"等）**不要改**，那是数据层，留给 v2.0 或后续版本统一处理。

## 3. 验收标准

- [ ] `py -3.13 main.py` 启动后，背景是水墨月夜，不再是蓝色渐变。
- [ ] 开始页标题是书法字"一箭又一箭"，不再是默认字体渲染。
- [ ] 棋盘区域是黑檀木云纹底，四角雕花可见，网格线和箭头仍清晰。
- [ ] 通关/失败/全部通关浮层是宣纸卷轴，文字是深墨色（不是白色），按钮是棕褐色系。
- [ ] 开始页、游戏页、结算页之间切换无卡顿、无图裂、无黑边。
- [ ] `py -3.13 -m pytest` 全部通过（应仍是 16 个）。
- [ ] 打包 exe 后图片能正常加载（见 §4）。

## 4. 打包注意事项

修改 `OneArrowGame.spec`，把 `assets/wuxia/` 加入 datas：

```python
datas = [("assets/wuxia", "assets/wuxia")],
```

确保用的是相对路径，并且 `pyinstaller` 运行目录是项目根目录（`C:\Users\HS\Documents\ChatGPT\软工`）。

打包后在 `dist/` 里双击 exe，图片路径用 `Path(__file__).parent / "assets" / "wuxia"` 能正确解析（PyInstaller onefile 模式下 `__file__` 指向解压目录，datas 会解到那里）。

## 5. 工作顺序建议

1. 先在 `__init__` 加资源加载，跑一次确认不报错。
2. 改 `_draw_background`，看开始页效果。
3. 改 `_draw_start_scene` 标题。
4. 改 `_draw_board` 底纹。
5. 改 `_draw_result_overlay`（这一步最复杂，先换面板图，再调文字色，最后调按钮色）。
6. 批量替换文案。
7. 跑 pytest，手动过一遍开始→游戏→结算流程。
8. 改 `.spec`，打包验证。

## 6. 如果出问题

- **图片加载报错 FileNotFoundError**：确认工作目录是项目根目录运行 `python main.py`；或者把 `ASSETS` 路径改成基于 `__file__` 的绝对路径（§2.1 已写）。
- **文字在卷轴上看不清**：确认 `_draw_button` 传了 `dark=True`，且结算页文字颜色改成了 `INK` / `INK_MUTED`，没有残留白色 `TEXT`。
- **棋盘云纹把格子遮住了**：说明 `board_img` 缩放尺寸不对；把 `620` 调成 `600` 或 `640` 微调，目标是四角雕花刚好在格子外、不压格子。
- **图变形/模糊**：确认用了 `pygame.transform.smoothscale` 而不是 `scale`。
