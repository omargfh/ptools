import subprocess

import click


@click.group(name='kill')
def cli():
    """Kill tools.

    To kill processes by name, use ``ptools proc kill --where 'name~NAME'``.

    \b
    Example:
      $ ptools kill port 9
      No process is listening on port 9.
    """
    pass


def _listening_pids(port: int) -> list[int]:
    """PIDs listening on ``port`` (same selector ``actions.kill_by_port`` uses)."""
    out = subprocess.run(
        ["lsof", "-t", "-i", f":{port}", "-sTCP:LISTEN"],
        capture_output=True, text=True, timeout=10,
    ).stdout
    return [int(p) for p in out.split() if p.isdigit()]


@cli.command(name="port")
@click.argument('port', type=int, required=True, nargs=-1)
@click.option('--force', '-9', is_flag=True, default=False, help="Send SIGKILL instead of SIGTERM")
@click.option('--dry-run', '-d', is_flag=True, default=False, help="Show what would be killed without killing")
def kill_port(port, force, dry_run):
    """Kill every process listening on one or more ports.

    \b
    Example:
      $ ptools kill port 9
      No process is listening on port 9.
    """
    from ptools.lib.proc import actions

    signal_name = "SIGKILL" if force else "SIGTERM"
    had_error = False

    for p in port:
        if dry_run:
            pids = _listening_pids(p)
            if not pids:
                click.echo(f"No process is listening on port {p}.")
                continue
            for pid in pids:
                click.echo(f"[dry-run] Would send {signal_name} to PID {pid} (port {p}).")
            continue

        try:
            click.echo(actions.kill_by_port(p, force=force))
        except actions.ActionError as e:
            click.echo(str(e), err=True)
            had_error = True

    if had_error:
        raise SystemExit(1)
