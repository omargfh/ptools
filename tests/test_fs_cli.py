"""Tests for ``ptools fs watchers kill``/``killname``.

These exercise the kill paths entirely through mocks: ``os.kill`` inside
``ptools.lib.proc.actions`` is monkeypatched to a recording stub, and
``_get_watcher_data`` is replaced with fixed fake process rows. No real
signal is ever sent to any process, including the pytest process itself.
"""
import os
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


class TestWatchersKillname:
    def _fake_watcher_data(self):
        # One entry deliberately shares the PID of the running test process
        # to exercise the self-PID exclusion; the other is a distinct,
        # non-existent PID that is never actually signalled (os.kill is
        # mocked below).
        return [
            {
                "pid": os.getpid(),
                "command": "ptools",
                "exec_path": "/usr/bin/ptools",
                "label": "",
                "fds": 5,
                "kqueues": 0,
            },
            {
                "pid": 424242,
                "command": "ptools-helper",
                "exec_path": "/usr/bin/ptools-helper",
                "label": "",
                "fds": 3,
                "kqueues": 1,
            },
        ]

    def test_dry_run_excludes_current_pid(self, monkeypatch):
        monkeypatch.setattr(fs, "_get_watcher_data", self._fake_watcher_data)

        runner = CliRunner()
        result = runner.invoke(fs.cli, ["watchers", "killname", "ptools", "--dry-run"])

        assert result.exit_code == 0, result.output
        assert str(os.getpid()) not in result.output
        assert "424242" in result.output

    def test_dry_run_output_format_unchanged(self, monkeypatch):
        monkeypatch.setattr(fs, "_get_watcher_data", self._fake_watcher_data)

        runner = CliRunner()
        result = runner.invoke(fs.cli, ["watchers", "killname", "ptools", "--dry-run"])

        assert (
            '[dry-run] Would kill PID 424242 (ptools-helper) (3 fds)' in result.output
        )

    def test_dry_run_bypasses_confirmation(self, monkeypatch):
        monkeypatch.setattr(fs, "_get_watcher_data", self._fake_watcher_data)

        runner = CliRunner()
        # No --yes and no stdin input: if a confirmation prompt were hit,
        # this would abort (or hang waiting for input).
        result = runner.invoke(fs.cli, ["watchers", "killname", "ptools", "--dry-run"])

        assert result.exit_code == 0, result.output

    def test_never_signals_current_pid_without_dry_run(self, monkeypatch):
        calls = []
        monkeypatch.setattr(actions.os, "kill", _fake_kill(calls))
        monkeypatch.setattr(fs, "_get_watcher_data", self._fake_watcher_data)

        runner = CliRunner()
        result = runner.invoke(fs.cli, ["watchers", "killname", "ptools", "--yes"])

        assert result.exit_code == 0, result.output
        assert all(pid != os.getpid() for pid, _sig in calls)
        assert calls == [(424242, signal.SIGTERM)]

    def test_prompts_for_confirmation_without_yes(self, monkeypatch):
        calls = []
        monkeypatch.setattr(actions.os, "kill", _fake_kill(calls))
        monkeypatch.setattr(fs, "_get_watcher_data", self._fake_watcher_data)

        runner = CliRunner()
        result = runner.invoke(fs.cli, ["watchers", "killname", "ptools"])

        assert result.exit_code != 0
        assert calls == []

    def test_yes_flag_skips_prompt(self, monkeypatch):
        calls = []
        monkeypatch.setattr(actions.os, "kill", _fake_kill(calls))
        monkeypatch.setattr(fs, "_get_watcher_data", self._fake_watcher_data)

        runner = CliRunner()
        result = runner.invoke(fs.cli, ["watchers", "killname", "ptools", "--yes"])

        assert result.exit_code == 0, result.output
        assert calls == [(424242, signal.SIGTERM)]

    def test_only_self_matching_kills_nothing(self, monkeypatch):
        calls = []
        monkeypatch.setattr(actions.os, "kill", _fake_kill(calls))
        monkeypatch.setattr(
            fs,
            "_get_watcher_data",
            lambda: [
                {
                    "pid": os.getpid(),
                    "command": "only-self",
                    "exec_path": "/usr/bin/only-self",
                    "label": "",
                    "fds": 1,
                    "kqueues": 0,
                }
            ],
        )

        runner = CliRunner()
        result = runner.invoke(fs.cli, ["watchers", "killname", "only-self", "--yes"])

        assert result.exit_code == 0, result.output
        assert calls == []
        assert "No processes matching" in result.output

    def test_never_calls_os_kill_import_in_fs_module(self):
        import inspect
        source = inspect.getsource(fs.watchers_killname.callback)
        assert "os.kill" not in source
