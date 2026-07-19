import contextlib
import re
import subprocess
import sys
import click
import json
import os

from prompt_toolkit.output.defaults import create_output

from ptools.lib.tui.select import SelectApp
from ptools.utils.print import FormatUtils

__version__ = "2.0.0"

PROJECT_SRC = os.path.expanduser("~/.ptools/projects.json")

# Embedded in the generated shell function so re-running `install` can tell
# whether the currently-installed block is up to date (see `install()`).
SHELL_FUNCTION_VERSION_MARKER = f"# ptools-project-switcher v{__version__}"

# Matches a previously-installed marker line through to the function's
# closing brace (always alone on its own line in `_SHELL_FUNCTION_BODY`),
# so a stale block can be located and stripped before installing the
# current one.
_VERSION_MARKER_RE = re.compile(
    r"^# ptools-project-switcher v(\S+)\n(?:.*\n)*?^\}[ \t]*\n?",
    re.MULTILINE,
)

# `@cd`: zero args opens the interactive picker, one arg changes directly
# to NAME (optionally with a `NAME/subdir` suffix), and two-or-more args
# pass through unchanged to `ptools projects ...`.
_SHELL_FUNCTION_BODY = """@cd() {
    if [ "$#" -eq 0 ]; then
        cd "$(ptools projects chdir --quiet)"
    elif [ "$#" -eq 1 ]; then
        cd "$(ptools projects chdir "$1" --quiet)"
    else
        ptools projects ${*:1} # pass all arguments except the first to ptools projects
        return $?
    fi
}"""


def _shell_function_snippet() -> str:
    """Build the versioned `@cd` shell function snippet."""
    return f"{SHELL_FUNCTION_VERSION_MARKER}\n{_SHELL_FUNCTION_BODY}"

class ProjectPathMissingError(RuntimeError):
    """A known project's recorded path no longer exists on disk.

    Distinct from an *unknown* project name (which :meth:`Projects.switch`
    signals by returning ``None``, letting the caller fall back to
    treating the name as a literal path): this is a known name whose
    directory has since been deleted, so silently falling back would be
    wrong — the caller should surface a clear error instead of letting
    ``os.chdir`` raise a raw ``FileNotFoundError``.
    """

    def __init__(self, name, path):
        self.name = name
        self.path = path
        super().__init__(f"Project '{name}' points to '{path}', which no longer exists.")


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

    def find_missing_projects(self):
        """Return ``(name, path)`` pairs for projects whose directory no longer exists.

        Shared query behind both the ``prune`` command and the ``chdir``
        picker's broken-entry remediation, so both agree on what counts
        as "missing" without duplicating the check.
        """
        return [
            (name, path)
            for name, path in self.projects.items()
            if not os.path.isdir(path)
        ]

    def remove_missing_projects(self, missing=None):
        """Remove projects whose directory no longer exists; return the removed names.

        Pass a precomputed *missing* list (from :meth:`find_missing_projects`)
        to reuse one a caller already listed for a confirmation prompt,
        otherwise it's computed fresh. Mirrors :meth:`delete_project`'s
        removal shape but saves once for the whole batch rather than once
        per project.
        """
        if missing is None:
            missing = self.find_missing_projects()

        for name, _path in missing:
            del self.projects[name]
        if missing:
            self.save_projects()

        return [name for name, _path in missing]

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
        """Switch to a project by name.

        Returns ``None`` if *name* isn't a known project at all, so the
        caller can fall back to treating it as a literal path. Raises
        :class:`ProjectPathMissingError` if *name* **is** a known project
        but its recorded directory no longer exists — a distinct failure
        mode from an unknown name; collapsing the two would either send
        an unknown-name lookup down the wrong branch or let a dead path
        reach ``os.chdir`` and raise an uncaught ``FileNotFoundError``.
        """
        if name not in self.projects:
            return None
        path = self.projects[name]
        if not os.path.isdir(path):
            raise ProjectPathMissingError(name, path)
        os.chdir(path)
        return path

    def get_projects(self):
        """Get all projects."""
        return self.projects

    def __repr__(self):
        return f"Projects({self.projects})"

    def __str__(self):
        return json.dumps(self.projects, indent=4)

def _handle_broken_project_pick(projects, name, path, output):
    """Offer remediation when the interactive picker's selection is broken.

    Reuses :meth:`Projects.delete_project` for the single-entry case and
    :meth:`Projects.remove_missing_projects` for "prune all" rather than
    reimplementing either. Their own status messages go through
    ``click.echo`` without ``err=True``, so calls to them are wrapped in
    ``redirect_stdout(sys.stderr)`` here: ``chdir`` is normally invoked as
    ``cd "$(ptools projects chdir --quiet)"``, so anything this prints to
    stdout would otherwise land inside the path `cd` receives instead of
    on the user's actual terminal.

    Returns ``True`` if something changed and the picker should be
    re-shown, ``False`` if the user backed out entirely (the whole
    ``chdir`` invocation should then abort with nothing on stdout).
    """
    click.echo(
        FormatUtils.warning(f"Project '{name}' points to '{path}', which no longer exists."),
        err=True,
    )
    choice = SelectApp(
        [
            ("delete", f"Remove just '{name}'"),
            ("prune", "Remove all projects with missing directories"),
            ("cancel", "Cancel"),
        ],
        message="That project's directory is missing. What would you like to do?",
        output=output,
    ).run()

    if choice == "delete":
        with contextlib.redirect_stdout(sys.stderr):
            projects.delete_project(name)
        return True

    if choice == "prune":
        with contextlib.redirect_stdout(sys.stderr):
            removed = projects.remove_missing_projects()
            click.echo(FormatUtils.success(f"Removed {len(removed)} project(s): {', '.join(removed)}"))
        return True

    return False


# Group that doubles as a CLI entry point
@click.group()
def cli():
    """Project management CLI for ptools.

    \b
    Example:
      $ HOME=/tmp/ptools-doc-home ptools projects chdir demo/subdir --quiet
      /private/tmp/ptools-doc-examples/subdir
    """
    pass

@cli.command()
@click.argument('name', required=False)
@click.option('--quiet', is_flag=True, help="Suppress output messages.")
@click.pass_context
def chdir(ctx, name, quiet):
    """Change directory to the project with NAME.

    When NAME is omitted, opens an interactive picker over configured
    projects; entries whose directory no longer exists are marked
    "(missing)" and, if picked, offer to remove just that one or prune
    every broken entry before re-showing the picker.

    \b
    Example:
      $ HOME=/tmp/ptools-doc-home ptools projects chdir demo/subdir --quiet
      /private/tmp/ptools-doc-examples/subdir
    """
    projects = Projects.get_instance()

    if not name:
        # `chdir` is normally invoked as `cd "$(ptools projects chdir --quiet)"`
        # from the installed shell function, so stdout is a pipe, not a
        # terminal. `always_prefer_tty=True` makes prompt_toolkit render the
        # interactive picker to stderr (a real terminal) instead of falling
        # back to a PlainTextOutput that would write raw UI text into the
        # very pipe `click.echo(full_path)` needs to stay clean for below.
        picker_output = create_output(always_prefer_tty=True)

        while True:
            all_projects = projects.get_projects()
            broken = {n for n, p in all_projects.items() if not os.path.isdir(p)}
            options = [
                (
                    proj_name,
                    proj_name,
                    f"{proj_path} (missing)" if proj_name in broken else proj_path,
                )
                for proj_name, proj_path in all_projects.items()
            ]
            picked = SelectApp(
                options, message="Select a project:", output=picker_output
            ).run()
            if not picked:
                ctx.exit(1)

            if picked in broken:
                if _handle_broken_project_pick(projects, picked, all_projects[picked], picker_output):
                    continue
                ctx.exit(1)

            name = picked
            break

    parts = name.split(os.path.sep)
    try:
        path = projects.switch(parts[0]) or parts[0]
    except ProjectPathMissingError as exc:
        click.echo(
            FormatUtils.error(
                f"Project '{exc.name}' points to '{exc.path}', which no longer exists. "
                "Run 'ptools projects prune' to clean it up."
            ),
            err=True,
        )
        ctx.exit(1)

    full_path = os.path.join(path, *parts[1:]) if len(parts) > 1 else path

    click.echo(full_path)

@cli.command(name='list')
def list_projects():
    """List all projects.

    \b
    Example:
      $ HOME=/tmp/ptools-doc-home ptools projects list
      INFO Listing 1 projects:
      Project: demo, Path: /private/tmp/ptools-doc-examples
    """
    projects = Projects.get_instance().get_projects()
    click.echo(FormatUtils.info(f"Listing {FormatUtils.bold(str(len(projects)))} projects:"))
    for name, path in projects.items():
        click.echo(f"Project: {FormatUtils.highlight(name)}, Path: {FormatUtils.highlight(path)}")

@cli.command(name='add')
@click.argument('name')
@click.argument('path', default='.', type=click.Path(exists=True, file_okay=False, resolve_path=True))
@click.option('--force', is_flag=True, help="Force add project even if it already exists.")
def add_project(name, path, force):
    """Add a new project with NAME at PATH.

    \b
    Example:
      $ HOME=/tmp/ptools-doc-home ptools projects add demo /tmp/ptools-doc-examples
      SUCCESS Projects saved to /tmp/ptools-doc-home/.ptools/projects.json.
      SUCCESS Project 'demo' added at /private/tmp/ptools-doc-examples.
    """
    projects = Projects.get_instance()
    projects.add_project(name, path, force)

@cli.command(name='delete')
@click.argument('name')
@click.confirmation_option(prompt='Are you sure you want to delete this project?')
def delete_project(name):
    """Delete the project with NAME.

    \b
    Example:
      $ HOME=/tmp/ptools-doc-home ptools projects delete demo --yes
      SUCCESS Projects saved to /tmp/ptools-doc-home/.ptools/projects.json.
      SUCCESS Project 'demo' deleted.
    """
    projects = Projects.get_instance()
    projects.delete_project(name)

@cli.command()
@click.argument('shellconfigfile', type=click.Path(exists=True, file_okay=True, resolve_path=True))
def install(shellconfigfile):
    """Install the @cd shell function from SHELLCONFIG.

    Re-running this command is idempotent: the generated snippet embeds a
    version marker, so an up-to-date install is left alone and an outdated
    one is replaced in place.

    \b
    Example:
      $ HOME=/tmp/ptools-doc-home ptools projects install /tmp/ptools-doc-home/shellrc
      SUCCESS Installed @cd function to /private/tmp/ptools-doc-home/shellrc.
      SUCCESS Installation completed successfully.
      INFO Please restart your shell or source the configuration file to apply changes.
    """
    try:
        with open(shellconfigfile, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        content = ""

    match = _VERSION_MARKER_RE.search(content)
    if match:
        existing_version = match.group(1)
        if existing_version == __version__:
            click.echo(FormatUtils.info(
                f"@cd function v{__version__} is already installed in {shellconfigfile}."
            ))
            return

        content = _VERSION_MARKER_RE.sub("", content)
        try:
            with open(shellconfigfile, 'w') as f:
                f.write(content)
        except Exception as e:
            click.echo(FormatUtils.error(f"Failed to update @cd function: {e}"))
            raise click.ClickException("Installation failed.")
        click.echo(FormatUtils.info(
            f"Removed outdated @cd function (v{existing_version}) from {shellconfigfile}."
        ))

    try:
        with open(shellconfigfile, 'a') as f:
            f.write(f"\n{_shell_function_snippet()}\n")
        click.echo(FormatUtils.success(f"Installed @cd function to {shellconfigfile}."))
    except Exception as e:
        click.echo(FormatUtils.error(f"Failed to install @cd function: {e}"))
        raise click.ClickException("Installation failed.")
    else:
        click.echo(FormatUtils.success("Installation completed successfully."))
    finally:
        click.echo(FormatUtils.info("Please restart your shell or source the configuration file to apply changes."))

@cli.command()
def prune():
    """Remove projects whose directory no longer exists on disk.

    Lists the affected projects and asks for a single confirmation before
    removing all of them (not one prompt per project).

    \b
    Example:
      $ HOME=/tmp/ptools-doc-home ptools projects prune
      INFO The following projects no longer exist on disk:
      Project: demo, Path: /private/tmp/deleted-project
      Remove these projects? [y/N]: y
      SUCCESS Removed 1 project(s): demo
    """
    projects = Projects.get_instance()
    missing = projects.find_missing_projects()

    if not missing:
        click.echo(FormatUtils.info("No projects to prune; all project directories exist."))
        return

    click.echo(FormatUtils.info("The following projects no longer exist on disk:"))
    for proj_name, proj_path in missing:
        click.echo(f"Project: {FormatUtils.highlight(proj_name)}, Path: {FormatUtils.highlight(proj_path)}")

    click.confirm("Remove these projects?", abort=True)

    removed_names = projects.remove_missing_projects(missing)
    click.echo(FormatUtils.success(f"Removed {len(removed_names)} project(s): {', '.join(removed_names)}"))
