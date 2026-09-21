"""关卡解锁存档测试。"""

from __future__ import annotations

from save_manager import Progress, load_progress, save_progress


def test_progress_round_trip(tmp_path) -> None:
    path = tmp_path / "save.json"
    progress = Progress(unlocked_level=3, completed_levels={0, 1, 2})

    assert save_progress(progress, path)

    loaded = load_progress(path, level_count=6)
    assert loaded.unlocked_level == 3
    assert loaded.completed_levels == {0, 1, 2}


def test_corrupt_save_falls_back_to_default(tmp_path) -> None:
    path = tmp_path / "save.json"
    path.write_text("{broken", encoding="utf-8")

    assert load_progress(path, level_count=6) == Progress()

    path.write_text("[]", encoding="utf-8")
    assert load_progress(path, level_count=6) == Progress()


def test_completion_unlocks_next_level_but_never_exceeds_last() -> None:
    progress = Progress()

    progress.mark_completed(0, 6)
    assert progress.unlocked_level == 1
    assert progress.completed_levels == {0}

    progress.mark_completed(5, 6)
    assert progress.unlocked_level == 5
    assert progress.completed_levels == {0, 5}
