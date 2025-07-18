import subprocess
import click
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time

###################################
######### CLICK COMMANDS ##########
###################################
@click.group()
def cli():
    """rsync power tools."""
    pass

@click.command(context_settings=dict(ignore_unknown_options=True, allow_extra_args=True))
@click.pass_context
def do(ctx):
    """Defer to rsync with arbitrary arguments."""
    if not ctx.args:
        raise click.UsageError("You must pass arguments to rsync after `do`.")

    rsync_cmd = ["rsync"] + ctx.args
    click.echo(f"Running: {' '.join(rsync_cmd)}")

    try:
        subprocess.run(rsync_cmd, check=True)
    except subprocess.CalledProcessError as e:
        click.echo(f"rsync failed: {e}", err=True)

@click.command(context_settings=dict(ignore_unknown_options=True, allow_extra_args=True))
@click.option('--path', '-p', default='.', help='Directory to watch for changes.')
@click.option('--delay', default=0.5, help='Debounce delay in seconds.')
@click.pass_context
def watch(ctx, path, delay):
    """Watch for changes and run rsync with given arguments after debounce."""
    if not ctx.args:
        raise click.UsageError("You must pass rsync arguments after `watch`.")
    rsync_cmd = ["rsync"] + ctx.args
    click.echo(f"Watching '{path}' for changes...")
    click.echo(f"Will run: {' '.join(rsync_cmd)} after {delay}s of no changes.")

    class DebouncedHandler(FileSystemEventHandler):
        def __init__(self):
            self.timer = None

        def on_any_event(self, event):
            if event.is_directory:
                return

            if self.timer:
                self.timer.cancel()

            self.timer = threading.Timer(delay, self.run_rsync)
            self.timer.start()
            click.echo(f"Change detected: {event.src_path} — debouncing...")

        def run_rsync(self):
            click.echo("Running rsync...")
            try:
                subprocess.run(rsync_cmd, check=True)
            except subprocess.CalledProcessError as e:
                click.echo(f"rsync failed: {e}", err=True)

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

cli.add_command(do, name="do")
cli.add_command(watch, name="watch")