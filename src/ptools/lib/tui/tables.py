"""Rich table helpers shared by ptools CLIs and TUIs.

Thin, opinionated wrappers around :class:`rich.table.Table` so every
ptools surface (CLI stdout, Textual screens) renders lists and
key/value data the same way.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

from rich import box
from rich.table import Table

__version__ = "0.1.0"

#: (key, header, justify) - justify may be omitted.
ColumnSpec = Sequence


def kv_table(pairs: Mapping | Iterable[tuple[str, Any]], title: str | None = None) -> Table:
    """Two-column key/value table (dim right-aligned keys)."""
    table = Table(
        show_header=False,
        box=box.SIMPLE,
        title=title,
        title_justify="left",
        title_style="bold",
        padding=(0, 1),
    )
    table.add_column(justify="right", style="bold cyan", no_wrap=True)
    table.add_column(overflow="fold")
    items = pairs.items() if isinstance(pairs, Mapping) else pairs
    for key, value in items:
        table.add_row(str(key), _cell(value) if value is not None else "(unavailable)")
    return table


def rows_table(
    rows: list[dict],
    columns: list[ColumnSpec] | None = None,
    title: str | None = None,
) -> Table:
    """Table of dict rows.

    ``columns`` is a list of ``(key, header)`` or ``(key, header, justify)``;
    when omitted, the first row's keys become the columns and numeric
    columns are right-justified automatically.
    """
    if columns is None:
        first = rows[0] if rows else {}
        columns = [(key, key, _auto_justify(rows, key)) for key in first.keys()]

    table = Table(
        box=box.SIMPLE_HEAVY,
        header_style="bold",
        title=title,
        title_justify="left",
        title_style="bold",
        padding=(0, 1),
    )
    for spec in columns:
        key, header = spec[0], spec[1]
        justify = spec[2] if len(spec) > 2 else "left"
        table.add_column(str(header), justify=justify, overflow="fold")
    for row in rows:
        table.add_row(*[_cell(row.get(spec[0])) for spec in columns])
    return table


def _cell(value: Any):
    if value is None:
        return ""
    return value if _is_renderable(value) else str(value)


def _auto_justify(rows: list[dict], key: str) -> str:
    for row in rows:
        value = row.get(key)
        if value is None:
            continue
        return "right" if isinstance(value, (int, float)) else "left"
    return "left"


def _is_renderable(value: Any) -> bool:
    """True for Rich renderables that should be passed through untouched."""
    return hasattr(value, "__rich_console__") or hasattr(value, "__rich__")
