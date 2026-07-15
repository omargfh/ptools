"""``ptools proc`` - a better ``ps aux``: live TUI plus scriptable listing."""

import click

from ptools.settings import EDITOR
from ptools.utils.output import output_flavor, OutputFlavorKind
from ptools.lib.proc.filter_wizard import (
    OPERATOR_LABELS,
    VALUE_PLACEHOLDERS,
    format_clause,
    join_clauses,
    operators_for_kind,
)
from ptools.lib.proc.model import FIELD_MAP, FIELDS, JOINS, required_joins

_JOIN_CHOICES = list(JOINS) + ["all"]
_SORT_CHOICES = ["cpu", "mem", "pid", "name", "age"]
_DEFAULT_COLS = ["pid", "name", "user", "cpu", "mem", "mem_pct", "status", "age"]
_JOIN_COLS = {
    "ports": ["ports", "conns"],
    "watchers": ["fds", "kqueues"],
    "files": ["nfiles", "cwd"],
    "launchd": ["service"],
    "docker": ["container", "image"],
    "io": ["io_read", "io_write"],
}
# Delta-based collectors need a second sample to be meaningful.
_PRIME_SLEEP_SECS = 0.25

# ----------------------------------------------------------------------
# Interactive filter wizard (``proc list --wizard``)
#
# The shell-agnostic pieces (which operators a field's kind allows, how
# to quote/join clauses) live in ``lib.proc.filter_wizard`` so the
# Textual TUI's own filter screen (``lib.proc.app.FilterWizardScreen``)
# can reuse them without duplicating this logic.
# ----------------------------------------------------------------------


def _select(options: list[tuple], title: str, selected: str | None = None) -> str | None:
    """Run an inline arrow-key picker over ``(value, label[, description])`` options.

    Returns the chosen value, or ``None`` when the user cancels (escape).
    """
    from ptools.lib.tui.select import SelectApp

    return SelectApp(options, message=title, selected=selected).run() or None


def _text(message: str, placeholder: str = "") -> str:
    """Prompt for a single line of text with a dim placeholder example."""
    from ptools.lib.tui.select import ask_text

    return ask_text(message, placeholder=placeholder)


def _build_wizard_clause() -> str | None:
    """Pick a field, a kind-appropriate operator, and a value.

    Returns the clause text (e.g. ``cpu>50``), or ``None`` if the user
    cancels any step.
    """
    field_key = _select(
        [(f.key, f.title, f.help) for f in FIELDS],
        "Field to filter on:",
    )
    if field_key is None:
        return None
    field = FIELD_MAP[field_key]

    op = _select(
        [(o, OPERATOR_LABELS[o]) for o in operators_for_kind(field.kind)],
        f"Operator for {field.title}:",
    )
    if op is None:
        return None

    value = _text(
        f"Value for {field.title} {op}:",
        placeholder=VALUE_PLACEHOLDERS.get(field.kind, ""),
    ).strip()
    if not value:
        return None

    return format_clause(field, op, value)


def _run_filter_wizard() -> str | None:
    """Interactively build a filter expression, chaining clauses with &/|.

    Produces the same expression syntax :func:`~ptools.lib.proc.query.compile_query`
    accepts from ``--where``/the positional query -- no parallel filtering
    representation. Returns ``None`` if the user cancels before completing
    a single clause.
    """
    clauses: list[str] = []
    combinators: list[str] = []
    while True:
        clause = _build_wizard_clause()
        if clause is None:
            break
        clauses.append(clause)

        choice = _select(
            [
                ("done", "Done"),
                ("&", "Add another clause (AND)"),
                ("|", "Add another clause (OR)"),
            ],
            "Add another clause?",
        )
        if choice is None or choice == "done":
            break
        combinators.append(choice)

    return join_clauses(clauses, combinators)


def _edit_wizard_expression(expression: str) -> str:
    """Open *expression* in the ``EDITOR`` setting for freeform tweaks.

    ``click.edit`` returns ``None`` when the editor is closed without
    saving/changes, in which case the original expression is kept as-is.
    """
    edited = click.edit(text=expression, editor=EDITOR)
    return (edited if edited is not None else expression).strip()


def _expand_joins(joins) -> set[str]:
    joins = set(joins)
    return set(JOINS) if "all" in joins else joins


def _compile(where: str | None):
    """Compile a --where expression, exiting with a clear error if invalid."""
    from ptools.lib.proc.query import QueryError, compile_query

    try:
        return compile_query(where)
    except QueryError as e:
        raise click.UsageError(f"Invalid --where expression: {e}")


def _scan_rows(query, joins: set[str]) -> list[dict]:
    """Prime, sleep, scan: one-shot CPU%/IO rates need two samples."""
    import time as _time
    from ptools.lib.proc import sources

    joins = joins | query.required_joins()
    sources.prime(joins)
    _time.sleep(_PRIME_SLEEP_SECS)
    rows = sources.scan(joins)
    return [row for row in rows if query.match(row)]


@click.group(invoke_without_command=True)
@click.option('--where', '-w', default=None, help="Filter expression, e.g. 'cpu>50 & name~node'.")
@click.option('--join', '-j', 'joins', multiple=True, type=click.Choice(_JOIN_CHOICES), help="Enable a data join (repeatable).")
@click.option('--refresh', '-n', type=float, default=2.0, show_default=True, help="TUI refresh interval in seconds.")
@click.option('--tree', '-t', is_flag=True, default=False, help="Start the TUI in tree view.")
@click.pass_context
def cli(ctx, where, joins, refresh, tree):
    """Process explorer: a better ps aux.

    Without a subcommand this opens the live TUI (filters, joins,
    sparklines, kill/renice/suspend/profile actions). Use ``proc list``
    for scriptable output.

    \b
    Example:
      $ ptools proc list --where 'name~definitely-not-running' --top 3
      No matching processes.
    """
    if ctx.invoked_subcommand is not None:
        return
    from ptools.lib.proc.app import launch_proc_app

    launch_proc_app(
        where=where,
        joins=_expand_joins(joins),
        refresh_interval=refresh,
        tree=tree,
    )


@cli.command(name="list")
@click.argument('query_arg', metavar='[WHERE]', required=False, default=None)
@click.option('--where', '-w', default=None, help="Filter expression (combined with the positional one via &).")
@click.option('--join', '-j', 'joins', multiple=True, type=click.Choice(_JOIN_CHOICES), help="Enable a data join (repeatable).")
@click.option('--sort', '-s', type=click.Choice(_SORT_CHOICES), default='cpu', show_default=True)
@click.option('--order', '-o', type=click.Choice(['asc', 'desc']), default='desc', show_default=True)
@click.option('--top', '-n', type=int, default=0, help="Only show the first N rows (0 = all).")
@click.option('--cols', '-c', default=None, help="Comma-separated columns (default: core + join columns).")
@click.option('--raw', is_flag=True, default=False, help="Machine values (bytes/seconds) instead of humanized.")
@click.option('--wizard', is_flag=True, default=False, help="Interactively build the filter expression (field, operator, value).")
@output_flavor.decorate()
def list_processes(query_arg, where, joins, sort, order, top, cols, raw, wizard, flavor):
    """List processes, filtered by a query expression.

    Fields referenced in the query auto-enable the joins that provide
    them, e.g. ``port=3000`` runs the ports join.

    \b
    Example:
      $ ptools proc list --where 'name~definitely-not-running'
      No matching processes.

    \b
      $ ptools proc list 'port=3000 | port=8080' --cols pid,name,ports
      $ ptools proc list 'cpu>50 & user=me' --top 10 --flavor table
      $ ptools proc list 'files~/Users/me/project' --flavor json
      $ ptools proc list --wizard
      ? Field to filter on:
      ❯ CPU%
        MEM
        ...
      # opens the assembled expression in $EDITOR for a last freeform tweak
    """
    from ptools.lib.flow.values import OutputValue

    wizard_expr = _run_filter_wizard() if wizard else None
    if wizard and wizard_expr:
        wizard_expr = _edit_wizard_expression(wizard_expr)
        click.echo(f"Filter: {wizard_expr}")

    expression = " & ".join(f"({part})" for part in [query_arg, where, wizard_expr] if part) or None
    query = _compile(expression)
    joins = _expand_joins(joins) | query.required_joins()
    rows = _scan_rows(query, joins)

    reverse = order == 'desc'
    if sort == 'name':
        rows.sort(key=lambda row: str(row.get('name') or '').lower(), reverse=reverse)
    else:
        rows.sort(key=lambda row: row.get(sort) or 0, reverse=reverse)
    if top > 0:
        rows = rows[:top]

    if not rows:
        click.echo("No matching processes.")
        return

    if cols:
        columns = [c.strip() for c in cols.split(',') if c.strip()]
        unknown = [c for c in columns if c not in FIELD_MAP]
        if unknown:
            raise click.UsageError(f"Unknown column(s): {', '.join(unknown)}")
        columns = [FIELD_MAP[c].key for c in columns]
    else:
        columns = list(_DEFAULT_COLS)
        for join in JOINS:
            if join in joins:
                columns.extend(_JOIN_COLS[join])

    pretty = flavor in (OutputFlavorKind.plain, OutputFlavorKind.table)
    output = [_project(row, columns, humanized=pretty and not raw) for row in rows]
    if pretty:
        from ptools.lib.proc.render import process_table
        _print_renderable(process_table(output, columns))
    else:
        click.echo(OutputValue(flavor=flavor).format(output))


def _print_renderable(renderable) -> None:
    from rich.console import Console

    Console().print(renderable)


def _project(row: dict, columns: list[str], humanized: bool) -> dict:
    import humanize

    projected = {}
    for key in columns:
        value = row.get(key)
        if humanized:
            if key in ('mem', '_mem_sum') and value is not None:
                value = humanize.naturalsize(value, gnu=True)
            elif key in ('io_read', 'io_write'):
                value = f"{humanize.naturalsize(value, gnu=True)}/s" if value is not None else "-"
            elif key == 'age' and value is not None:
                value = humanize.naturaldelta(value)
            elif key == 'cpu' and value is not None:
                value = round(value, 1)
            elif key == 'ports':
                value = ",".join(str(p) for p in (value or []))
            elif key == 'files':
                value = len(value or [])
        projected[key] = value
    return projected


@cli.command(name="info")
@click.argument('pid', type=int)
@output_flavor.decorate()
def info(pid, flavor):
    """Deep-dive on a single PID: cmdline, cwd, open files, connections, env.

    \b
    Example:
      $ ptools proc info 1 --flavor json
      {
        "pid": 1,
        "name": "launchd",
        ...
      }
    """
    import psutil
    from ptools.lib.flow.values import OutputValue
    from ptools.lib.proc import sources

    try:
        detail = sources.process_detail(pid)
    except psutil.NoSuchProcess:
        raise click.ClickException(f"PID {pid} not found.")
    if flavor in (OutputFlavorKind.plain, OutputFlavorKind.table):
        from ptools.lib.proc.render import detail_group
        _print_renderable(detail_group(detail))
    else:
        click.echo(OutputValue(flavor=flavor).format(detail))


@cli.command(name="kill")
@click.argument('pids', nargs=-1, type=int)
@click.option('--where', '-w', default=None, help="Kill every process matching this expression.")
@click.option('--force', '-9', is_flag=True, default=False, help="Send SIGKILL instead of SIGTERM.")
@click.option('--tree', '-t', is_flag=True, default=False, help="Also kill each target's descendants.")
@click.option('--dry-run', '-d', is_flag=True, default=False, help="Show what would be killed without killing.")
@click.option('--yes', '-y', is_flag=True, default=False, help="Skip the confirmation prompt.")
def kill(pids, where, force, tree, dry_run, yes):
    """Kill processes by PID and/or by query expression.

    \b
    Example:
      $ ptools proc kill --where 'name~definitely-not-running' --dry-run
      No matching processes.

    \b
      $ ptools proc kill --where 'port=3000' --dry-run
      $ ptools proc kill 1234 5678 --force
      $ ptools proc kill --where 'name~node & cpu>90' --tree
    """
    import os
    from ptools.lib.proc import actions

    if not pids and not where:
        raise click.UsageError("Give at least one PID or a --where expression.")

    targets: dict[int, str] = {pid: f"pid {pid}" for pid in pids}
    if where:
        query = _compile(where)
        if not query.fields_used and not query.text:
            raise click.UsageError("Refusing an empty --where (it matches every process).")
        for row in _scan_rows(query, set()):
            targets.setdefault(row["pid"], row["name"])

    targets.pop(os.getpid(), None)  # never kill ourselves
    if not targets:
        click.echo("No matching processes.")
        return

    signal_name = "SIGKILL" if force else "SIGTERM"
    for pid, name in sorted(targets.items()):
        prefix = "[dry-run] Would send" if dry_run else "Will send"
        click.echo(f"{prefix} {signal_name} to PID {pid} ({name}){' + subtree' if tree else ''}")
    if dry_run:
        return
    if not yes and not click.confirm(f"Kill {len(targets)} process(es)?"):
        click.echo("Aborted.")
        return

    for pid in sorted(targets):
        try:
            if tree:
                click.echo(actions.kill_tree(pid, force=force))
            else:
                click.echo(actions.terminate(pid, force=force))
        except actions.ActionError as e:
            click.echo(str(e), err=True)
