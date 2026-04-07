"""Tests for ptools.json CLI commands and read_json helper."""
import pytest
from click.testing import CliRunner

from ptools.json import cli, read_json


class TestReadJson:
    def test_valid(self):
        assert read_json('{"a": 1}') == {"a": 1}
        assert read_json("[1, 2, 3]") == [1, 2, 3]

    def test_invalid_exits(self):
        with pytest.raises(SystemExit):
            read_json("{not json}")

    def test_empty_exits(self):
        with pytest.raises(SystemExit):
            read_json("")


class TestFormatCommand:
    def test_pretty_prints(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["format", '{"b":2,"a":1}'])
        assert result.exit_code == 0
        # Default indent=4; sort_keys=False.
        assert '"b": 2' in result.output
        assert '"a": 1' in result.output

    def test_sort_keys(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["format", "--sort-keys", '{"b":2,"a":1}'])
        assert result.exit_code == 0
        # With sort_keys, "a" must appear before "b" in the output.
        assert result.output.index('"a"') < result.output.index('"b"')

    def test_writes_to_output_file(self, tmp_path):
        out = tmp_path / "out.json"
        runner = CliRunner()
        result = runner.invoke(
            cli, ["format", '{"x":1}', "-o", str(out)]
        )
        assert result.exit_code == 0
        assert out.exists()
        assert '"x": 1' in out.read_text()

    def test_invalid_json_errors(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["format", "{not json}"])
        assert result.exit_code != 0


class TestCliGroup:
    def test_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "JSON manipulation tools" in result.output

    def test_lists_subcommands(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        for name in ("format", "to-csv", "from-js", "to-yaml"):
            assert name in result.output
