"""Tests for the shared Rich table helpers and the proc renderers."""

from io import StringIO

from rich.console import Console

from ptools.lib.proc.render import detail_group, process_table
from ptools.lib.tui.tables import kv_table, rows_table


def render(renderable, width: int = 120) -> str:
    console = Console(file=StringIO(), width=width, force_terminal=False)
    console.print(renderable)
    return console.file.getvalue()


def test_kv_table_renders_pairs_and_placeholder_for_none():
    text = render(kv_table([("Name", "zsh"), ("CWD", None)], title="Overview"))
    assert "Overview" in text
    assert "Name" in text and "zsh" in text
    assert "(unavailable)" in text


def test_kv_table_accepts_mappings():
    text = render(kv_table({"a": 1, "b": 2}))
    assert "a" in text and "1" in text and "b" in text and "2" in text


def test_rows_table_with_explicit_columns():
    rows = [{"pid": 1, "name": "launchd"}, {"pid": 2, "name": "smd"}]
    text = render(rows_table(rows, [("pid", "PID", "right"), ("name", "Name")], title="Procs"))
    assert "Procs" in text
    assert "PID" in text and "Name" in text
    assert "launchd" in text and "smd" in text


def test_rows_table_auto_columns_and_none_cells():
    rows = [{"x": 5, "y": None}, {"x": 7, "y": "hello"}]
    text = render(rows_table(rows))
    assert "x" in text and "y" in text
    assert "hello" in text


def test_process_table_uses_field_titles_and_colors_cpu():
    rows = [{"pid": 42, "name": "node (vite.js)", "cpu": 93.0, "mem": "1.2G"}]
    table = process_table(rows, ["pid", "name", "cpu", "mem"])
    text = render(table)
    assert "PID" in text and "Name" in text and "CPU%" in text and "MEM" in text
    assert "node (vite.js)" in text
    # High CPU renders red when colors are on
    colored = Console(file=StringIO(), width=120, force_terminal=True)
    colored.print(table)
    assert "\x1b[" in colored.file.getvalue()


DETAIL = {
    "pid": 42, "name": "node", "display_name": "node (vite.js)",
    "exe": "/opt/homebrew/bin/node", "cmdline": ["node", "vite.js"],
    "user": "omar", "status": "running", "created": "2026-07-12 10:00:00",
    "cpu": 12.5, "mem_rss": 300 * 1024**2, "mem_vms": 4 * 1024**3, "mem_pct": 0.9,
    "threads": 12, "nice": 0, "cwd": "/Users/omar/project", "terminal": None,
    "parent": "1 launchd",
    "children": [{"pid": 43, "name": "esbuild"}],
    "open_files": ["/Users/omar/project/src/main.ts"],
    "connections": [{"local": "127.0.0.1:3000", "remote": "", "status": "LISTEN"}],
    "environ": {"PATH": "/usr/bin", "NODE_ENV": "development"},
    "bundle": "",
}


def test_detail_group_renders_all_sections_as_tables():
    text = render(detail_group(DETAIL))
    assert "node (vite.js)" in text
    assert "Children (1)" in text and "esbuild" in text
    assert "Connections (1)" in text and "127.0.0.1:3000" in text and "LISTEN" in text
    assert "Open files (1)" in text and "main.ts" in text
    assert "Environment (2)" in text and "NODE_ENV" in text


def test_detail_group_handles_unavailable_and_empty_sections():
    detail = dict(DETAIL, children=[], environ=None, open_files=None, connections=[])
    text = render(detail_group(detail))
    assert "Children: (none)" in text
    assert "Connections: (none)" in text
    assert "Open files: (unavailable - permission denied)" in text
    assert "Environment: (unavailable - permission denied)" in text
