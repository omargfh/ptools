import subprocess
import time

import click

from ptools.utils.parsers import parse_human_time
from ptools.utils.print import FormatUtils as fmt
from ptools.settings import SHELL_EXECUTABLE


@click.command(context_settings={"ignore_unknown_options": True})
@click.argument("interval", type=str)
@click.argument("command", type=str, nargs=-1, required=True)
@click.option("--shell/--no-shell", default=True, help="Run command in shell.")
@click.option("--shell-path", default=SHELL_EXECUTABLE, show_default=True)
def every(interval: str, command: tuple[str, ...], shell: bool, shell_path: str) -> None:
    """Run a command at regular intervals.

    \b
    Example:
        $ ptools every 5s echo 'Hello, World!'
        $ ptools every 2m python my_script.py
        $ ptools every 1h -- docker-compose up
    """
    try:
        seconds = parse_human_time(interval)
    except ValueError as e:
        raise click.BadParameter(fmt.error(str(e)), param_hint="INTERVAL")

    if seconds <= 0:
        raise click.BadParameter(
            fmt.error("Interval must be positive."), param_hint="INTERVAL"
        )

    if command[0] == "--":
        command = command[1:]

    try:
        while True:
            subprocess.run(" ".join(command), shell=shell, executable=shell_path)
            time.sleep(seconds)
    except KeyboardInterrupt:
        click.echo(fmt.warning("Stopped by user."))