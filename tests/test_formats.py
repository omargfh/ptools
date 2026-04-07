"""Tests for ptools.formats (click option composites for json/yaml dumps)."""
import click
from click.testing import CliRunner

from ptools.formats import json as pjson
from ptools.formats import yaml as pyaml
from ptools.utils.decorator_compistor import DecoratorCompositor


def test_json_dump_is_compositor():
    assert isinstance(pjson.dump, DecoratorCompositor)
    # Sanity check: one decorator per registered CLI option.
    assert len(pjson.dump.decorators) == 5


def test_yaml_dump_is_compositor():
    assert isinstance(pyaml.dump, DecoratorCompositor)
    assert len(pyaml.dump.decorators) >= 5


def test_json_dump_applies_options_to_click_command():
    @click.command()
    @pjson.dump.decorate()
    def cmd(indent, ensure_ascii, sort_keys, separators, allow_nan):
        click.echo(f"indent={indent} sort_keys={sort_keys}")

    runner = CliRunner()
    result = runner.invoke(cmd, ["--indent", "2", "--sort-keys"])
    assert result.exit_code == 0, result.output
    assert "indent=2 sort_keys=True" in result.output


def test_json_dump_defaults():
    @click.command()
    @pjson.dump.decorate()
    def cmd(indent, ensure_ascii, sort_keys, separators, allow_nan):
        click.echo(f"{indent},{ensure_ascii},{sort_keys},{allow_nan}")

    runner = CliRunner()
    result = runner.invoke(cmd, [])
    assert result.exit_code == 0
    # defaults: indent=4, ensure_ascii=True, sort_keys=False, allow_nan=True
    assert "4,True,False,True" in result.output
