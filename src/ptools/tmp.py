import click
from ptools.utils.print import FormatUtils as fmt
from ptools.settings import PTOOLS_DEBUG

@click.command(name="tmp", help="Temporary command for testing purposes.")
@click.argument("command", type=str, nargs=-1, required=True, metavar="COMMAND")
def tmp(command):
    """Temporary command for testing purposes.

    \b
    Example:
      $ ptools tmp code         // Run the 'code' command in a temporary directory
      $ ptools tmp ls -l        // Run the 'ls -l' command in a temporary directory
      $ ptools tmp "echo {}"    // Run the 'echo {}' command in a temporary directory, replacing '{}' with the temp dir path
    """
    import subprocess
    import tempfile

    tmpdir = tempfile.mkdtemp(prefix="ptools-")

    command = " ".join(command)
    command = command.replace("{}", tmpdir) if "{}" in command else " ".join([command, tmpdir])

    if PTOOLS_DEBUG:
        click.echo(fmt.info(f"Temporary directory created at: {tmpdir}"))
        click.echo(fmt.info(f"Executing command: {command}"))

    result = subprocess.run(command, shell=True, cwd=tmpdir, capture_output=True, text=True)

    if result.stderr:
        click.echo(fmt.error(f"Error executing command: {result.stderr}"), err=True)