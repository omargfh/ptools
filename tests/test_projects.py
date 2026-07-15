"""Tests for ptools.projects, focused on the ``chdir`` interactive picker.

``Projects.PROJECT_SRC`` is computed at import time from ``~`` via
``os.path.expanduser``, and the module keeps a process-wide singleton
(``projects.projectsInstance``). Both mean we need $HOME pinned *before*
the module is (re)imported for each test, so the ``projects_module``
fixture reloads it fresh every time (mirroring ``tests/test_touch.py``'s
approach for the same kind of import-time/singleton state).
"""
from __future__ import annotations

import importlib
import json
import shutil
import subprocess

import pytest
from click.testing import CliRunner


@pytest.fixture
def projects_module(isolated_home, tmp_path):
    """Import ptools.projects with a pre-seeded projects.json under a tmp $HOME."""
    config_dir = tmp_path / ".ptools"
    config_dir.mkdir()

    demo_path = tmp_path / "demo-project"
    demo_path.mkdir()
    (demo_path / "subdir").mkdir()

    other_path = tmp_path / "other-project"
    other_path.mkdir()

    (config_dir / "projects.json").write_text(json.dumps({
        "demo": str(demo_path),
        "other": str(other_path),
    }))

    import ptools.projects as projects

    return importlib.reload(projects)


def patch_select_app(monkeypatch, module, answer):
    """Replace ``SelectApp`` with a fake that records its args and returns *answer*."""
    captured = {}

    class FakeSelectApp:
        def __init__(self, options, message="", **kwargs):
            captured["options"] = options
            captured["message"] = message

        def run(self):
            return answer

    monkeypatch.setattr(module, "SelectApp", FakeSelectApp)
    return captured


def patch_select_app_sequence(monkeypatch, module, answers):
    """Replace ``SelectApp`` with a fake that pops one canned answer per construction.

    Needed for the broken-entry remediation flow, which constructs several
    ``SelectApp``\\ s in turn within a single ``chdir`` invocation (the
    project picker, then the remediation submenu, then the re-shown
    picker...). Returns the list of ``(message, options)`` each
    construction was called with, in order, for assertions.
    """
    remaining = list(answers)
    calls = []

    class FakeSelectApp:
        def __init__(self, options, message="", **kwargs):
            calls.append((message, options))

        def run(self):
            assert remaining, "unexpected extra SelectApp invocation"
            return remaining.pop(0)

    monkeypatch.setattr(module, "SelectApp", FakeSelectApp)
    return calls


class TestChdirWithName:
    """``chdir NAME`` behavior is unchanged when a name is typed explicitly."""

    def test_prints_resolved_path(self, projects_module, tmp_path):
        runner = CliRunner()
        result = runner.invoke(projects_module.cli, ["chdir", "demo"])

        assert result.exit_code == 0
        assert result.stdout.strip() == str(tmp_path / "demo-project")

    def test_does_not_open_picker(self, projects_module, monkeypatch):
        class ExplodingSelectApp:
            def __init__(self, *args, **kwargs):
                raise AssertionError("picker should not be constructed when NAME is given")

        monkeypatch.setattr(projects_module, "SelectApp", ExplodingSelectApp)

        runner = CliRunner()
        result = runner.invoke(projects_module.cli, ["chdir", "demo"])

        assert result.exit_code == 0

    def test_subpath_handling_is_unaffected(self, projects_module, tmp_path):
        runner = CliRunner()
        result = runner.invoke(projects_module.cli, ["chdir", "demo/subdir"])

        assert result.exit_code == 0
        assert result.stdout.strip() == str(tmp_path / "demo-project" / "subdir")


class TestChdirWithoutName:
    """``chdir`` with no argument opens the interactive project picker."""

    def test_pick_resolves_to_same_output_as_typing_the_name(
        self, projects_module, tmp_path, monkeypatch
    ):
        captured = patch_select_app(monkeypatch, projects_module, "demo")

        runner = CliRunner()
        typed_result = runner.invoke(projects_module.cli, ["chdir", "demo"])
        picked_result = runner.invoke(projects_module.cli, ["chdir"])

        assert picked_result.exit_code == 0
        assert picked_result.stdout == typed_result.stdout
        assert picked_result.stdout.strip() == str(tmp_path / "demo-project")

    def test_options_use_name_as_label_and_path_as_description(
        self, projects_module, tmp_path, monkeypatch
    ):
        captured = patch_select_app(monkeypatch, projects_module, "demo")

        runner = CliRunner()
        runner.invoke(projects_module.cli, ["chdir"])

        assert captured["message"] == "Select a project:"
        assert set(captured["options"]) == {
            ("demo", "demo", str(tmp_path / "demo-project")),
            ("other", "other", str(tmp_path / "other-project")),
        }

    def test_cancelling_picker_prints_nothing_and_exits_nonzero(
        self, projects_module, monkeypatch
    ):
        patch_select_app(monkeypatch, projects_module, None)

        runner = CliRunner()
        result = runner.invoke(projects_module.cli, ["chdir"])

        assert result.exit_code != 0
        assert result.stdout == ""


class TestChdirMissingPathGuard:
    """``chdir NAME`` against a *known* project whose directory is gone.

    Distinct from an unknown name (literal-path passthrough, unaffected)
    and from the interactive-picker remediation flow (see
    ``TestChdirBrokenPickRemediation``): typing a known but broken name
    directly should fail cleanly, not crash with a raw traceback and not
    leak anything onto stdout (chdir's stdout is what the ``@cd`` shell
    function feeds straight into ``cd "$(...)"``).
    """

    def test_missing_directory_prints_clean_error_on_stderr_and_exits_nonzero(
        self, projects_module, tmp_path
    ):
        shutil.rmtree(tmp_path / "other-project")
        runner = CliRunner()

        result = runner.invoke(projects_module.cli, ["chdir", "other"])

        assert result.exit_code != 0
        assert result.stdout == ""
        assert "other" in result.stderr
        assert str(tmp_path / "other-project") in result.stderr
        assert "no longer exists" in result.stderr
        assert "prune" in result.stderr

    def test_missing_directory_does_not_raise_a_raw_exception(
        self, projects_module, tmp_path
    ):
        shutil.rmtree(tmp_path / "other-project")
        runner = CliRunner()

        result = runner.invoke(projects_module.cli, ["chdir", "other"])

        assert result.exception is None or isinstance(result.exception, SystemExit)

    def test_valid_directory_is_unaffected(self, projects_module, tmp_path):
        runner = CliRunner()

        result = runner.invoke(projects_module.cli, ["chdir", "demo"])

        assert result.exit_code == 0
        assert result.stdout.strip() == str(tmp_path / "demo-project")
        assert result.stderr == ""

    def test_unknown_name_literal_path_passthrough_is_unaffected(self, projects_module):
        """A name that isn't a configured project at all must still pass through
        unchanged (``switch()`` returns ``None`` for it) — the missing-path
        guard only applies to *known* projects, per ``switch()``'s contract.
        """
        runner = CliRunner()

        result = runner.invoke(projects_module.cli, ["chdir", "literal-project"])

        assert result.exit_code == 0
        assert result.stdout.strip() == "literal-project"


class TestChdirBrokenPickRemediation:
    """Interactive picker: selecting a broken entry offers remediation.

    Uses ``patch_select_app_sequence`` to script the *sequence* of
    ``SelectApp`` picks within one ``chdir`` invocation: the main project
    picker, then the remediation submenu, then (since ``chdir`` loops
    back to re-show the picker after cleanup) another picker pick to
    bring the run to a clean, assertable finish.
    """

    def test_broken_entry_is_marked_missing_in_the_picker(self, projects_module, tmp_path, monkeypatch):
        shutil.rmtree(tmp_path / "other-project")
        calls = patch_select_app_sequence(monkeypatch, projects_module, ["demo"])

        runner = CliRunner()
        result = runner.invoke(projects_module.cli, ["chdir"])

        assert result.exit_code == 0, (result.stdout, result.stderr)
        first_message, first_options = calls[0]
        assert first_message == "Select a project:"
        options_by_name = {value: (label, desc) for value, label, desc in first_options}
        assert options_by_name["other"][1] == f"{tmp_path / 'other-project'} (missing)"
        assert options_by_name["demo"][1] == str(tmp_path / "demo-project")

    def test_picking_delete_removes_only_that_entry(self, projects_module, tmp_path, monkeypatch):
        shutil.rmtree(tmp_path / "other-project")
        patch_select_app_sequence(
            monkeypatch, projects_module, ["other", "delete", "demo"]
        )

        runner = CliRunner()
        result = runner.invoke(projects_module.cli, ["chdir"])

        assert result.exit_code == 0, (result.stdout, result.stderr)
        # stdout stays clean: only the final resolved path for the re-picked "demo".
        assert result.stdout.strip() == str(tmp_path / "demo-project")
        # Remediation status messages land on stderr, not stdout.
        assert "no longer exists" in result.stderr
        assert "deleted" in result.stderr

        remaining = projects_module.Projects.get_instance().get_projects()
        assert "other" not in remaining
        assert "demo" in remaining

    def test_picking_prune_all_removes_every_broken_entry(
        self, projects_module, tmp_path, monkeypatch
    ):
        # A second broken project so "prune all" has more than one to remove,
        # added straight through the live singleton (same one `chdir` will use).
        broken2_dir = tmp_path / "broken2-project"
        broken2_dir.mkdir()
        projects_module.Projects.get_instance().add_project("broken2", str(broken2_dir))
        shutil.rmtree(broken2_dir)
        shutil.rmtree(tmp_path / "other-project")

        # Pick "other" (one of the two broken entries), choose "prune" (removes
        # *both* broken entries, not just the one picked), then pick "demo" on
        # the re-shown picker to bring the run to a clean finish.
        patch_select_app_sequence(monkeypatch, projects_module, ["other", "prune", "demo"])

        runner = CliRunner()
        result = runner.invoke(projects_module.cli, ["chdir"])

        assert result.exit_code == 0, (result.stdout, result.stderr)
        assert result.stdout.strip() == str(tmp_path / "demo-project")
        assert "Removed 2 project(s)" in result.stderr

        remaining = projects_module.Projects.get_instance().get_projects()
        assert "other" not in remaining
        assert "broken2" not in remaining
        assert "demo" in remaining

    def test_cancelling_remediation_leaves_everything_untouched(
        self, projects_module, tmp_path, monkeypatch
    ):
        shutil.rmtree(tmp_path / "other-project")
        patch_select_app_sequence(monkeypatch, projects_module, ["other", "cancel"])

        runner = CliRunner()
        result = runner.invoke(projects_module.cli, ["chdir"])

        assert result.exit_code != 0
        assert result.stdout == ""

        remaining = projects_module.Projects.get_instance().get_projects()
        assert "other" in remaining
        assert "demo" in remaining


class TestShellFunctionSnippet:
    """Structural checks on the generated ``@cd`` shell function source.

    These don't shell out (see ``TestShellFunctionSubprocess`` for that);
    they just assert the generated text has the right shape: renamed from
    ``pcd`` to ``@cd``, and branching on 0 / 1 / 2+ args rather than the
    old ``-ne 1`` passthrough-only-unless-exactly-one-arg logic.
    """

    def test_no_pcd_references_remain_anywhere_in_the_module(self, projects_module):
        import inspect

        source = inspect.getsource(projects_module)
        assert "pcd" not in source

    def test_function_is_named_at_cd(self, projects_module):
        assert "@cd()" in projects_module._SHELL_FUNCTION_BODY

    def test_zero_args_branch_invokes_picker_without_a_name(self, projects_module):
        body = projects_module._SHELL_FUNCTION_BODY
        assert '"$#" -eq 0' in body
        assert 'cd "$(ptools projects chdir --quiet)"' in body

    def test_one_arg_branch_passes_name_through(self, projects_module):
        body = projects_module._SHELL_FUNCTION_BODY
        assert '"$#" -eq 1' in body
        assert 'cd "$(ptools projects chdir "$1" --quiet)"' in body

    def test_multi_arg_branch_still_passes_through_unchanged(self, projects_module):
        body = projects_module._SHELL_FUNCTION_BODY
        assert "ptools projects ${*:1}" in body

    def test_snippet_embeds_current_version_marker(self, projects_module):
        snippet = projects_module._shell_function_snippet()
        assert snippet.startswith(f"# ptools-project-switcher v{projects_module.__version__}")
        assert "@cd()" in snippet


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash not available")
class TestShellFunctionSubprocess:
    """Source the generated ``@cd`` function into a real shell and drive it.

    A fake ``ptools`` stub on $PATH logs the arguments it was invoked with
    to a file (rather than relying on its stdout, which the 0/1-arg
    branches pipe straight into ``cd "$(...)"`` and would otherwise
    swallow) and echoes a real, existing directory so ``cd`` succeeds
    cleanly. This exercises the *shell-level* argument branching
    (0 / 1 / 2+ args) end to end without needing the real CLI or an
    interactive terminal.
    """

    @pytest.fixture
    def stub_ptools(self, tmp_path):
        """A fake ``ptools`` executable that logs its invocation and 'cd's cleanly."""
        bin_dir = tmp_path / "fakebin"
        bin_dir.mkdir()
        log_file = tmp_path / "invocations.log"
        stub = bin_dir / "ptools"
        stub.write_text(
            "#!/bin/sh\n"
            f'echo "$@" >> "{log_file}"\n'
            f'echo "{tmp_path}"\n'
        )
        stub.chmod(0o755)
        return str(bin_dir), log_file

    def _run(self, shell, tmp_path, stub_ptools, args):
        import ptools.projects as projects

        bin_dir, log_file = stub_ptools
        snippet_file = tmp_path / "snippet.sh"
        snippet_file.write_text(projects._SHELL_FUNCTION_BODY)

        script = f"source {snippet_file}; @cd {args}"
        env = {"PATH": f"{bin_dir}:/usr/bin:/bin"}
        result = subprocess.run(
            [shell, "-c", script],
            capture_output=True,
            text=True,
            env=env,
            timeout=10,
        )
        invocations = log_file.read_text().splitlines() if log_file.exists() else []
        return result, invocations

    def test_zero_args_calls_chdir_without_a_name(self, tmp_path, stub_ptools):
        result, invocations = self._run("bash", tmp_path, stub_ptools, "")
        assert result.returncode == 0, result.stderr
        assert invocations == ["projects chdir --quiet"]

    def test_one_arg_calls_chdir_with_the_name(self, tmp_path, stub_ptools):
        result, invocations = self._run("bash", tmp_path, stub_ptools, "demo")
        assert result.returncode == 0, result.stderr
        assert invocations == ["projects chdir demo --quiet"]

    def test_multiple_args_pass_through_unchanged(self, tmp_path, stub_ptools):
        result, invocations = self._run("bash", tmp_path, stub_ptools, "list extra")
        assert result.returncode == 0, result.stderr
        assert invocations == ["projects list extra"]

    @pytest.mark.skipif(shutil.which("zsh") is None, reason="zsh not available")
    def test_zero_args_calls_chdir_without_a_name_in_zsh(self, tmp_path, stub_ptools):
        result, invocations = self._run("zsh", tmp_path, stub_ptools, "")
        assert result.returncode == 0, result.stderr
        assert invocations == ["projects chdir --quiet"]

    @pytest.mark.skipif(shutil.which("zsh") is None, reason="zsh not available")
    def test_at_cd_is_accepted_as_a_function_name_in_zsh(self, tmp_path, stub_ptools):
        result, invocations = self._run("zsh", tmp_path, stub_ptools, "demo")
        assert result.returncode == 0, result.stderr
        assert invocations == ["projects chdir demo --quiet"]


class TestInstall:
    """Idempotent, version-marker-driven install of the ``@cd`` function."""

    def _rc_file(self, tmp_path, content=""):
        rc = tmp_path / "shellrc"
        rc.write_text(content)
        return rc

    def test_appends_fresh_when_nothing_installed(self, projects_module, tmp_path):
        rc = self._rc_file(tmp_path, "export FOO=bar\n")
        runner = CliRunner()

        result = runner.invoke(projects_module.cli, ["install", str(rc)])

        assert result.exit_code == 0
        assert "Installed @cd function" in result.output
        content = rc.read_text()
        assert "@cd()" in content
        assert f"# ptools-project-switcher v{projects_module.__version__}" in content
        assert "export FOO=bar" in content

    def test_rerunning_with_same_version_is_a_noop(self, projects_module, tmp_path):
        rc = self._rc_file(tmp_path)
        runner = CliRunner()

        runner.invoke(projects_module.cli, ["install", str(rc)])
        first_content = rc.read_text()

        result = runner.invoke(projects_module.cli, ["install", str(rc)])

        assert result.exit_code == 0
        assert "already installed" in result.output
        # File must be untouched: exactly one function block, byte-identical.
        assert rc.read_text() == first_content
        assert first_content.count("@cd()") == 1

    def test_older_version_block_is_replaced(self, projects_module, tmp_path):
        stale_block = (
            "# ptools-project-switcher v0.0.1\n"
            "@cd() {\n"
            "    echo 'stale implementation'\n"
            "}"
        )
        rc = self._rc_file(tmp_path, f"export FOO=bar\n\n{stale_block}\n\nalias ll='ls -la'\n")
        runner = CliRunner()

        result = runner.invoke(projects_module.cli, ["install", str(rc)])

        assert result.exit_code == 0
        assert "Removed outdated @cd function (v0.0.1)" in result.output
        assert "Installed @cd function" in result.output

        content = rc.read_text()
        assert content.count("@cd()") == 1
        assert "stale implementation" not in content
        assert f"v{projects_module.__version__}" in content
        # Unrelated surrounding content in the rc file must survive.
        assert "export FOO=bar" in content
        assert "alias ll='ls -la'" in content


class TestPrune:
    """``prune`` removes projects whose directory no longer exists."""

    def test_removes_projects_with_missing_directories(self, projects_module, tmp_path):
        shutil.rmtree(tmp_path / "other-project")
        runner = CliRunner()

        result = runner.invoke(projects_module.cli, ["prune"], input="y\n")

        assert result.exit_code == 0, result.output
        assert "Removed 1 project(s): other" in result.output
        remaining = projects_module.Projects.get_instance().get_projects()
        assert "other" not in remaining
        assert "demo" in remaining

    def test_lists_affected_projects_before_prompting(self, projects_module, tmp_path):
        shutil.rmtree(tmp_path / "other-project")
        runner = CliRunner()

        result = runner.invoke(projects_module.cli, ["prune"], input="y\n")

        assert "no longer exist on disk" in result.output
        assert "other" in result.output
        assert str(tmp_path / "other-project") in result.output

    def test_declining_confirmation_removes_nothing(self, projects_module, tmp_path):
        shutil.rmtree(tmp_path / "other-project")
        runner = CliRunner()

        result = runner.invoke(projects_module.cli, ["prune"], input="n\n")

        assert result.exit_code != 0
        remaining = projects_module.Projects.get_instance().get_projects()
        assert "other" in remaining
        assert "demo" in remaining

    def test_reports_nothing_to_prune_when_all_directories_exist(self, projects_module):
        runner = CliRunner()

        result = runner.invoke(projects_module.cli, ["prune"])

        assert result.exit_code == 0, result.output
        assert "No projects to prune" in result.output
        remaining = projects_module.Projects.get_instance().get_projects()
        assert set(remaining) == {"demo", "other"}
