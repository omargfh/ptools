
import os
import click

def get_project_root():
    """Get the root directory of the project."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

@click.group()
def cli():
    """developer options for power tools."""
    pass

@cli.command()
def code():
    """Make changes to this tool in VSCode."""
    cmd = f"code {get_project_root()}"
    os.system(cmd)

@cli.command()
def install():
    """(re)install the tool."""
    cmd = f"pip install -e {get_project_root()}"
    os.system(cmd)

@cli.command()
def update():
    """Update the tool to the latest version."""
    cmd = f"git -C {get_project_root()} pull"
    os.system(cmd)

    install()

cli.add_command(code, name="code")
cli.add_command(install, name="install")
cli.add_command(update, name="update")