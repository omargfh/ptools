import click
from . import rsync, dev, watch, projects, shell, secrets, json, clip
from ptools.models.default_config import load_default_config

@click.group()
@click.version_option()
def cli():
    """power tools command line interface."""
    pass

cli.add_command(rsync.cli, name="rsync")
cli.add_command(watch.cli, name="watch")
cli.add_command(dev.cli, name="dev")

cli.add_command(projects.cli, name="projects")
cli.add_command(shell.cli, name="shell")
cli.add_command(secrets.cli, name="secrets")

cli.add_command(json.cli, name="json")
cli.add_command(clip.cli, name="clip")
