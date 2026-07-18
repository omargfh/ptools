"""Developer options for power tools.

The :command:`ptools dev` subcommands wrap the chores you'd otherwise
run by hand from the repo root - (re)installing the tool, opening it in
an editor, building the Sphinx docs, regenerating the full requirements
file, and running the test suite.
"""

import importlib
import importlib.util
import os
import pkgutil
import shutil
import subprocess
import sys

import click

from ptools.settings import EDITOR, PIP_EXECUTABLE

def get_project_root():
    """Get the root directory of the project."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _run(cmd: list[str], *, cwd: str | None = None) -> int:
    """Run ``cmd``, streaming output, and return its exit code.

    Accepts a list (preferred - no shell quoting footguns) and echoes
    the command before running it so the user can see exactly what is
    being executed.
    """
    click.echo(click.style("$ " + " ".join(cmd), fg="cyan"))
    return subprocess.call(cmd, cwd=cwd or get_project_root())


@click.group()
def cli():
    """developer options for power tools.

    \b
    Example:
      $ ptools dev root
      /Users/pas6148/Documents/sdk/ptools
    """
    pass

@cli.command()
def root():
    """Print the root directory of the project.

    \b
    Example:
      $ ptools dev root
      /Users/pas6148/Documents/sdk/ptools
    """
    click.echo(get_project_root())

@cli.command()
@click.option('--target', '-t', type=click.Choice(['project', 'config']), default='project', help="Which file to open: the project root or the config file.")
def edit(target):
    """Make changes to this tool in your configured editor.

    Uses the ``EDITOR`` setting (env var, ``~/.ptools/settings.json``, or
    the ``vim`` default - see ``ptools settings``).

    \b
    Example:
      $ ptools dev edit
      # Opens /Users/pas6148/Documents/sdk/ptools in $EDITOR; no stdout on success.
    """

    # os.system (shell) is intentional here, mirroring the `vim`/`editor`
    # commands below in this same file: EDITOR is a locally-configured
    # setting (not untrusted request input) and the target is one of two
    # fixed local paths, so this isn't a new command-injection surface.
    match target:
        case 'project':
            os.system(f"{EDITOR} {get_project_root()}")
        case 'config':
            os.system(f"{EDITOR} {os.path.join(os.path.expanduser('~'), '.ptools')}")

@cli.command()
def vim():
    """Make changes to this tool in Vim.

    \b
    Example:
      $ ptools dev vim
      # Opens /Users/pas6148/Documents/sdk/ptools in Vim.
    """
    cmd = f"vim {get_project_root()}"
    os.system(cmd)

@cli.command()
@click.argument('command', type=str, default='open')
def editor(command):
    """Open the project in the specified editor.

    \b
    Example:
      $ ptools dev editor open
      # Runs: open /Users/pas6148/Documents/sdk/ptools
    """
    cmd = f"{command} {get_project_root()}"
    os.system(cmd)

@cli.command()
@click.option(
    '--extras', '-e', 'extras',
    multiple=True,
    help="Optional dependency group(s) to install (e.g. 'docs'). May be repeated.",
)
def install(extras):
    """(re)install the tool.

    \b
    Example:
      $ ptools dev install --extras docs
      $ uv pip install -e /Users/pas6148/Documents/sdk/ptools[docs]
      ...
    """
    target = get_project_root()
    if extras:
        target = f"{target}[{','.join(extras)}]"
    _run([*PIP_EXECUTABLE.split(), "install", "-e", target])

@cli.command()
def update():
    """Update the tool to the latest version.

    \b
    Example:
      $ ptools dev update
      # Runs git pull, then reinstalls the editable package.
    """
    cmd = f"git -C {get_project_root()} pull"
    os.system(cmd)

    install.callback()

@cli.command()
@click.option('-m', '--message', default='Update power tools', help='Commit message for the changes.')
def push(message):
    """Commit and push changes to the repository.

    \b
    Example:
      $ ptools dev push --message 'Update docs'
      $ git add .
      $ git commit -m Update docs
      $ git push
    """
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
    """Build the Sphinx documentation under ``docs/``.

    \b
    Example:
      $ ptools dev docs --builder html
      $ /Users/pas6148/Documents/sdk/ptools/.venv/bin/python -m sphinx -b html /Users/pas6148/Documents/sdk/ptools/docs /Users/pas6148/Documents/sdk/ptools/docs/_build/html
      Docs built at /Users/pas6148/Documents/sdk/ptools/docs/_build/html/index.html
    """
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

    \b
    Example:
      $ ptools dev requirements --output -
      $ /Users/pas6148/Documents/sdk/ptools/.venv/bin/python /Users/pas6148/Documents/sdk/ptools/scripts/generate_requirements.py
      click>=8.1
      watchdog>=3.0
      ...
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


def _import_all_ptools_submodules() -> list[tuple[str, str]]:
    """Import every submodule under :mod:`ptools`.

    Mirrors the walk in ``scripts/generate_requirements.py``: importing
    each module is enough to make every ``@require.*`` decorator fire
    and register itself into
    :func:`ptools.utils.require.announced_requirements`. Returns
    ``(module_name, error_message)`` pairs for modules that failed to
    import, so ``doctor`` can flag that its report may be incomplete.
    """
    import ptools

    failures: list[tuple[str, str]] = []
    for module_info in pkgutil.walk_packages(ptools.__path__, prefix="ptools."):
        try:
            importlib.import_module(module_info.name)
        except Exception as exc:  # noqa: BLE001
            failures.append((module_info.name, f"{type(exc).__name__}: {exc}"))
    return failures


@cli.command(name="doctor")
def doctor():
    """Report which optional libraries/binaries/API keys are satisfied.

    Imports every ``ptools`` submodule so all ``@require.*`` decorators
    announce themselves into
    :func:`ptools.utils.require.announced_requirements`, then re-checks
    each announced requirement against the current environment. Missing
    libraries or binaries make this command exit non-zero, so it's
    scriptable (e.g. in CI or a pre-flight check). Announced API keys
    are listed for awareness but cannot be verified generically - the
    registry only records the key's name/aliases, not which store(s)
    the declaring command resolves it from - so they never affect the
    exit code. Makes no installation attempt and no network access.

    \b
    Example:
      $ ptools dev doctor
      Libraries:
        [ok]      click
        [MISSING] openai (pip install openai)
      Binaries:
        [ok]      git
      Operating system:
        [ok]      darwin
      API keys (cannot verify generically; check manually):
        - OPENAI_API_KEY (aliases: OPENAI_API_KEY)
      Error: 1 requirement(s) missing; see above.
    """
    import platform

    from ptools.utils.enums import LogicalOperators
    from ptools.utils.require import (
        BinaryRequirement,
        KeyRequirement,
        LibraryRequirement,
        OSRequirement,
        announced_requirements,
    )

    import_failures = _import_all_ptools_submodules()

    announced = announced_requirements()
    # Dedup while preserving first-seen order; the same requirement is
    # commonly announced by more than one module (e.g. several commands
    # each requiring 'pyperclip'). Libraries are deduped by module name
    # alone (first announcement wins) since availability only depends
    # on the module - two announcements can differ in pypi_name/
    # prompt_install (e.g. 'pygments' is both an optional_library and a
    # hard require.library elsewhere) without being distinct checks.
    seen_modules: dict[str, LibraryRequirement] = {}
    for req in announced:
        if isinstance(req, LibraryRequirement) and req.module not in seen_modules:
            seen_modules[req.module] = req
    library_reqs = list(seen_modules.values())

    binary_reqs = list(dict.fromkeys(
        req for req in announced if isinstance(req, BinaryRequirement)
    ))
    key_reqs = list(dict.fromkeys(
        req for req in announced if isinstance(req, KeyRequirement)
    ))
    os_reqs = list(dict.fromkeys(
        req for req in announced if isinstance(req, OSRequirement)
    ))

    missing_count = 0

    click.echo(click.style("Libraries:", bold=True))
    if not library_reqs:
        click.echo("  (none announced)")
    for req in sorted(library_reqs, key=lambda r: r.module):
        if importlib.util.find_spec(req.module) is not None:
            click.echo(f"  {click.style('[ok]', fg='green')}      {req.module}")
        else:
            missing_count += 1
            click.echo(
                f"  {click.style('[MISSING]', fg='red')} {req.module} "
                f"(pip install {req.pip_name})"
            )

    click.echo(click.style("Binaries:", bold=True))
    if not binary_reqs:
        click.echo("  (none announced)")
    for req in sorted(binary_reqs, key=lambda r: r.names):
        found = [shutil.which(name) is not None for name in req.names]
        satisfied = LogicalOperators(req.logical_operator).apply(found)
        joined = f" {req.logical_operator.upper()} ".join(req.names)
        if satisfied:
            click.echo(f"  {click.style('[ok]', fg='green')}      {joined}")
        else:
            missing_count += 1
            click.echo(f"  {click.style('[MISSING]', fg='red')} {joined}")

    click.echo(click.style("Operating system:", bold=True))
    if not os_reqs:
        click.echo("  (none announced)")
    current_os = platform.system().lower()
    for req in sorted(os_reqs, key=lambda r: r.names):
        matches = [current_os == name.lower() for name in req.names]
        satisfied = LogicalOperators(req.logical_operator).apply(matches)
        joined = f" {req.logical_operator.upper()} ".join(req.names)
        if satisfied:
            click.echo(f"  {click.style('[ok]', fg='green')}      {joined}")
        else:
            missing_count += 1
            click.echo(f"  {click.style('[MISSING]', fg='red')} {joined}")

    click.echo(click.style("API keys (cannot verify generically; check manually):", bold=True))
    if not key_reqs:
        click.echo("  (none announced)")
    for req in sorted(key_reqs, key=lambda r: r.name):
        click.echo(f"  - {req.name} (aliases: {', '.join(req.aliases)})")

    if import_failures:
        click.echo(click.style("Modules that failed to import (report may be incomplete):", fg="yellow"))
        for name, error in import_failures:
            click.echo(f"  - {name}: {error}")

    if missing_count:
        raise click.ClickException(f"{missing_count} requirement(s) missing; see above.")
    click.echo(click.style("All checked requirements are satisfied.", fg="green"))


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

    \b
    Example:
      $ ptools dev test tests/test_time.py
      $ /Users/pas6148/Documents/sdk/ptools/.venv/bin/python -m pytest tests/test_time.py
      ...
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
