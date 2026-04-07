"""Developer options for power tools.

The :command:`ptools dev` subcommands wrap the chores you'd otherwise
run by hand from the repo root — (re)installing the tool, opening it in
an editor, building the Sphinx docs, regenerating the full requirements
file, and running the test suite.
"""

import os
import subprocess
import sys

import click

from ptools.settings import PIP_EXECUTABLE

def get_project_root():
    """Get the root directory of the project."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _run(cmd: list[str], *, cwd: str | None = None) -> int:
    """Run ``cmd``, streaming output, and return its exit code.

    Accepts a list (preferred — no shell quoting footguns) and echoes
    the command before running it so the user can see exactly what is
    being executed.
    """
    click.echo(click.style("$ " + " ".join(cmd), fg="cyan"))
    return subprocess.call(cmd, cwd=cwd or get_project_root())


@click.group()
def cli():
    """developer options for power tools."""
    pass

@cli.command()
def root():
    """Print the root directory of the project."""
    click.echo(get_project_root())

@cli.command()
def code():
    """Make changes to this tool in VSCode."""
    cmd = f"code {get_project_root()}"
    os.system(cmd)

@cli.command()
def vim():
    """Make changes to this tool in Vim."""
    cmd = f"vim {get_project_root()}"
    os.system(cmd)

@cli.command()
@click.argument('command', type=str, default='open')
def editor(command):
    """Open the project in the specified editor."""
    cmd = f"{command} {get_project_root()}"
    os.system(cmd)

@cli.command()
@click.option(
    '--extras', '-e', 'extras',
    multiple=True,
    help="Optional dependency group(s) to install (e.g. 'docs'). May be repeated.",
)
def install(extras):
    """(re)install the tool."""
    target = get_project_root()
    if extras:
        target = f"{target}[{','.join(extras)}]"
    _run([*PIP_EXECUTABLE.split(), "install", "-e", target])

@cli.command()
def update():
    """Update the tool to the latest version."""
    cmd = f"git -C {get_project_root()} pull"
    os.system(cmd)

    install.callback()

@cli.command()
@click.option('-m', '--message', default='Update power tools', help='Commit message for the changes.')
def push(message):
    """Commit and push changes to the repository."""
    root_dir = get_project_root()
    if _run(["git", "add", "."], cwd=root_dir) != 0:
        raise click.ClickException("git add failed")
    if _run(["git", "commit", "-m", message], cwd=root_dir) != 0:
        raise click.ClickException("git commit failed")
    if _run(["git", "push"], cwd=root_dir) != 0:
        raise click.ClickException("git push failed")


@cli.command()
@click.option(
    '--builder', '-b', default='html',
    help="Sphinx builder to use (html, dirhtml, linkcheck, ...).",
)
@click.option(
    '--clean', '-c', is_flag=True, default=False,
    help="Remove the existing build output (and autosummary stubs) before building.",
)
@click.option(
    '--open', '-o', 'open_after', is_flag=True, default=False,
    help="Open the built docs in the default browser when the build succeeds.",
)
def docs(builder, clean, open_after):
    """Build the Sphinx documentation under ``docs/``."""
    root_dir = get_project_root()
    source = os.path.join(root_dir, "docs")
    build_dir = os.path.join(source, "_build", builder)

    if not os.path.isdir(source):
        raise click.ClickException(f"docs directory not found: {source}")

    if clean:
        import shutil
        for target in (os.path.join(source, "_build"), os.path.join(source, "api", "generated")):
            if os.path.exists(target):
                click.echo(click.style(f"Removing {target}", fg="yellow"))
                shutil.rmtree(target)

    rc = _run(
        [sys.executable, "-m", "sphinx", "-b", builder, source, build_dir],
        cwd=root_dir,
    )
    if rc != 0:
        raise click.ClickException(
            "sphinx-build failed. Did you install the docs extras? "
            "Try: ptools dev install --extras docs"
        )

    index = os.path.join(build_dir, "index.html")
    click.echo(click.style(f"Docs built at {index}", fg="green"))

    if open_after and os.path.exists(index):
        click.launch(index)


@cli.command(name="requirements")
@click.option(
    '--output', '-o', 'output',
    default='full_requirements.txt',
    show_default=True,
    help="Path (relative to the project root) to write the generated file to. "
         "Pass '-' to stream to stdout instead.",
)
def requirements(output):
    """Regenerate the full requirements file.

    Walks every ``ptools`` submodule so the ``ptools.utils.require``
    decorators announce themselves, then combines what they report with
    the base dependencies declared in ``pyproject.toml``.
    """
    root_dir = get_project_root()
    script = os.path.join(root_dir, "scripts", "generate_requirements.py")
    if not os.path.isfile(script):
        raise click.ClickException(f"generator script not found: {script}")

    cmd = [sys.executable, script]
    if output != '-':
        out_path = output if os.path.isabs(output) else os.path.join(root_dir, output)
        cmd.extend(["--output", out_path])
        rc = _run(cmd, cwd=root_dir)
        if rc == 0:
            click.echo(click.style(f"Wrote {out_path}", fg="green"))
    else:
        rc = _run(cmd, cwd=root_dir)

    if rc != 0:
        raise click.ClickException("requirements generation failed")


@cli.command(
    name="test",
    context_settings=dict(ignore_unknown_options=True, allow_extra_args=True),
)
@click.option('-k', 'keyword', default=None, help="Only run tests matching this keyword expression.")
@click.option('-v', 'verbose', count=True, help="Increase pytest verbosity (repeat for more).")
@click.option('-x', 'exitfirst', is_flag=True, default=False, help="Stop after the first failing test.")
@click.pass_context
def test(ctx, keyword, verbose, exitfirst):
    """Run the test suite with pytest.

    Any unknown arguments are forwarded to pytest unchanged, so e.g.
    ``ptools dev test tests/test_flow.py --lf`` just works.
    """
    cmd = [sys.executable, "-m", "pytest"]
    if keyword:
        cmd.extend(["-k", keyword])
    if verbose:
        cmd.append("-" + "v" * verbose)
    if exitfirst:
        cmd.append("-x")
    cmd.extend(ctx.args)

    rc = _run(cmd)
    if rc != 0:
        raise click.ClickException(f"pytest exited with status {rc}")