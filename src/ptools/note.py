import re
from ast import pattern
import sys
import os

import click
import humanize
from functools import partial, wraps
from datetime import datetime

from ptools.utils.files import get_extension
from ptools.utils.file_storage import FileStorageClient
from ptools.utils.print import FormatUtils as fmt

client = FileStorageClient("notes")


def _slug(text: str, fallback: str = "note") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.strip().lower()).strip("-")
    return slug[:40] or fallback


def _read_body(initial: str = "", extension: str = ".md") -> str | None:
    """Editor when attached to a terminal, stdin otherwise. ``None`` if empty."""
    if sys.stdin.isatty():
        body = click.edit(initial, extension=extension)
        if body is None:  # editor closed without saving
            return None
    else:
        body = sys.stdin.read()
    body = body.rstrip("\n")
    return body + "\n" if body.strip() else None


def _pick(message: str) -> str | None:
    """Interactive picker over stored notes; usage error off a terminal."""
    if not sys.stdin.isatty():
        raise click.UsageError("NAME is required when not running interactively.")
    from prompt_toolkit.output.defaults import create_output
    from ptools.lib.tui.select import select

    names = client.list_objects()
    if not names:
        click.echo(fmt.warning("No notes yet."), err=True)
        return None
    rows = [(n, n, _preview(n)) for n in names]
    return select(rows, message, output=create_output(always_prefer_tty=True))


def _preview(name: str, width: int = 32) -> str:
    text = client.get_object(name) or ""
    text = " ".join(text.split("\n")[0].split())
    return fmt.truncate(text, width, truncate_middle=False)


def _resolve(name: str | None, message: str) -> str:
    """Return a stored note name, prompting when *name* is omitted."""
    if name is None:
        name = _pick(message)
        if name is None:
            sys.exit(1)
    if not client.exists(name):
        raise click.UsageError(f"No note named '{name}'. Try 'ptools note ls'.")
    return name


@click.group(invoke_without_command=True, name="note")
@click.option("-n", "--name", help="Name to save the new note under (skips the prompt).")
@click.pass_context
def cli(ctx, name):
    """Take notes and manage them. With no subcommand, create a new note."""
    if ctx.invoked_subcommand is not None:
        return

    body = _read_body()
    if body is None:
        click.echo(fmt.warning("Empty note, nothing saved."), err=True)
        sys.exit(1)

    if name is None:
        if not sys.stdin.isatty():
            raise click.UsageError("--name is required when the note comes from stdin.")
        name = click.prompt("Save as", default=_slug(body.splitlines()[0]))

    if client.exists(name) and not click.confirm(f"'{name}' exists. Overwrite?"):
        sys.exit(1)

    path = client.put_object(name, body)
    click.echo(fmt.success(f"Saved '{name}' ({path})"))


@cli.command(name="ls")
@click.argument("prefix", default="")
@click.option("-p", "--path", is_flag=True, help="Show the file path of each note.")
@click.option("-l", "--long", is_flag=True, help="Show detailed information for each note.")
@click.option("-h", "--humanize", "is_humanize", is_flag=True, help="Show human-readable file sizes.")
def list_notes(prefix, path, long, is_humanize):
    """List notes, optionally filtered by PREFIX."""
    names = client.list_objects(prefix)
    if not names:
        click.echo(fmt.warning("No notes found."), err=True)
        sys.exit(1)
    width = max(len(n) for n in names)
    for n in names:
        line = f"{n.ljust(width)}"
        if path:
            line += f"  ~/{client.get_file_path(n).relative_to(os.path.expanduser('~'))}".ljust(36)
        if long:
            # Example of long info: size in bytes
            file_path = client.get_file_path(n)
            if os.path.exists(file_path):
                if is_humanize:
                    line += f"  {humanize.naturalsize(os.path.getsize(file_path))}"
                else:
                    line += f"  {os.path.getsize(file_path)}"
                # date
                line += f"  {humanize.naturaldate(datetime.fromtimestamp(os.path.getmtime(file_path)))}".ljust(10)
        line += f"  {fmt.bold(fmt.highlight(_preview(n), 'cyan'))}"
        click.echo(line)


@cli.command(name="cat")
@click.argument("name", required=False)
def cat_note(name):
    """Print a note."""
    name = _resolve(name, "Select a note:")
    click.echo(client.get_object(name), nl=False)


@cli.command(name="edit")
@click.argument("name", required=False)
def edit_note(name):
    """Open a note in $EDITOR."""
    name = _resolve(name, "Select a note to edit:")
    content = client.get_object(name)
    if content is None:
        content = ""

    body = _read_body(content, extension=get_extension(name, fallback=".md"))
    if body is None:
        click.echo(fmt.warning("No changes."), err=True)
        return
    client.put_object(name, body)
    click.echo(fmt.success(f"Updated '{name}'"))


@cli.command(name="rm")
@click.argument("name", required=False)
@click.option("-y", "--yes", is_flag=True, help="Skip confirmation.")
def remove_note(name, yes):
    """Delete a note."""
    name = _resolve(name, "Select a note to delete:")
    if not yes:
        click.confirm(f"Delete '{name}'?", abort=True)
    client.delete_object(name)
    click.echo(fmt.success(f"Deleted '{name}'"))


@cli.command(name="path")
@click.argument("name", required=False)
def note_path(name):
    """Print the file path of a note (for use in $( ... ))."""
    name = _resolve(name, "Select a note:")
    click.echo(client.get_file_path(name))


@cli.command(name="run", context_settings={"ignore_unknown_options": True})
@click.argument("name")
@click.argument("command", nargs=-1, required=True, type=click.UNPROCESSED)
def run_on_note(name, command):
    """Run COMMAND with the note's path appended, no shell involved.

    \b
    Example:
      $ ptools note run todo -- wc -l
    """
    name = _resolve(name, "Select a note:")
    sys.exit(subprocess.call([*command, str(client.get_file_path(name))]))