import click
from ptools.utils.files import resolve_input
import ptools.utils.require as require

@click.command()
@resolve_input()
@require.library("pyperclip", prompt_install=True)
def cli(source_type, content):
    """Copy input data to clipboard."""
    import pyperclip

    try:
        pyperclip.copy(content)
    except Exception as e:
        click.echo(f"Failed to copy data to clipboard: {e}", err=True)
