"""Live process explorer TUI (a better ``ps aux``) using Textual.

Keybindings:
    arrows / j/k   - navigate
    enter / i      - inspect selected process (detail screen)
    /              - filter bar (query DSL, e.g. ``cpu>50 & name~node``)
    f              - filter wizard (pick field/operator/value, no DSL needed)
    s / o          - cycle sort column / toggle order
    t              - toggle tree view (with subtree CPU/MEM aggregation)
    space          - pause / resume auto-refresh
    r              - force refresh (also clears join caches)
    1-6            - toggle joins: ports, watchers, files, launchd, docker, io
    k / K / ctrl+k - SIGTERM / SIGKILL / SIGTERM whole subtree
    z              - suspend / resume (SIGSTOP / SIGCONT)
    n              - renice
    y              - copy PID + command line to clipboard
    O              - open cwd in Finder
    P              - profile with `sample`
    w              - watch: bell + notification when the process exits
    :              - kill whatever is listening on a port
    ?              - help
    q              - quit
"""

from __future__ import annotations

from typing import Callable

import click
import humanize
from rich.console import Group
from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.coordinate import Coordinate
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Input, OptionList, Static
from textual.widgets.option_list import Option

from ptools.lib.proc import actions, sources
from ptools.lib.proc.filter_wizard import (
    OPERATOR_LABELS,
    VALUE_PLACEHOLDERS,
    format_clause,
    join_clauses,
    operators_for_kind,
)
from ptools.lib.proc.history import History
from ptools.lib.proc.model import FIELD_MAP, FIELDS, JOINS
from ptools.lib.proc.query import QueryError, compile_query, substring_query
from ptools.lib.proc.render import detail_group
from ptools.lib.tui.charts import meter, pct_color, sparkline
from ptools.lib.tui.screens import ConfirmScreen, InputScreen, TextScreen
from ptools.lib.tui.tables import rows_table
from ptools import settings

__version__ = "0.1.1"

BASE_COLUMNS = ["pid", "name", "user", "cpu", "_spark", "mem", "mem_pct", "status", "age"]
JOIN_COLUMNS = {
    "ports": ["ports", "conns"],
    "watchers": ["fds", "kqueues"],
    "files": ["nfiles", "cwd"],
    "launchd": ["service"],
    "docker": ["container"],
    "io": ["io_read", "io_write"],
}
TREE_COLUMNS = ["_cpu_sum", "_mem_sum"]
SYNTHETIC_TITLES = {"_spark": "CPU ▂▄▆", "_cpu_sum": "ΣCPU%", "_mem_sum": "ΣMEM"}
COLUMN_WIDTHS = {"name": 32, "cwd": 28, "service": 24, "container": 16, "ports": 14}
SORT_KEYS = ["cpu", "mem", "pid", "name", "age"]
SPARK_WIDTH = 8

_STATUS_SHORT = {
    "running": "run", "sleeping": "slp", "idle": "idle", "stopped": "stop",
    "zombie": "zomb", "disk-sleep": "dsk", "waiting": "wait",
}

_HELP_VIEW_KEYS = [
    ("arrows / j k", "navigate"),
    ("enter / i", "inspect selected process"),
    ("/", "filter bar (DSL, e.g. cpu>50 & name~node)"),
    ("f", "filter wizard (pick field/operator/value)"),
    ("s / o", "cycle sort column / toggle order"),
    ("t", "tree view with subtree ΣCPU/ΣMEM"),
    ("space", "pause / resume auto-refresh"),
    ("r", "force refresh (clears join caches)"),
    ("?", "this help"),
    ("q", "quit"),
]
_HELP_ACTION_KEYS = [
    ("k / K", "kill: SIGTERM / SIGKILL"),
    ("ctrl+k", "kill whole subtree"),
    ("z", "suspend / resume (SIGSTOP / SIGCONT)"),
    ("n", "renice"),
    ("y", "copy PID + command line"),
    ("O", "open cwd in Finder"),
    ("P", "profile with `sample`"),
    ("w", "watch: notify when the process exits"),
    (":", "kill whatever listens on a port"),
]


def _keys_table(title: str, pairs: list[tuple[str, str]]):
    rows = [{"key": key, "action": action} for key, action in pairs]
    return rows_table(rows, [("key", "Key"), ("action", "Action")], title=title)


def _help_group() -> Group:
    join_rows = [(str(i + 1), join) for i, join in enumerate(JOINS)]
    return Group(
        _keys_table("View", _HELP_VIEW_KEYS),
        _keys_table("Joins (toggle)", join_rows),
        _keys_table("Actions on selected process", _HELP_ACTION_KEYS),
    )


def _fmt_age(seconds: float | None) -> str:
    if seconds is None:
        return "?"
    seconds = int(seconds)
    if seconds >= 86400:
        return f"{seconds // 86400}d{(seconds % 86400) // 3600}h"
    if seconds >= 3600:
        return f"{seconds // 3600}h{(seconds % 3600) // 60}m"
    if seconds >= 60:
        return f"{seconds // 60}m{seconds % 60}s"
    return f"{seconds}s"


def _shorten_path(path: str, width: int) -> str:
    import os
    home = os.path.expanduser("~")
    if path.startswith(home):
        path = "~" + path[len(home):]
    if len(path) > width:
        path = "…" + path[-(width - 1):]
    return path


def _tree_order(rows: list[dict], key_fn, reverse: bool) -> list[dict]:
    """Order rows as a forest (children under parents) with aggregates.

    Aggregation runs over the *visible* rows only, so filtered-out
    children don't contribute to their parent's ΣCPU/ΣMEM.
    """
    by_pid = {row["pid"]: row for row in rows}
    children: dict[int, list[dict]] = {}
    roots: list[dict] = []
    for row in rows:
        ppid = row.get("ppid")
        if ppid is not None and ppid != row["pid"] and ppid in by_pid:
            children.setdefault(ppid, []).append(row)
        else:
            roots.append(row)

    def aggregate(row: dict) -> tuple[float, float]:
        cpu = row.get("cpu") or 0.0
        mem = float(row.get("mem") or 0)
        for child in children.get(row["pid"], []):
            child_cpu, child_mem = aggregate(child)
            cpu += child_cpu
            mem += child_mem
        row["_cpu_sum"] = cpu
        row["_mem_sum"] = mem
        return cpu, mem

    ordered: list[dict] = []

    def walk(rows_at_level: list[dict], depth: int) -> None:
        rows_at_level = sorted(rows_at_level, key=key_fn, reverse=reverse)
        for i, row in enumerate(rows_at_level):
            row["_depth"] = depth
            row["_last"] = i == len(rows_at_level) - 1
            ordered.append(row)
            walk(children.get(row["pid"], []), depth + 1)

    for root in roots:
        aggregate(root)
    walk(roots, 0)
    return ordered


def _edit_expression(app: App, expression: str) -> str:
    """Suspend *app*'s terminal control and open *expression* in ``$EDITOR``.

    Mirrors :func:`ptools.proc._edit_wizard_expression` for the CLI wizard:
    falls back to the unedited expression when the editor exits without
    saving. A standalone function (rather than a method) so tests can
    monkeypatch it directly instead of needing a real terminal/editor.
    """
    with app.suspend():
        edited = click.edit(text=expression, editor=settings.EDITOR)
    return (edited if edited is not None else expression).strip()


class FilterWizardScreen(Screen):
    """Pick a field, an operator valid for its kind, and a value.

    Unlike a sequential wizard where each step replaces the screen
    before it, the field list, operator list, and value input are three
    simultaneously-visible panels (see :attr:`CSS`) so earlier choices
    stay on screen while later ones are made. Clauses are joined with
    ``&``/``|`` (toggled with ``o``) using the same shell-agnostic
    helpers :mod:`ptools.proc`'s CLI wizard uses
    (:mod:`ptools.lib.proc.filter_wizard`) -- no parallel filter-building
    logic. Finishing (``f2``) opens the assembled expression in
    ``$EDITOR`` for a last freeform tweak, then hands the result to
    *on_submit* (the host app's ``_set_where``).
    """

    BINDINGS = [
        Binding("escape", "cancel_wizard", "Cancel"),
        Binding("f2", "finish_wizard", "Finish (edit & apply)"),
        Binding("o", "toggle_combinator", "Toggle AND/OR", show=False),
    ]

    CSS = """
    FilterWizardScreen #wizard-panels {
        height: 1fr;
    }
    FilterWizardScreen .wizard-panel {
        width: 1fr;
        height: 100%;
        border: solid $primary;
        padding: 0 1;
    }
    FilterWizardScreen .panel-title {
        text-style: bold;
        height: 1;
    }
    FilterWizardScreen #wizard-status {
        dock: bottom;
        height: 4;
        padding: 0 1;
        background: $panel;
    }
    """

    def __init__(self, on_submit: Callable[[str], None], **kwargs):
        super().__init__(**kwargs)
        self.on_submit = on_submit
        self._clauses: list[str] = []
        self._combinators: list[str] = []
        self._pending_combinator = "&"
        self._field = None
        self._op: str | None = None

    def compose(self) -> ComposeResult:
        yield Header(name="Filter wizard")
        with Horizontal(id="wizard-panels"):
            with Vertical(classes="wizard-panel"):
                yield Static("Field", classes="panel-title")
                yield OptionList(*self._field_options(), id="field-list")
            with Vertical(classes="wizard-panel"):
                yield Static("Operator", classes="panel-title")
                yield OptionList(id="operator-list")
            with Vertical(classes="wizard-panel"):
                yield Static("Value", classes="panel-title")
                yield Input(placeholder="pick a field and operator first", id="value-input")
        yield Static(id="wizard-status")
        yield Footer()

    @staticmethod
    def _field_label(field) -> str:
        return f"{field.title} — {field.help}" if field.help else field.title

    def _field_options(self) -> list[Option]:
        return [Option(self._field_label(f), id=f.key) for f in FIELDS]

    def on_mount(self) -> None:
        self.query_one("#field-list", OptionList).focus()
        self._update_status()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        event.stop()
        if event.option_list.id == "field-list":
            self._select_field(event.option_id)
        elif event.option_list.id == "operator-list":
            self._select_operator(event.option_id)

    def _select_field(self, field_key: str | None) -> None:
        if field_key is None:
            return
        self._field = FIELD_MAP[field_key]
        self._op = None
        op_list = self.query_one("#operator-list", OptionList)
        op_list.clear_options()
        for op in operators_for_kind(self._field.kind):
            op_list.add_option(Option(OPERATOR_LABELS[op], id=op))
        value_input = self.query_one("#value-input", Input)
        value_input.value = ""
        value_input.placeholder = VALUE_PLACEHOLDERS.get(self._field.kind, "")
        op_list.focus()
        self._update_status()

    def _select_operator(self, op: str | None) -> None:
        if op is None:
            return
        self._op = op
        self.query_one("#value-input", Input).focus()
        self._update_status()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "value-input":
            return
        event.stop()
        self._commit_clause(event.value)

    def _commit_clause(self, raw_value: str) -> None:
        raw_value = raw_value.strip()
        if self._field is None or self._op is None or not raw_value:
            self.app.bell()
            return
        clause = format_clause(self._field, self._op, raw_value)
        if self._clauses:
            self._combinators.append(self._pending_combinator)
        self._clauses.append(clause)

        self._field = None
        self._op = None
        value_input = self.query_one("#value-input", Input)
        value_input.value = ""
        value_input.placeholder = "pick a field and operator first"
        self.query_one("#operator-list", OptionList).clear_options()
        self.query_one("#field-list", OptionList).focus()
        self._update_status()

    def action_toggle_combinator(self) -> None:
        self._pending_combinator = "|" if self._pending_combinator == "&" else "&"
        self._update_status()

    def _update_status(self) -> None:
        status = self.query_one("#wizard-status", Static)
        expr = join_clauses(self._clauses, self._combinators)
        combinator_name = "AND" if self._pending_combinator == "&" else "OR"
        status.update(
            f"Clauses so far: {expr or '(none yet)'}\n"
            f"next join: {combinator_name} (press 'o' to toggle)   "
            "enter in value = add clause   f2 = finish (edit & apply)   esc = cancel"
        )

    def action_cancel_wizard(self) -> None:
        self.app.pop_screen()

    def action_finish_wizard(self) -> None:
        expression = join_clauses(self._clauses, self._combinators)
        if not expression:
            self.app.bell()
            return
        final = _edit_expression(self.app, expression)
        self.app.pop_screen()
        if final:
            self.on_submit(final)


class ProcApp(App):
    """Full-screen live process explorer."""

    TITLE = "Processes"
    CSS = """
    #system-panel {
        dock: top;
        height: 2;
        padding: 0 1;
        background: $panel;
    }
    #proc-table {
        height: 1fr;
    }
    #filter-bar {
        dock: bottom;
        height: 3;
        display: none;
    }
    #filter-bar.visible {
        display: block;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("slash", "show_filter", "Filter", key_display="/"),
        Binding("f", "show_filter_wizard", "Filter wizard"),
        Binding("s", "cycle_sort", "Sort"),
        Binding("o", "toggle_order", "Order"),
        Binding("t", "toggle_tree", "Tree"),
        Binding("space", "toggle_pause", "Pause"),
        Binding("r", "refresh", "Refresh"),
        Binding("i", "inspect", "Inspect"),
        Binding("k", "kill(False, False)", "Kill"),
        Binding("K", "kill(True, False)", "Kill -9", show=False),
        Binding("ctrl+k", "kill(False, True)", "Kill tree", show=False),
        Binding("z", "suspend", "Suspend/Resume", show=False),
        Binding("n", "renice", "Renice", show=False),
        Binding("y", "copy", "Copy", show=False),
        Binding("O", "open_cwd", "Open cwd", show=False),
        Binding("P", "profile", "Profile", show=False),
        Binding("w", "watch", "Watch", show=False),
        Binding("colon", "kill_port", "Kill port", show=False, key_display=":"),
        Binding("question_mark", "help", "Help", key_display="?"),
    ] + [
        Binding(str(i + 1), f"toggle_join('{join}')", join, show=False)
        for i, join in enumerate(JOINS)
    ]

    def __init__(
        self,
        where: str | None = None,
        joins: set[str] | None = None,
        refresh_interval: float = 2.0,
        tree: bool = False,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.joins: set[str] = set(joins or ())
        self.refresh_interval = max(0.5, refresh_interval)
        self.sort_by = "name"
        self.sort_order = "desc"
        self.tree_mode = tree
        self.paused = False
        self.where_text = where or ""
        self._query = substring_query("")
        self._query_ok = True
        self._rows: list[dict] = []
        self._rows_by_pid: dict[int, dict] = {}
        self._history = History()
        self._last_system: dict | None = None
        self._watched: dict[int, str] = {}
        self._scanning = False
        self._current_cols: list[str] = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(id="system-panel")
        yield DataTable(id="proc-table")
        yield Input(placeholder="Filter: e.g. cpu>50 & name~node   (plain text works too)", id="filter-bar")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#proc-table", DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True
        table.focus()
        self._set_where(self.where_text, rescan=False)
        self._update_subtitle()
        self.set_interval(self.refresh_interval, self._tick)
        self._request_scan()

    # ------------------------------------------------------------------
    # Data flow: tick -> scan (worker thread) -> apply (main thread)
    # ------------------------------------------------------------------

    def _tick(self) -> None:
        if not self.paused:
            self._request_scan()

    def _request_scan(self) -> None:
        if self._scanning:
            return
        self._scanning = True
        self._scan()

    @work(thread=True, exclusive=True, group="scan")
    def _scan(self) -> None:
        try:
            rows = sources.scan(self.joins)
            system = sources.system_snapshot()
            self.call_from_thread(self._apply, rows, system)
        finally:
            self._scanning = False

    def _apply(self, rows: list[dict], system: dict) -> None:
        self._history.record(rows, system)
        self._last_system = system
        self._rows = rows
        self._rows_by_pid = {row["pid"]: row for row in rows}
        self._notify_watched_exits()
        self._render()

    def _notify_watched_exits(self) -> None:
        for pid in list(self._watched):
            if pid not in self._rows_by_pid:
                name = self._watched.pop(pid)
                self.bell()
                self.notify(f"Watched process exited: PID {pid} ({name})", severity="warning", timeout=10)

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _sort_key_fn(self):
        key = self.sort_by
        if key == "name":
            return lambda row: str(row.get("name") or "").lower()
        return lambda row: row.get(key) or 0

    def _visible_rows(self) -> list[dict]:
        rows = [row for row in self._rows if self._query.match(row)]
        reverse = self.sort_order == "desc"
        if self.tree_mode:
            return _tree_order(rows, self._sort_key_fn(), reverse)
        return sorted(rows, key=self._sort_key_fn(), reverse=reverse)

    def _column_keys(self) -> list[str]:
        cols = list(BASE_COLUMNS)
        if self.tree_mode:
            cols[cols.index("cpu") + 1:cols.index("cpu") + 1] = TREE_COLUMNS
        for join in JOINS:  # stable order regardless of toggle order
            if join in self.joins:
                cols.extend(JOIN_COLUMNS[join])
        return cols

    def _render(self) -> None:
        table = self.query_one("#proc-table", DataTable)
        selected = self._selected_pid()
        ordered = self._visible_rows()

        cols = self._column_keys()
        if cols != self._current_cols:
            table.clear(columns=True)
            for key in cols:
                field = FIELD_MAP.get(key)
                title = SYNTHETIC_TITLES.get(key) or (field.title if field else key)
                table.add_column(title, key=key, width=COLUMN_WIDTHS.get(key))
            self._current_cols = cols
        else:
            table.clear()

        cursor_row = 0
        for index, row in enumerate(ordered):
            table.add_row(*[self._format_cell(key, row) for key in cols], key=str(row["pid"]))
            if row["pid"] == selected:
                cursor_row = index
        if table.row_count:
            table.move_cursor(row=cursor_row, animate=False)

        self._update_system_panel(len(ordered))
        self._update_subtitle()

    def _format_cell(self, key: str, row: dict):
        value = row.get(key)
        if key == "pid":
            return str(value)
        if key == "name":
            name = str(value or "?")
            prefix = ""
            depth = row.get("_depth")
            if self.tree_mode and depth:
                prefix = "│ " * (depth - 1) + ("└─" if row.get("_last") else "├─")
            marker = "★" if row["pid"] in self._watched else ""
            text = Text(f"{prefix}{marker}{name}")
            if row.get("kind") == "helper":
                text.stylize("dim")
            return text
        if key in ("cpu", "_cpu_sum"):
            pct = float(value or 0.0)
            return Text(f"{pct:5.1f}", style=pct_color(pct, warn=40, crit=80))
        if key == "_spark":
            return Text(sparkline(self._history.cpu_series(row["pid"]), width=SPARK_WIDTH, v_max=100), style="cyan")
        if key in ("mem", "_mem_sum"):
            return humanize.naturalsize(value or 0, gnu=True)
        if key == "mem_pct":
            return f"{float(value or 0.0):4.1f}"
        if key == "status":
            status = str(value or "?")
            return _STATUS_SHORT.get(status, status[:4])
        if key == "age":
            return _fmt_age(value)
        if key == "ports":
            ports = value or []
            shown = ",".join(str(p) for p in ports[:4])
            if len(ports) > 4:
                shown += f"+{len(ports) - 4}"
            return Text(shown, style="bold blue") if shown else ""
        if key in ("cwd", "service", "container"):
            width = COLUMN_WIDTHS.get(key, 24)
            return _shorten_path(str(value), width) if value else ""
        if key in ("io_read", "io_write"):
            if value is None:
                return Text("–", style="dim")
            if value < 1024:
                return Text("0", style="dim")
            return f"{humanize.naturalsize(value, gnu=True)}/s"
        return str(value if value is not None else "")

    def _update_system_panel(self, visible_count: int) -> None:
        panel = self.query_one("#system-panel", Static)
        system = self._last_system
        if not system:
            panel.update("scanning...")
            return
        cpu_spark = sparkline(list(self._history.system_cpu), width=20, v_max=100)
        mem_spark = sparkline(list(self._history.system_mem), width=20, v_max=100)
        load = system["load"]
        used = humanize.naturalsize(system["mem_used"], gnu=True)
        total = humanize.naturalsize(system["mem_total"], gnu=True)
        line1 = (
            f"{meter('CPU', system['cpu'], 16)} [cyan]{cpu_spark}[/cyan]"
            f"  load {load[0]:.2f} {load[1]:.2f} {load[2]:.2f}  ({system['ncpu']} cores)"
        )
        line2 = (
            f"{meter('MEM', system['mem_pct'], 16)} [cyan]{mem_spark}[/cyan]"
            f"  {used}/{total}  {visible_count}/{system['nproc']} procs"
        )
        panel.update(f"{line1}\n{line2}")

    def _update_subtitle(self) -> None:
        parts = [f"sort: {self.sort_by} {self.sort_order}"]
        if self.tree_mode:
            parts.append("tree")
        if self.joins:
            parts.append("joins: " + ",".join(j for j in JOINS if j in self.joins))
        if self.where_text.strip():
            kind = "where" if self._query_ok else "text"
            parts.append(f"{kind}: {self.where_text.strip()}")
        if self.paused:
            parts.append("PAUSED")
        self.sub_title = " │ ".join(parts)

    # ------------------------------------------------------------------
    # Selection helpers
    # ------------------------------------------------------------------

    def _selected_pid(self) -> int | None:
        table = self.query_one("#proc-table", DataTable)
        if not table.row_count:
            return None
        try:
            cell_key = table.coordinate_to_cell_key(Coordinate(table.cursor_row, 0))
            return int(cell_key.row_key.value)
        except Exception:
            return None

    def _selected_row(self) -> dict | None:
        pid = self._selected_pid()
        row = self._rows_by_pid.get(pid) if pid is not None else None
        if row is None:
            self.bell()
        return row

    # ------------------------------------------------------------------
    # Filter bar
    # ------------------------------------------------------------------

    def _set_where(self, text: str, rescan: bool = True) -> None:
        self.where_text = text
        try:
            self._query = compile_query(text)
            self._query_ok = True
        except QueryError:
            self._query = substring_query(text)
            self._query_ok = False
        # Filtering on a join-provided field silently enables that join.
        needed = self._query.required_joins() - self.joins
        if rescan:
            if needed:
                self.joins |= needed
                self._request_scan()
            else:
                self._render()

    def action_show_filter(self) -> None:
        filter_bar = self.query_one("#filter-bar", Input)
        if filter_bar.has_class("visible"):
            self._hide_filter()
        else:
            filter_bar.add_class("visible")
            filter_bar.focus()

    def action_show_filter_wizard(self) -> None:
        """Push the field/operator/value filter builder (no DSL required)."""
        self.push_screen(FilterWizardScreen(self._apply_wizard_filter))

    def _apply_wizard_filter(self, expression: str) -> None:
        """Feed the wizard's compiled expression through the same path the
        filter-bar Input uses (``_set_where``), also syncing the bar's
        displayed text so it reflects what's now active.
        """
        filter_bar = self.query_one("#filter-bar", Input)
        filter_bar.value = expression
        filter_bar.add_class("visible")
        self._set_where(expression)

    def _hide_filter(self) -> None:
        filter_bar = self.query_one("#filter-bar", Input)
        filter_bar.remove_class("visible")
        filter_bar.value = ""
        self._set_where("")
        self.query_one("#proc-table", DataTable).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "filter-bar":
            self._set_where(event.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "filter-bar":
            self.query_one("#proc-table", DataTable).focus()

    def on_key(self, event) -> None:
        if event.key == "escape":
            filter_bar = self.query_one("#filter-bar", Input)
            if filter_bar.has_class("visible"):
                self._hide_filter()

    # ------------------------------------------------------------------
    # View actions
    # ------------------------------------------------------------------

    def action_cycle_sort(self) -> None:
        index = SORT_KEYS.index(self.sort_by) if self.sort_by in SORT_KEYS else 0
        self.sort_by = SORT_KEYS[(index + 1) % len(SORT_KEYS)]
        self._render()

    def action_toggle_order(self) -> None:
        self.sort_order = "asc" if self.sort_order == "desc" else "desc"
        self._render()

    def action_toggle_tree(self) -> None:
        self.tree_mode = not self.tree_mode
        self._render()

    def action_toggle_pause(self) -> None:
        self.paused = not self.paused
        self._update_subtitle()

    def action_refresh(self) -> None:
        sources.clear_cache()
        self._request_scan()

    def action_toggle_join(self, join: str) -> None:
        if join in self.joins:
            self.joins.discard(join)
            self._render()
        else:
            self.joins.add(join)
            self._request_scan()
        self.notify(f"join {join}: {'on' if join in self.joins else 'off'}", timeout=2)

    def action_help(self) -> None:
        self.push_screen(TextScreen("Help", _help_group()))

    # ------------------------------------------------------------------
    # Process actions
    # ------------------------------------------------------------------

    def action_kill(self, force: bool, tree: bool) -> None:
        row = self._selected_row()
        if row is None:
            return
        pid, name = row["pid"], row["name"]
        signal_name = "SIGKILL" if force else "SIGTERM"
        target = f"subtree of PID {pid}" if tree else f"PID {pid}"

        def do_kill():
            if tree:
                self.notify(actions.kill_tree(pid, force=force))
            else:
                self.notify(actions.terminate(pid, force=force))

        self.push_screen(ConfirmScreen(f"Send {signal_name} to {target} ({name})?", do_kill))

    def action_suspend(self) -> None:
        row = self._selected_row()
        if row is None:
            return
        self._notify_action(lambda: actions.toggle_suspend(row["pid"]))

    def action_renice(self) -> None:
        row = self._selected_row()
        if row is None:
            return
        pid = row["pid"]

        def submit(value: str):
            self._notify_action(lambda: actions.renice(pid, int(value)))

        self.push_screen(InputScreen(
            f"New nice value for PID {pid} ({row['name']}), currently {row.get('nice')}:",
            submit, placeholder="-20 (high priority) .. 19 (low)",
        ))

    def action_copy(self) -> None:
        row = self._selected_row()
        if row is None:
            return
        self._notify_action(lambda: actions.copy_to_clipboard(f"{row['pid']}\t{row.get('cmd') or row['name']}"))

    def action_open_cwd(self) -> None:
        row = self._selected_row()
        if row is None:
            return
        self._notify_action(lambda: actions.open_cwd(row["pid"]))

    def action_watch(self) -> None:
        row = self._selected_row()
        if row is None:
            return
        pid = row["pid"]
        if pid in self._watched:
            del self._watched[pid]
            self.notify(f"Unwatched PID {pid}.", timeout=3)
        else:
            self._watched[pid] = row["name"]
            self.notify(f"Watching PID {pid} ({row['name']}) - you'll be notified when it exits.", timeout=3)
        self._render()

    def action_kill_port(self) -> None:
        def submit(value: str):
            port = int(value)
            self.push_screen(ConfirmScreen(
                f"Kill every process listening on port {port}?",
                lambda: self.notify(actions.kill_by_port(port)),
            ))

        self.push_screen(InputScreen("Kill processes by listening port:", submit, placeholder="e.g. 3000"))

    def _notify_action(self, fn) -> None:
        try:
            self.notify(fn())
        except actions.ActionError as e:
            self.bell()
            self.notify(str(e), severity="error", timeout=6)

    # ------------------------------------------------------------------
    # Detail / profile (worker threads; both end by pushing a TextScreen)
    # ------------------------------------------------------------------

    def action_inspect(self) -> None:
        row = self._selected_row()
        if row is None:
            return
        self._fetch_detail(row["pid"])

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        try:
            self._fetch_detail(int(event.row_key.value))
        except (TypeError, ValueError):
            pass

    @work(thread=True, exclusive=True, group="detail")
    def _fetch_detail(self, pid: int) -> None:
        try:
            content = detail_group(sources.process_detail(pid))
        except Exception as e:
            self.call_from_thread(self.notify, f"Cannot inspect PID {pid}: {e}", severity="error")
            return
        self.call_from_thread(self.push_screen, TextScreen(f"PID {pid}", content))

    def action_profile(self) -> None:
        row = self._selected_row()
        if row is None:
            return
        self.notify(f"Sampling PID {row['pid']} for 3s...", timeout=3)
        self._run_sample(row["pid"])

    @work(thread=True, exclusive=True, group="profile")
    def _run_sample(self, pid: int) -> None:
        try:
            report = actions.sample(pid, seconds=3)
        except actions.ActionError as e:
            self.call_from_thread(self.notify, str(e), severity="error", timeout=6)
            return
        self.call_from_thread(self.push_screen, TextScreen(f"sample of PID {pid}", report))


def launch_proc_app(
    where: str | None = None,
    joins: set[str] | None = None,
    refresh_interval: float = 2.0,
    tree: bool = False,
) -> None:
    """Entry point used by ``ptools proc``."""
    ProcApp(where=where, joins=joins, refresh_interval=refresh_interval, tree=tree).run()
