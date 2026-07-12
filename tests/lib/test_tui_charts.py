"""Tests for the shared terminal chart primitives."""

from ptools.lib.tui.charts import GAUGE_PARTIALS, SPARK_BLOCKS, gauge, meter, pct_color, sparkline


def test_sparkline_empty():
    assert sparkline([]) == ""
    assert sparkline([], width=5) == "     "


def test_sparkline_scales_to_max():
    line = sparkline([0, 50, 100])
    assert len(line) == 3
    assert line[0] == SPARK_BLOCKS[0]
    assert line[-1] == SPARK_BLOCKS[-1]


def test_sparkline_explicit_max_and_clamping():
    line = sparkline([0, 100, 200], v_max=100)
    assert line[1] == SPARK_BLOCKS[-1]  # 100/100 is full height
    assert line[2] == SPARK_BLOCKS[-1]  # values above v_max clamp


def test_sparkline_width_pads_left_and_truncates_to_last_values():
    assert sparkline([100], width=4) == "   " + SPARK_BLOCKS[-1]
    line = sparkline([0, 0, 0, 100, 100], width=2)
    assert line == SPARK_BLOCKS[-1] * 2  # only the last two samples shown


def test_sparkline_constant_values():
    assert sparkline([0, 0]) == SPARK_BLOCKS[0] * 2       # all-zero stays at the floor
    assert sparkline([5, 5]) == SPARK_BLOCKS[-1] * 2      # constant nonzero maxes out
    assert sparkline([None, 100]) [0] == SPARK_BLOCKS[0]  # None treated as 0


def test_gauge_bounds_and_width():
    assert gauge(0, 4) == "    "
    assert gauge(1, 4) == "████"
    assert gauge(2.0, 4) == "████"   # clamps above 1
    assert gauge(-1.0, 4) == "    "  # clamps below 0
    assert len(gauge(0.371, 13)) == 13


def test_gauge_partial_blocks():
    assert gauge(0.5, 10) == "█████     "
    assert gauge(0.5625, 2) == "█" + GAUGE_PARTIALS[1]  # 1.125 cells -> full + 1/8


def test_pct_color_thresholds():
    assert pct_color(10) == "green"
    assert pct_color(60) == "yellow"
    assert pct_color(85) == "red"


def test_meter_contains_label_and_percentage():
    text = meter("CPU", 42.0, width=10)
    assert "CPU" in text
    assert "42.0%" in text
    assert "[green]" in text
