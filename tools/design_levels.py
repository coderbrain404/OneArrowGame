"""搜索方向均衡的可解关卡。"""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from levels import Level  # noqa: E402
from game_logic import is_path_clear, solve_board, remaining_arrows  # noqa: E402

DIRECTIONS = ("U", "D", "L", "R")


def random_balanced(arrow_count: int, seed: int) -> tuple[str, ...]:
    rng = random.Random(seed)
    cells = rng.sample([(r, c) for r in range(6) for c in range(6)], arrow_count)
    # 保证每个方向至少 2 个
    dirs = ["U", "D", "L", "R"]
    required = {d: 2 for d in dirs}
    chosen_dirs: list[str] = []
    for d, n in required.items():
        chosen_dirs.extend([d] * n)
    remaining = arrow_count - len(chosen_dirs)
    chosen_dirs.extend(rng.choices(DIRECTIONS, k=remaining))
    rng.shuffle(chosen_dirs)
    grid = [["."] * 6 for _ in range(6)]
    for (r, c), d in zip(cells, chosen_dirs):
        grid[r][c] = d
    return tuple("".join(row) for row in grid)


def evaluate(rows):
    L = Level("x", rows)
    b = L.create_board()
    s = solve_board(b)
    if s is None:
        return None
    movable = sum(1 for r in range(6) for c in range(6) if b[r][c] and is_path_clear(b, r, c))
    return remaining_arrows(b), movable


def search(arrow_count, target_movable, n=60000):
    found = []
    for seed in range(n):
        rows = random_balanced(arrow_count, seed)
        ev = evaluate(rows)
        if ev is None:
            continue
        arrows, movable = ev
        if target_movable[0] <= movable <= target_movable[1]:
            found.append((seed, rows, movable))
    return found


if __name__ == "__main__":
    for label, count, mv in [
        ("L4 ~12 arrows, 1-2 opening", 12, (1, 2)),
        ("L5 ~14 arrows, 2-3 opening", 14, (2, 3)),
        ("L6 ~16 arrows, 2-3 opening", 16, (2, 3)),
    ]:
        print(f"##### {label}")
        results = search(count, mv)
        seen = set()
        shown = 0
        for seed, rows, movable in results:
            if rows in seen:
                continue
            seen.add(rows)
            dirs = {}
            for r in rows:
                for ch in r:
                    if ch != ".":
                        dirs[ch] = dirs.get(ch, 0) + 1
            print(f"seed={seed} movable={movable} mix={dirs}")
            for r in rows:
                print("  " + r)
            print()
            shown += 1
            if shown >= 3:
                break
        print()
