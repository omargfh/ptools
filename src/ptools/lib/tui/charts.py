"""Terminal chart primitives shared by ptools TUIs.

Pure string-producing helpers with no Textual imports, so they can be
used in any Rich/Textual label, DataTable cell, or plain CLI output -
and unit tested without an app.
"""

from __future__ import annotations

__version__ = "0.1.0"

# Eighth-height blocks, lowest to highest, for sparklines.
SPARK_BLOCKS = "▁▂▃▄▅▆▇█"
# Eighth-width blocks for the fractional cell of a horizontal gauge.
GAUGE_PARTIALS = " ▏▎▍▌▋▊▉█"


def sparkline(
    values: list[float | int | None],
    width: int | None = None,
    v_min: float = 0.0,
    v_max: float | None = None,
) -> str:
    """Render ``values`` as a one-line block-character sparkline.

    ``None`` values are treated as 0. When ``width`` is given, only the
    last ``width`` values are shown and the result is left-padded with
    spaces to exactly ``width`` characters. ``v_max`` defaults to the
    max of the rendered values, so the line is self-scaling.
    """
    nums = [0.0 if v is None else float(v) for v in values]
    if width is not None:
        nums = nums[-width:]
    if not nums:
        return "" if width is None else " " * width

    top = max(nums) if v_max is None else float(v_max)
    span = top - v_min

    chars = []
    for v in nums:
        if span <= 0:
            index = 0 if v <= v_min else len(SPARK_BLOCKS) - 1
        else:
            fraction = min(1.0, max(0.0, (v - v_min) / span))
            index = round(fraction * (len(SPARK_BLOCKS) - 1))
        chars.append(SPARK_BLOCKS[index])

    line = "".join(chars)
    if width is not None and len(line) < width:
        line = " " * (width - len(line)) + line
    return line


def gauge(fraction: float, width: int = 10) -> str:
    """Render ``fraction`` (0..1) as a fixed-``width`` horizontal bar.

    Uses eighth-width partial blocks for sub-cell resolution, e.g.
    ``gauge(0.5625, 2) == "█▏"``. Always returns exactly ``width`` chars.
    """
    fraction = min(1.0, max(0.0, fraction))
    cells = fraction * width
    full = int(cells)
    partial_index = round((cells - full) * 8)
    if partial_index == 8:
        full += 1
        partial_index = 0

    bar = "█" * full
    if full < width and partial_index > 0:
        bar += GAUGE_PARTIALS[partial_index]
    return bar.ljust(width)


def pct_color(pct: float, warn: float = 60.0, crit: float = 85.0) -> str:
    """Return a Rich color name for a 0-100 percentage by severity."""
    if pct >= crit:
        return "red"
    if pct >= warn:
        return "yellow"
    return "green"


def meter(label: str, pct: float, width: int = 20) -> str:
    """Render ``label ▕bar▏ NN%`` as Rich markup, colored by severity."""
    color = pct_color(pct)
    bar = gauge(pct / 100.0, width)
    return f"{label} ▕[{color}]{bar}[/{color}]▏ {pct:5.1f}%"
