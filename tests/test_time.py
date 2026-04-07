"""Tests for ptools.time - formatting helper and CLI sanity."""
from click.testing import CliRunner

from ptools.time import STAT_CHOICES, cli, fmt_time


class TestFmtTime:
    def test_sub_second_is_milliseconds(self):
        assert fmt_time(0.001) == "1.000 ms"
        assert fmt_time(0.12345) == "123.450 ms"

    def test_exactly_one_second_is_seconds(self):
        assert fmt_time(1.0) == "1.000 seconds"

    def test_multi_second(self):
        assert fmt_time(2.5) == "2.500 seconds"

    def test_zero(self):
        assert fmt_time(0) == "0.000 ms"


def test_stat_choices_are_expected():
    assert set(STAT_CHOICES) == {"each", "mean", "mode", "median", "stddev", "min", "max"}


def test_cli_help_runs():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Timing utilities" in result.output
