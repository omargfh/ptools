"""Tests for FileTreeApp's stale-cache detection.

The interactive file tree renders a one-shot snapshot of the filesystem
(``_tree_data``), so it silently drifts out of date as files change on
disk. These tests cover the poller that notices that drift:

* ``_scan_tree`` records the mtime of every scanned directory.
* ``_is_cache_stale`` -- pure comparison logic -- flags adds/removes and a
  vanished directory, and stays quiet when nothing changed.
* the Textual wiring (reactive ``is_stale`` -> subtitle marker, and a
  refresh clearing it) is exercised headlessly via ``app.run_test()``,
  mirroring ``tests/lib/test_proc_app_filter_wizard.py``.
"""

from __future__ import annotations

import os
import time

import pytest

from ptools.lib.fs.file_tree_app import FileTreeApp


def _make_app(root: str, **kwargs) -> FileTreeApp:
    """Build a FileTreeApp with size lookups stubbed out (staleness is mtime-based)."""
    kwargs.setdefault("max_depth", 3)
    return FileTreeApp(
        root,
        get_size_fn=lambda p, ignore_hidden=False: 0,
        **kwargs,
    )


def _scan(app: FileTreeApp, root: str) -> dict[str, int]:
    """Run a scan the way _do_scan does, populating the mtime snapshot."""
    mtimes: dict[str, int] = {}
    app._scan_tree(root, 0, mtimes)
    app._scan_dir_mtimes = mtimes
    return mtimes


# ---------------------------------------------------------------------------
# Pure logic: _scan_tree recording + _is_cache_stale detection
# ---------------------------------------------------------------------------


def test_scan_records_mtime_for_each_scanned_directory(tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "a.txt").write_text("hi")

    app = _make_app(str(tmp_path))
    mtimes = _scan(app, str(tmp_path))

    assert str(tmp_path) in mtimes
    assert str(tmp_path / "sub") in mtimes
    # Files are not directories -> not tracked as their own mtime key.
    assert str(tmp_path / "a.txt") not in mtimes


def test_fresh_scan_is_not_stale(tmp_path):
    (tmp_path / "sub").mkdir()
    app = _make_app(str(tmp_path))
    _scan(app, str(tmp_path))

    assert app._is_cache_stale() is False


def test_added_file_is_detected(tmp_path):
    app = _make_app(str(tmp_path))
    _scan(app, str(tmp_path))
    assert app._is_cache_stale() is False

    time.sleep(0.01)  # ensure the directory mtime advances past the snapshot
    (tmp_path / "new.txt").write_text("added")

    assert app._is_cache_stale() is True


def test_removed_entry_is_detected(tmp_path):
    victim = tmp_path / "doomed.txt"
    victim.write_text("bye")

    app = _make_app(str(tmp_path))
    _scan(app, str(tmp_path))
    assert app._is_cache_stale() is False

    time.sleep(0.01)
    victim.unlink()

    assert app._is_cache_stale() is True


def test_vanished_directory_is_detected(tmp_path):
    app = _make_app(str(tmp_path))
    _scan(app, str(tmp_path))

    # A tracked directory that no longer stats -> stale.
    app._scan_dir_mtimes = {str(tmp_path / "gone"): 123}
    assert app._is_cache_stale() is True


def test_empty_snapshot_is_never_stale(tmp_path):
    """Before the first scan lands there is nothing to compare -> not stale."""
    app = _make_app(str(tmp_path))
    assert app._scan_dir_mtimes == {}
    assert app._is_cache_stale() is False


def test_deep_change_below_max_depth_is_not_tracked(tmp_path):
    """Directories whose children aren't displayed aren't watched for drift."""
    deep = tmp_path / "a" / "b" / "c" / "d"
    deep.mkdir(parents=True)

    app = _make_app(str(tmp_path), max_depth=1)
    mtimes = _scan(app, str(tmp_path))

    # max_depth=1 -> only the root's children are shown; ``a`` is rendered but
    # not expanded, so _scan_tree stops at it without recording its mtime.
    # A change buried beneath it wouldn't alter the displayed tree, so it is
    # deliberately not flagged as stale.
    assert str(tmp_path) in mtimes
    assert str(tmp_path / "a") not in mtimes

    time.sleep(0.01)
    (deep / "buried.txt").write_text("x")
    assert app._is_cache_stale() is False


# ---------------------------------------------------------------------------
# Textual wiring: reactive marker + refresh, driven headlessly
# ---------------------------------------------------------------------------


async def _wait_scanned(app: FileTreeApp, pilot) -> None:
    for _ in range(200):
        if app._mount_complete and app._scan_dir_mtimes:
            return
        await pilot.pause()
    raise AssertionError("initial scan never completed")


@pytest.mark.anyio
class TestStaleWiring:
    async def test_marker_appears_and_clears_on_refresh(self, tmp_path):
        (tmp_path / "keep.txt").write_text("x")
        app = _make_app(str(tmp_path))

        async with app.run_test() as pilot:
            await _wait_scanned(app, pilot)

            assert app.is_stale is False
            assert "STALE" not in (app.sub_title or "")

            # Simulate the poller detecting drift.
            app._mark_stale()
            await pilot.pause()
            assert app.is_stale is True
            assert "STALE" in app.sub_title

            # 'r' rescans and clears the marker.
            await pilot.press("r")
            for _ in range(200):
                if not app.is_stale:
                    break
                await pilot.pause()
            assert app.is_stale is False
            assert "STALE" not in app.sub_title

    async def test_poll_worker_flags_real_change(self, tmp_path):
        app = _make_app(str(tmp_path))

        async with app.run_test() as pilot:
            await _wait_scanned(app, pilot)
            assert app.is_stale is False

            time.sleep(0.01)
            (tmp_path / "surprise.txt").write_text("boo")

            # Drive the poll worker directly and wait for it to settle.
            app._check_stale()
            for _ in range(200):
                if app.is_stale:
                    break
                await pilot.pause()

            assert app.is_stale is True
            assert "STALE" in app.sub_title
