import click
from . import rsync, dev, watch

@click.group()
def cli():
    """power tools command line interface."""
    pass

cli.add_command(rsync.cli, name="rsync")
cli.add_command(watch.cli, name="watch")
cli.add_command(dev.cli, name="__dev")