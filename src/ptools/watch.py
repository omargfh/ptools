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
@click.option('--kill-on-change', '-K', is_flag=True, default=False, help='Kill the running command on file change.')
@click.option('--shell/--no-shell', default=True, help='Run the command in a shell.')
@click.option('--quiet', '-q', is_flag=True, default=False, help='Suppress informational output.')
@click.pass_context
def cli(ctx, path, events, delay, kill_on_change, shell, quiet):
    """Watch for changes and run a command with given arguments after debounce.

    \b
    Example:
      $ ptools watch
      Usage: ptools watch [OPTIONS]
      Try 'ptools watch --help' for help.

      Error: You must pass command arguments after `watch`.

    \b
      $ ptools watch --path /tmp/ptools-doc-examples echo changed
      INFO Watching '/tmp/ptools-doc-examples' for changes...
      INFO Will run: echo changed after 0.5s of no changes.
    """
    if not ctx.args:
        raise click.UsageError("You must pass command arguments after `watch`.")
    command = ctx.args

    if not quiet:
        click.echo(FormatUtils.info(f"Watching '{path}' for changes..."))
        click.echo(FormatUtils.info(f"Will run: {' '.join(command)} after {delay}s of no changes."))

    class DebouncedHandler(FileSystemEventHandler):
        def __init__(self):
            self.timer = None
            self.process = None

        def on_any_event(self, event):
            if event.is_directory:
                return

            if event.event_type not in events.split(','):
                return

            if self.timer:
                self.timer.cancel()

            if kill_on_change and hasattr(self, 'process') and self.process:
                self.process.kill()

            self.timer = threading.Timer(delay, self.run_command)
            self.timer.start()

            if not quiet:
                click.echo(FormatUtils.info(f"Change detected: {event.src_path} - debouncing..."))

        def run_command(self):
            if not quiet:
                click.echo(FormatUtils.info(f"Running command: {' '.join(command)}..."))
            try:
                self.process = subprocess.Popen(command, shell=shell)
                self.process.wait()
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
