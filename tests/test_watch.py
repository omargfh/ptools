"""Tests for ``ptools watch``.

watchdog's ``Observer`` (real OS file events) is replaced by a stub that
hands the registered handler to the test, which feeds it synthetic
events. ``watch.time`` is swapped so the keep-alive loop exits on its
first sleep. The watched command itself always runs as a real subprocess.
"""
import shlex
import signal
import sys
import threading
import time
from types import SimpleNamespace

import pytest
from click.testing import CliRunner
from watchdog.events import FileModifiedEvent

import ptools.watch as watch

WAIT_TIMEOUT = 10

INFO_LINES = ("Watching", "Will run:", "Change detected:", "Running command:")

_WRITE_MARKER = "import pathlib, sys; pathlib.Path(sys.argv[1]).write_text('ran')"

_BLOCK_FIRST_RUN = """
import pathlib, sys, time
started, release, finished = map(pathlib.Path, sys.argv[1:4])
if started.exists():
    sys.exit(0)
started.write_text('')
deadline = time.monotonic() + 60
while not release.exists() and time.monotonic() < deadline:
    time.sleep(0.01)
if release.exists():
    finished.write_text('')
"""


class _ScriptedObserver:
    def __init__(self, script):
        self.script = script

    def schedule(self, handler, path, recursive):
        self.handler = handler

    def start(self):
        self.script(self.handler)

    def stop(self):
        pass

    def join(self):
        pass


def _interrupt(_seconds):
    raise KeyboardInterrupt


def _run_watch(monkeypatch, args, script):
    monkeypatch.setattr(watch, "Observer", lambda: _ScriptedObserver(script))
    monkeypatch.setattr(watch, "time", SimpleNamespace(sleep=_interrupt))
    result = CliRunner().invoke(watch.cli, ["--delay", "0", *args], catch_exceptions=False)
    assert result.exit_code == 0, result.output
    return result


def _change(handler):
    handler.on_any_event(FileModifiedEvent("changed.txt"))
    return handler.timer


def _join(timer):
    timer.join(WAIT_TIMEOUT)
    assert not timer.is_alive()


def _change_and_wait(handler):
    _join(_change(handler))


def _wait_until(predicate):
    deadline = time.monotonic() + WAIT_TIMEOUT
    tick = threading.Event()
    while not predicate():
        assert time.monotonic() < deadline
        tick.wait(0.01)


def _marker_command(marker):
    return ["--no-shell", "--", sys.executable, "-c", _WRITE_MARKER, str(marker)]


@pytest.fixture
def blocking(tmp_path):
    """A command whose first run blocks until ``release`` exists; later runs exit at once."""
    files = SimpleNamespace(
        started=tmp_path / "started",
        release=tmp_path / "release",
        finished=tmp_path / "finished",
    )
    files.command = [
        "--no-shell", "--", sys.executable, "-c", _BLOCK_FIRST_RUN,
        str(files.started), str(files.release), str(files.finished),
    ]
    yield files
    files.release.write_text("")


class TestQuiet:
    def test_default_prints_info_lines(self, monkeypatch, tmp_path):
        # Catches: the quiet gate inverted or applied unconditionally.
        result = _run_watch(monkeypatch, _marker_command(tmp_path / "marker"), _change_and_wait)

        for line in INFO_LINES:
            assert line in result.output

    def test_quiet_suppresses_info_lines_and_still_runs_command(self, monkeypatch, tmp_path):
        # Catches: an info line left ungated, or -q skipping the command itself.
        marker = tmp_path / "marker"

        result = _run_watch(monkeypatch, ["-q", *_marker_command(marker)], _change_and_wait)

        for line in INFO_LINES:
            assert line not in result.output
        assert marker.read_text() == "ran"


class TestShell:
    def test_default_runs_command_through_a_shell(self, monkeypatch, tmp_path):
        # Catches: the default flipping to no-shell, which cannot interpret a redirect.
        marker = tmp_path / "marker"

        _run_watch(monkeypatch, [f"echo ran > {shlex.quote(str(marker))}"], _change_and_wait)

        assert marker.read_text().strip() == "ran"

    def test_no_shell_passes_arguments_to_the_command(self, monkeypatch, tmp_path):
        # Catches: --no-shell not reaching Popen; under shell=True a list drops every argument after the first.
        marker = tmp_path / "marker"

        _run_watch(monkeypatch, _marker_command(marker), _change_and_wait)

        assert marker.read_text() == "ran"


class TestKillOnChange:
    def test_kill_on_change_kills_the_running_command(self, monkeypatch, blocking):
        # Catches: -K not wired up, or the handler losing track of the running process.
        seen = {}

        def script(handler):
            first_run = _change(handler)
            _wait_until(lambda: blocking.started.exists() and handler.process is not None)
            seen["process"] = handler.process
            _change_and_wait(handler)
            _join(first_run)

        _run_watch(monkeypatch, ["-K", *blocking.command], script)

        assert seen["process"].returncode == -signal.SIGKILL
        assert not blocking.finished.exists()

    def test_running_command_survives_a_change_without_the_flag(self, monkeypatch, blocking):
        # Catches: the kill happening regardless of -K.
        def script(handler):
            first_run = _change(handler)
            _wait_until(blocking.started.exists)
            _change_and_wait(handler)
            blocking.release.write_text("")
            _join(first_run)

        _run_watch(monkeypatch, blocking.command, script)

        assert blocking.finished.exists()
