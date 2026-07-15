"""Tests for the ``ptools shell`` command group, focused on ``completion``.

Uses the ``isolated_home`` fixture so ``Shell``'s underlying ``ConfigFile``
(which defaults to ``~/.ptools``) never touches the developer's real home
directory, and writes the "shell rc" target itself to a tmp path so
``--install`` never touches a real ``~/.zshrc``/``~/.bashrc``.
"""
from click.testing import CliRunner

import ptools.shell as shell_mod


def _set_default_shell(runner, shconfig_path):
    result = runner.invoke(shell_mod.cli, ["set-default-shell", str(shconfig_path)])
    assert result.exit_code == 0, result.output
    return result


class TestCompletionPrint:
    """``ptools shell completion --shell <shell>`` (no --install) prints a script."""

    def test_bash_prints_completion_marker(self, isolated_home):
        runner = CliRunner()
        result = runner.invoke(shell_mod.cli, ["completion", "--shell", "bash"])

        assert result.exit_code == 0, result.output
        assert "_PTOOLS_COMPLETE" in result.output
        assert "complete -o nosort -F" in result.output

    def test_zsh_prints_completion_marker(self, isolated_home):
        runner = CliRunner()
        result = runner.invoke(shell_mod.cli, ["completion", "--shell", "zsh"])

        assert result.exit_code == 0, result.output
        assert "_PTOOLS_COMPLETE" in result.output
        assert "compdef" in result.output

    def test_fish_prints_completion_marker(self, isolated_home):
        runner = CliRunner()
        result = runner.invoke(shell_mod.cli, ["completion", "--shell", "fish"])

        assert result.exit_code == 0, result.output
        assert "_PTOOLS_COMPLETE" in result.output

    def test_invalid_shell_rejected(self, isolated_home):
        runner = CliRunner()
        result = runner.invoke(shell_mod.cli, ["completion", "--shell", "powershell"])

        assert result.exit_code != 0

    def test_missing_shell_option_required(self, isolated_home):
        runner = CliRunner()
        result = runner.invoke(shell_mod.cli, ["completion"])

        assert result.exit_code != 0


class TestCompletionInstall:
    """``ptools shell completion --shell <shell> --install`` appends a managed line."""

    def test_install_appends_one_block(self, isolated_home, tmp_cwd):
        shconfig = tmp_cwd / "shellrc"
        shconfig.write_text("# existing content\n")

        runner = CliRunner()
        _set_default_shell(runner, shconfig)

        result = runner.invoke(shell_mod.cli, ["completion", "--shell", "bash", "--install"])
        assert result.exit_code == 0, result.output

        content = shconfig.read_text()
        assert content.count("_PTOOLS_COMPLETE=bash_source") == 1
        assert 'eval "$(_PTOOLS_COMPLETE=bash_source ptools)"' in content
        # Original content is preserved, not clobbered.
        assert "# existing content" in content

    def test_install_twice_is_idempotent(self, isolated_home, tmp_cwd):
        shconfig = tmp_cwd / "shellrc"
        shconfig.write_text("")

        runner = CliRunner()
        _set_default_shell(runner, shconfig)

        first = runner.invoke(shell_mod.cli, ["completion", "--shell", "zsh", "--install"])
        second = runner.invoke(shell_mod.cli, ["completion", "--shell", "zsh", "--install"])

        assert first.exit_code == 0, first.output
        assert second.exit_code == 0, second.output
        assert "already installed" in second.output

        content = shconfig.read_text()
        assert content.count("_PTOOLS_COMPLETE=zsh_source") == 1

    def test_install_different_shells_each_get_a_line(self, isolated_home, tmp_cwd):
        shconfig = tmp_cwd / "shellrc"
        shconfig.write_text("")

        runner = CliRunner()
        _set_default_shell(runner, shconfig)

        runner.invoke(shell_mod.cli, ["completion", "--shell", "bash", "--install"])
        runner.invoke(shell_mod.cli, ["completion", "--shell", "zsh", "--install"])

        content = shconfig.read_text()
        assert content.count("_PTOOLS_COMPLETE=bash_source") == 1
        assert content.count("_PTOOLS_COMPLETE=zsh_source") == 1
