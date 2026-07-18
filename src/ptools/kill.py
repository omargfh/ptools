import subprocess

import click


@click.group(name='kill')
def cli():
    """Kill tools.

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


@cli.command(name="process")
@click.argument('process_name', type=str, required=True, nargs=-1)
@click.option('--force', '-9', is_flag=True, default=False, help="Send SIGKILL instead of SIGTERM")
@click.option('--dry-run', '-d', is_flag=True, default=False, help="Show what would be killed without killing")
def kill_process(process_name, force, dry_run):
    """Kill every process matching a name.

    \b
    Example:
      $ ptools kill process definitely-not-running-ptools-example
      No process found with name 'definitely-not-running-ptools-example'.
    """
    import os

    from ptools.lib.proc import actions

    signal_name = "SIGKILL" if force else "SIGTERM"
    had_error = False

    for name in process_name:
        raw_pids = subprocess.run(
            ["pgrep", name], capture_output=True, text=True,
        ).stdout.split()
        pids = [int(p) for p in raw_pids if p.isdigit() and int(p) != os.getpid()]  # never kill ourselves

        if dry_run:
            if not pids:
                click.echo(f"No process found with name '{name}'.")
                continue
            for pid in pids:
                click.echo(f"[dry-run] Would send {signal_name} to PID {pid} ({name}).")
            continue

        if not pids:
            click.echo(f"No process found with name '{name}'.", err=True)
            had_error = True
            continue

        for pid in pids:
            try:
                click.echo(actions.terminate(pid, force=force))
            except actions.ActionError as e:
                click.echo(str(e), err=True)
                had_error = True

    if had_error:
        raise SystemExit(1)
