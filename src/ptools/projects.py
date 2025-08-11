import subprocess
import click
import json
import os 

from ptools.utils.print import FormatUtils

PROJECT_SRC = os.path.expanduser("~/.ptools/projects.json")

projectsInstance = None
class Projects():
    """Class to manage projects in ptools."""
    def __init__(self):
        self.projects = None
        self.projects = self.initialize_projects()

    @staticmethod
    def get_instance():
        global projectsInstance
        if projectsInstance is None:
            projectsInstance = Projects()
        return projectsInstance

    def initialize_projects(self):
        """Initialize projects from the JSON file."""
        if self.projects is not None:
            return self.projects
    
        try:
            with open(PROJECT_SRC, 'r') as f:
                self.projects = json.load(f)
        except FileNotFoundError:
            click.echo(FormatUtils.error(f"Projects file not found: {PROJECT_SRC}"))
            click.echo(FormatUtils.info(f"Creating a new projects file at {PROJECT_SRC}"))

            if not os.path.exists(os.path.dirname(PROJECT_SRC)):
                os.mkdir(os.path.dirname(PROJECT_SRC))

            with open(PROJECT_SRC, 'w') as f:
                json.dump({}, f, indent=4)

            self.projects = {}

            return self.projects
        except json.JSONDecodeError:
            msg = f"Error decoding JSON from {PROJECT_SRC}. Please check the file format."
            click.echo(FormatUtils.error(msg))
            raise click.ClickException(msg)
        except Exception as e:
            click.echo(FormatUtils.error(f"An unexpected error occurred: {e}"))
            raise click.ClickException("Failed to initialize projects.")

        return self.projects

    def add_project(self, name, path, force=False):
        """Add a new project."""
        if name in self.projects and not force:
            click.echo(FormatUtils.error(f"Project '{name}' already exists. Use --force to overwrite."))
            return
        
        self.projects[name] = os.path.abspath(path)
        self.save_projects()
        click.echo(FormatUtils.success(f"Project '{name}' added at {path}."))
        return self.projects

    def delete_project(self, name):
        """Delete a project by name."""
        if name not in self.projects:
            click.echo(FormatUtils.error(f"Project '{name}' does not exist."))
            return
        
        del self.projects[name]
        self.save_projects()
        click.echo(FormatUtils.success(f"Project '{name}' deleted."))
        return self.projects
    
    def save_projects(self):
        """Save projects to the JSON file."""
        try:
            with open(os.path.expanduser(PROJECT_SRC), 'w') as f:
                json.dump(self.projects, f, indent=4)
            click.echo(FormatUtils.success(f"Projects saved to {PROJECT_SRC}."))
        except Exception as e:
            click.echo(FormatUtils.error(f"Failed to save projects: {e}"))
            raise click.ClickException("Failed to save projects.")

    def switch(self, name):
        """Switch to a project by name."""
        if name not in self.projects:
            click.echo(FormatUtils.error(f"Project '{name}' does not exist."))
            return
        
        path = self.projects[name]
        os.chdir(path)
        return path
    
    def get_projects(self):
        """Get all projects."""
        return self.projects

    def __repr__(self):
        return f"Projects({self.projects})"

    def __str__(self):
        return json.dumps(self.projects, indent=4)

# Group that doubles as a CLI entry point
@click.group()
def cli():
    """Project management CLI for ptools."""
    pass
    
@cli.command()
@click.argument('name')
@click.option('--quiet', is_flag=True, help="Suppress output messages.")
def chdir(name, quiet):
    """Change directory to the project with NAME."""
    projects = Projects.get_instance()
    path = projects.switch(name)
    if path:
        if not quiet:
            click.echo(FormatUtils.success(f"Changed directory to {path}"))
        else:
            click.echo(path)
    else:
        click.echo(FormatUtils.error(f"Failed to change directory to project '{name}'."))

@cli.command()
def list_projects():
    """List all projects."""
    projects = Projects.get_instance().get_projects()
    click.echo(FormatUtils.info(f"Listing {FormatUtils.bold(len(projects))} projects:"))
    for name, path in projects.items():
        click.echo(f"Project: {FormatUtils.highlight(name)}, Path: {FormatUtils.highlight(path)}")

@cli.command()
@click.argument('name')
@click.argument('path', default='.', type=click.Path(exists=True, file_okay=False, resolve_path=True))
@click.option('--force', is_flag=True, help="Force add project even if it already exists.")
def add_project(name, path, force):
    """Add a new project with NAME at PATH."""
    projects = Projects.get_instance()
    projects.add_project(name, path, force)

@cli.command()
@click.argument('name')
@click.confirmation_option(prompt='Are you sure you want to delete this project?')
def delete_project(name):
    """Delete the project with NAME."""
    projects = Projects.get_instance()
    projects.delete_project(name)

@cli.command()
@click.argument('shellconfigfile', type=click.Path(exists=True, file_okay=True, resolve_path=True))
def install(shellconfigfile):
    """Install the shell configuration from SHELLCONFIG."""
    fn = """pcd() {
    cd "$(ptools projects chdir "$1" --quiet)"
}"""

    try:
        with open(shellconfigfile, 'a') as f:
            f.write(f"\n{fn}\n")
        click.echo(FormatUtils.success(f"Installed pcd function to {shellconfigfile}."))
    except Exception as e:
        click.echo(FormatUtils.error(f"Failed to install pcd function: {e}"))
        raise click.ClickException("Installation failed.")
    else:
        click.echo(FormatUtils.success("Installation completed successfully."))
    finally:
        click.echo(FormatUtils.info("Please restart your shell or source the configuration file to apply changes."))

cli.add_command(chdir, name='chdir')
cli.add_command(add_project, name='add')
cli.add_command(list_projects, name='list')
cli.add_command(delete_project, name='delete')
cli.add_command(install, name='install')