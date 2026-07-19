"""Tests for ``ptools fs watchers kill``.

``ptools fs watchers killname`` was retired in favor of
``ptools proc kill --where 'name~NAME'`` -- see
``test_watchers_killname_no_longer_exists`` below.

These exercise the kill paths entirely through mocks: ``os.kill`` inside
``ptools.lib.proc.actions`` is monkeypatched to a recording stub. No real
signal is ever sent to any process, including the pytest process itself.
"""
import signal

from click.testing import CliRunner

import ptools.fs as fs
from ptools.lib.proc import actions


def _fake_kill(calls):
    def _kill(pid, sig):
        calls.append((pid, sig))
    return _kill


def _raising_kill(exc):
    def _kill(pid, sig):
        raise exc
    return _kill


class TestWatchersKill:
    def test_success_sends_sigterm_by_default(self, monkeypatch):
        calls = []
        monkeypatch.setattr(actions.os, "kill", _fake_kill(calls))

        runner = CliRunner()
        result = runner.invoke(fs.cli, ["watchers", "kill", "12345", "--yes"])

        assert result.exit_code == 0, result.output
        assert calls == [(12345, signal.SIGTERM)]
        assert "Sent SIGTERM to PID 12345." in result.output

    def test_force_sends_sigkill(self, monkeypatch):
        calls = []
        monkeypatch.setattr(actions.os, "kill", _fake_kill(calls))

        runner = CliRunner()
        result = runner.invoke(fs.cli, ["watchers", "kill", "12345", "--force", "--yes"])

        assert result.exit_code == 0, result.output
        assert calls == [(12345, signal.SIGKILL)]
        assert "Sent SIGKILL to PID 12345." in result.output

    def test_process_lookup_error_is_reported(self, monkeypatch):
        monkeypatch.setattr(actions.os, "kill", _raising_kill(ProcessLookupError()))

        runner = CliRunner()
        result = runner.invoke(fs.cli, ["watchers", "kill", "99999", "--yes"])

        assert "not found" in result.output
        assert "99999" in result.output

    def test_permission_error_is_reported(self, monkeypatch):
        monkeypatch.setattr(actions.os, "kill", _raising_kill(PermissionError()))

        runner = CliRunner()
        result = runner.invoke(fs.cli, ["watchers", "kill", "12345", "--yes"])

        assert "Permission denied for PID 12345" in result.output
        assert "sudo" in result.output

    def test_requires_confirmation_without_yes(self, monkeypatch):
        calls = []
        monkeypatch.setattr(actions.os, "kill", _fake_kill(calls))

        runner = CliRunner()
        result = runner.invoke(fs.cli, ["watchers", "kill", "12345"])

        assert result.exit_code != 0
        assert calls == []

    def test_never_calls_os_kill_import_in_fs_module(self):
        # Regression guard: fs.py must not shell out to os.kill directly.
        import inspect
        source = inspect.getsource(fs.watchers_kill.callback)
        assert "os.kill" not in source


def test_watchers_killname_no_longer_exists():
    # Retired in favor of `ptools proc kill --where 'name~NAME'`; it must
    # not silently keep working.
    runner = CliRunner()
    result = runner.invoke(fs.cli, ["watchers", "killname", "anything"])

    assert result.exit_code != 0
    assert "No such command" in result.output
