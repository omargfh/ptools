import subprocess
import click
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time

from ptools.utils.print import FormatUtils

@click.command(context_settings=dict(ignore_unknown_options=True, allow_extra_args=True))
@click.option('--path', '-p', default='.', help='Directory to watch for changes.')
@click.option('--events', '-e', default='modified,created,deleted', help='Events to watch for (comma-separated).')
@click.option('--delay', default=0.5, help='Debounce delay in seconds.')
@click.pass_context
def cli(ctx, path, events, delay):
    """Watch for changes and run a command with given arguments after debounce."""
    if not ctx.args:
        raise click.UsageError("You must pass command arguments after `watch`.")
    command = ctx.args
    click.echo(FormatUtils.info(f"Watching '{path}' for changes..."))
    click.echo(FormatUtils.info(f"Will run: {' '.join(command)} after {delay}s of no changes."))

    class DebouncedHandler(FileSystemEventHandler):
        def __init__(self):
            self.timer = None

        def on_any_event(self, event):
            if event.is_directory:
                return

            if event.event_type not in events.split(','):
                return

            if self.timer:
                self.timer.cancel()

            self.timer = threading.Timer(delay, self.run_command)
            self.timer.start()

            click.echo(FormatUtils.info(f"Change detected: {event.src_path} — debouncing..."))

        def run_command(self):
            click.echo(FormatUtils.info(f"Running command: {' '.join(command)}..."))
            try:
                subprocess.run(command, check=True)
            except subprocess.CalledProcessError as e:
                click.echo(FormatUtils.error(f"Command failed: {e}"), err=True)

    import threading
    observer = Observer()
    observer.schedule(DebouncedHandler(), path=path, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        click.echo("Stopping watcher...")
        observer.stop()
    observer.join()