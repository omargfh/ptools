"""Tests for ptools.utils.cases - case-style parsing and conversion."""
import pytest

from ptools.utils.parsers import (
    parse_human_time
)

class TestParseHumanTime:
    def test_parse_human_time_valid(self):
        assert parse_human_time("10s") == 10
        assert parse_human_time("5m") == 300
        assert parse_human_time("2h") == 7200
        assert parse_human_time("1d") == 86400
        assert parse_human_time("1w") == 604800
        assert parse_human_time("1mo") == 2592000
        assert parse_human_time("1y") == 31536000
        assert parse_human_time("1h30m") == 5400
        assert parse_human_time("2d3h15m") == 184500
        assert parse_human_time("1w2d3h4m5s") == 788645
        assert parse_human_time("1mo2w3d4h5m6s") == 4075506
        assert parse_human_time("1y2mo3w4d5h6m7s") == 38898367.0
        assert parse_human_time("500ms") == 0.5
        assert parse_human_time("1s500ms") == 1.5
        assert parse_human_time("2m30s500ms") == 150.5

    def test_parse_human_time_consistent(self):
        assert parse_human_time("1h30m") == parse_human_time("90m")
        assert parse_human_time("2d3h15m") == parse_human_time("51h15m")
        assert parse_human_time("1w2d3h4m5s") == parse_human_time("9d3h4m5s")

    def test_parse_human_time_floating_point(self):
        assert parse_human_time("1.5h") == 5400
        assert parse_human_time("2.5m") == 150
        assert parse_human_time("0.5d") == 43200

    def test_parse_human_time_invalid(self):
        with pytest.raises(ValueError):
            parse_human_time("invalid")
        with pytest.raises(ValueError):
            parse_human_time("10x")
        with pytest.raises(ValueError):
            parse_human_time("1h30x")
        with pytest.raises(ValueError):
            parse_human_time("1.5.5h")
