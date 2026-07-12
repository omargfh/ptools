"""Rich renderables for process data - shared by the proc CLI and TUI.

The CLI prints these to stdout with a :class:`rich.console.Console`;
the TUI mounts them in a scrollable ``TextScreen``. Keeping the
rendering here means both surfaces always look the same.
"""

from __future__ import annotations

import humanize
from rich.console import Group
from rich.text import Text

from ptools.lib.proc.model import DURATION, FIELD_MAP, NUM, SIZE
from ptools.lib.tui.charts import pct_color
from ptools.lib.tui.tables import kv_table, rows_table

__version__ = "0.1.0"

_NUMERIC_KINDS = (NUM, SIZE, DURATION)


def _styled(key: str, value):
    """Severity-color the hot columns; leave everything else alone."""
    if key in ("cpu", "mem_pct") and isinstance(value, (int, float)):
        return Text(f"{value:.1f}", style=pct_color(float(value), warn=40, crit=80))
    return value


def process_table(rows: list[dict], columns: list[str], title: str | None = None):
    """Render process rows (already projected/humanized) as a table."""
    specs = []
    for key in columns:
        field = FIELD_MAP.get(key)
        header = field.title if field else key
        justify = "right" if field and field.kind in _NUMERIC_KINDS else "left"
        specs.append((key, header, justify))
    styled_rows = [{key: _styled(key, row.get(key)) for key in columns} for row in rows]
    return rows_table(styled_rows, specs, title=title)


def _section(title: str, items, table_fn):
    """Section header + table, or a dim placeholder when empty/unavailable."""
    if items is None:
        return Text(f"{title}: (unavailable - permission denied)", style="dim")
    if not items:
        return Text(f"{title}: (none)", style="dim")
    return table_fn(f"{title} ({len(items)})")


def detail_group(detail: dict) -> Group:
    """Everything about one process, as stacked tables."""
    cpu = detail.get("cpu")
    rss = detail.get("mem_rss")
    mem_pct = detail.get("mem_pct")
    cmdline = detail.get("cmdline")

    overview = kv_table([
        ("Name", detail.get("display_name") or detail.get("name")),
        ("PID", detail.get("pid")),
        ("Parent", detail.get("parent")),
        ("User", detail.get("user")),
        ("Status", detail.get("status")),
        ("Started", detail.get("created")),
        ("CPU", Text(f"{cpu:.1f}%", style=pct_color(cpu, warn=40, crit=80)) if cpu is not None else None),
        ("Memory", f"{humanize.naturalsize(rss)} rss ({mem_pct:.1f}%)"
                   if rss is not None and mem_pct is not None else None),
        ("Threads", detail.get("threads")),
        ("Nice", detail.get("nice")),
        ("Terminal", detail.get("terminal")),
        ("Bundle", detail.get("bundle") or ""),
        ("Exe", detail.get("exe")),
        ("CWD", detail.get("cwd")),
        ("Cmdline", " ".join(cmdline) if cmdline else None),
    ])

    children = detail.get("children")
    connections = detail.get("connections")
    open_files = detail.get("open_files")
    environ = detail.get("environ")

    return Group(
        overview,
        _section("Children", children, lambda title: rows_table(
            children, [("pid", "PID", "right"), ("name", "Name")], title=title,
        )),
        _section("Connections", connections, lambda title: rows_table(
            connections, [("local", "Local"), ("remote", "Remote"), ("status", "Status")], title=title,
        )),
        _section("Open files", open_files, lambda title: rows_table(
            [{"path": path} for path in open_files], [("path", "Path")], title=title,
        )),
        _section("Environment", environ, lambda title: rows_table(
            [{"var": key, "value": value} for key, value in sorted(environ.items())],
            [("var", "Variable"), ("value", "Value")], title=title,
        )),
    )
