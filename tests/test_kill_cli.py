"""Tests for ``ptools kill port``/``ptools kill process``.

Every path that could send a real signal is exercised through mocks:
``subprocess.run`` (the ``lsof``/``pgrep`` lookups) and
``ptools.lib.proc.actions.os.kill`` (the actual signal) are both
monkeypatched to recording stubs. No real process is ever touched,
including the pytest process itself.
"""
import os
import signal

from click.testing import CliRunner

import ptools.kill as kill
from ptools.lib.proc import actions


class _FakeCompleted:
    def __init__(self, stdout):
        self.stdout = stdout


def _fake_kill(calls):
    def _kill(pid, sig):
        calls.append((pid, sig))
    return _kill


def _raising_kill(exc):
    def _kill(pid, sig):
        raise exc
    return _kill


class TestKillPort:
    def test_dry_run_lists_each_pid_individually(self, monkeypatch):
        monkeypatch.setattr(
            kill.subprocess, "run", lambda *a, **k: _FakeCompleted("111\n222\n")
        )

        runner = CliRunner()
        result = runner.invoke(kill.cli, ["port", "3000", "--dry-run"])

        assert result.exit_code == 0, result.output
        assert "[dry-run] Would send SIGTERM to PID 111 (port 3000)." in result.output
        assert "[dry-run] Would send SIGTERM to PID 222 (port 3000)." in result.output

    def test_dry_run_force_shows_sigkill(self, monkeypatch):
        monkeypatch.setattr(
            kill.subprocess, "run", lambda *a, **k: _FakeCompleted("111\n")
        )

        runner = CliRunner()
        result = runner.invoke(kill.cli, ["port", "3000", "--dry-run", "--force"])

        assert result.exit_code == 0, result.output
        assert "Would send SIGKILL to PID 111" in result.output

    def test_dry_run_no_listener(self, monkeypatch):
        monkeypatch.setattr(kill.subprocess, "run", lambda *a, **k: _FakeCompleted(""))

        runner = CliRunner()
        result = runner.invoke(kill.cli, ["port", "9", "--dry-run"])

        assert result.exit_code == 0, result.output
        assert "No process is listening on port 9." in result.output

    def test_real_kill_sends_sigterm_by_default(self, monkeypatch):
        calls = []
        monkeypatch.setattr(actions.os, "kill", _fake_kill(calls))
        monkeypatch.setattr(
            actions.subprocess, "run", lambda *a, **k: _FakeCompleted("111\n")
        )

        runner = CliRunner()
        result = runner.invoke(kill.cli, ["port", "3000"])

        assert result.exit_code == 0, result.output
        assert calls == [(111, signal.SIGTERM)]
        assert "Sent SIGTERM to PID 111." in result.output

    def test_real_kill_force_sends_sigkill(self, monkeypatch):
        calls = []
        monkeypatch.setattr(actions.os, "kill", _fake_kill(calls))
        monkeypatch.setattr(
            actions.subprocess, "run", lambda *a, **k: _FakeCompleted("111\n")
        )

        runner = CliRunner()
        result = runner.invoke(kill.cli, ["port", "3000", "--force"])

        assert result.exit_code == 0, result.output
        assert calls == [(111, signal.SIGKILL)]
        assert "Sent SIGKILL to PID 111." in result.output

    def test_unused_port_fails_and_exits_nonzero(self, monkeypatch):
        monkeypatch.setattr(actions.subprocess, "run", lambda *a, **k: _FakeCompleted(""))

        runner = CliRunner()
        result = runner.invoke(kill.cli, ["port", "9"])

        assert result.exit_code != 0
        assert "No process is listening on port 9." in result.output

    def test_never_shells_out_to_kill(self):
        source = open(kill.__file__).read()
        assert '"kill",' not in source
        assert "'kill'," not in source


class TestKillProcess:
    def test_dry_run_lists_each_pid_individually(self, monkeypatch):
        monkeypatch.setattr(
            kill.subprocess, "run", lambda *a, **k: _FakeCompleted("111\n222\n")
        )

        runner = CliRunner()
        result = runner.invoke(kill.cli, ["process", "somename", "--dry-run"])

        assert result.exit_code == 0, result.output
        assert "[dry-run] Would send SIGTERM to PID 111 (somename)." in result.output
        assert "[dry-run] Would send SIGTERM to PID 222 (somename)." in result.output

    def test_excludes_own_pid(self, monkeypatch):
        own = os.getpid()
        monkeypatch.setattr(
            kill.subprocess, "run", lambda *a, **k: _FakeCompleted(f"{own}\n333\n")
        )

        runner = CliRunner()
        result = runner.invoke(kill.cli, ["process", "somename", "--dry-run"])

        assert result.exit_code == 0, result.output
        assert str(own) not in result.output
        assert "333" in result.output

    def test_never_signals_own_pid_on_real_kill(self, monkeypatch):
        own = os.getpid()
        calls = []
        monkeypatch.setattr(actions.os, "kill", _fake_kill(calls))
        monkeypatch.setattr(
            kill.subprocess, "run", lambda *a, **k: _FakeCompleted(f"{own}\n333\n")
        )

        runner = CliRunner()
        result = runner.invoke(kill.cli, ["process", "somename"])

        assert result.exit_code == 0, result.output
        assert all(pid != own for pid, _sig in calls)
        assert calls == [(333, signal.SIGTERM)]

    def test_no_match_reports_and_exits_nonzero(self, monkeypatch):
        monkeypatch.setattr(kill.subprocess, "run", lambda *a, **k: _FakeCompleted(""))

        runner = CliRunner()
        result = runner.invoke(kill.cli, ["process", "definitely-not-running"])

        assert result.exit_code != 0
        assert "No process found with name 'definitely-not-running'." in result.output

    def test_no_match_dry_run_still_exits_zero(self, monkeypatch):
        monkeypatch.setattr(kill.subprocess, "run", lambda *a, **k: _FakeCompleted(""))

        runner = CliRunner()
        result = runner.invoke(kill.cli, ["process", "definitely-not-running", "--dry-run"])

        assert result.exit_code == 0, result.output

    def test_permission_error_surfaces_and_exits_nonzero(self, monkeypatch):
        monkeypatch.setattr(actions.os, "kill", _raising_kill(PermissionError()))
        monkeypatch.setattr(
            kill.subprocess, "run", lambda *a, **k: _FakeCompleted("111\n")
        )

        runner = CliRunner()
        result = runner.invoke(kill.cli, ["process", "somename"])

        assert result.exit_code != 0
        assert "Permission denied for PID 111" in result.output

    def test_never_shells_out_to_kill(self):
        source = open(kill.__file__).read()
        assert '"kill",' not in source
        assert "'kill'," not in source
