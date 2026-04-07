"""Tests for the top-level ptools CLI entrypoint and LazyGroup loader."""
import click
from click.testing import CliRunner

from ptools.main import COMMANDS, LazyGroup, cli


def test_cli_help_runs():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "power tools command line interface" in result.output


def test_cli_help_lists_all_registered_commands():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    for name in COMMANDS:
        assert name in result.output


def test_unknown_command_returns_error():
    runner = CliRunner()
    result = runner.invoke(cli, ["definitely-not-a-command"])
    assert result.exit_code != 0


def test_lazy_group_list_commands_is_sorted():
    group = LazyGroup(name="x")
    names = group.list_commands(click.Context(group))
    assert names == sorted(COMMANDS)


def test_lazy_group_returns_none_for_unknown():
    group = LazyGroup(name="x")
    assert group.get_command(click.Context(group), "nope") is None
