
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
@click.option('--pip', default='pip3', help='Path to pip executable.')
def install(pip):
    """(re)install the tool."""
    cmd = f"{pip} install -e {get_project_root()}"
    os.system(cmd)

@cli.command()
def update():
    """Update the tool to the latest version."""
    cmd = f"git -C {get_project_root()} pull"
    os.system(cmd)

    install()

@cli.command()
def push():
    """Commit and push changes to the repository."""
    cmd = f"git -C {get_project_root()} add . && git -C {get_project_root()} commit -m 'Update power tools' && git -C {get_project_root()} push"
    os.system(cmd)
    

cli.add_command(code, name="code")
cli.add_command(install, name="install")
cli.add_command(update, name="update")
cli.add_command(push, name="push")