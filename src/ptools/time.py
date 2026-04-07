"""Timing utilities.

Exposes the :command:`ptools time` CLI for measuring command execution
time. The :command:`ptools time it` subcommand runs an arbitrary shell
command one or more times and reports statistics (mean, median,
standard deviation, min, max, mode, and/or individual samples) over the
collected timings.
"""

from time import time
import click


STAT_CHOICES = ['each', 'mean', 'mode', 'median', 'stddev', 'min', 'max']
"""Statistics accepted by :option:`ptools time it --stats`."""


def fmt_time(x: float) -> str:
    """Format a duration in seconds as a human-readable string.

    Durations under one second are rendered in milliseconds with three
    decimal places; longer durations are rendered in seconds.

    :param x: Duration in seconds.
    :returns: Formatted duration string, e.g. ``"12.345 ms"`` or
        ``"1.234 seconds"``.
    """
    return f"{x * 1000:.3f} ms" if x < 1 else f"{x:.3f} seconds"


@click.group()
def cli():
    """Timing utilities for power tools."""
    pass


@cli.command()
@click.option('--repeat', '-r', default=1, help='Number of times to repeat the command')
@click.option(
    '--stats', '-s',
    multiple=True,
    type=click.Choice(STAT_CHOICES, case_sensitive=False),
    default=['mean'],
    help='Statistics to compute',
)
@click.argument('command', type=str, default='ptools --help', nargs=-1, metavar='COMMAND')
def it(repeat, stats, command):
    """Time the execution of a command and compute statistics."""
    import json
    import subprocess

    import numpy as np
    from ptools.utils.print import ProgressBar, ProgressBarOptions

    my_start = time()
    command = ' '.join(command) if command else 'ptools --help'

    STAT_FNS = {
        'mean':   np.mean,
        'median': np.median,
        'stddev': np.std,
        'min':    np.min,
        'max':    np.max,
    }

    progress = ProgressBar(
        repeat, prefix="Executing: ", suffix="...",
        options=ProgressBarOptions(length=50, show_percentage=True),
    )

    try:
      times = []
      for i in range(repeat):
          progress.update(i + 1)
          start = time()
          subprocess.run(command, shell=True, check=True, capture_output=True)
          end = time()
          times.append(end - start)
    except subprocess.CalledProcessError as e:
        click.echo(f"Command failed with exit code {e.returncode}", err=True)
        click.echo(f"Error output: {e.stderr.decode()}", err=True)
        return
    except KeyboardInterrupt:
        click.echo("\nTiming interrupted by user.", err=True)
        return
    finally:
      progress.complete()
      progress.join()

    times = np.array(times)
    results = {}

    if 'each' in stats:
        results['each'] = [fmt_time(t) for t in times]
    if 'mode' in stats:
        results['mode'] = fmt_time(
            float(np.bincount((times * 1000).astype(int)).argmax()) / 1000
        )
    for key, fn in STAT_FNS.items():
        if key in stats:
            results[key] = fmt_time(fn(times))

    my_time = time() - my_start
    results['execution_time'] = fmt_time(my_time)

    click.echo(json.dumps(results, indent=2))