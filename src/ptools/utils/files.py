"""File-system and input-resolution helpers for ptools commands."""
import os
import click
import sys
import requests

from functools import wraps
from typing import Optional

from ptools.utils.cache import disk_cache

__version__ = "0.1.0"


def resolve_input(allow_stdin=True):
    """Click decorator that resolves an input from positional, ``--file``, ``--url`` or stdin.

    Wrapped commands receive ``source_type`` and ``content`` keyword
    arguments describing where the input came from and its raw text.

    :param allow_stdin: If ``True``, fall back to reading stdin when no
        other source is provided.
    """
    def decorator(func):
        """
        Decorator that adds --file and INPUT arg, and injects `source_type` and `content`
        into the wrapped function automatically.
        """
        @click.argument('input', required=False)
        @click.option('--file', '-f', 'file_path', help="Path to input file")
        @click.option('--url', '-u', 'url', help="URL to fetch input from", required=False)
        @wraps(func)
        def wrapper(*args, input: Optional[str] = None, url, file_path: Optional[str] = None, **kwargs):
            # Decide source
            provided = [x is not None for x in (input, url, file_path)]
            if sum(provided) > 1:
                raise click.UsageError("Provide only one of: string, file path, or stdin.")

            if file_path:
                if not os.path.isfile(file_path):
                    raise click.FileError(file_path, hint="File does not exist.")
                with open(file_path, "r", encoding="utf-8") as f:
                    source_type, content = "file", f.read()

            elif input is not None:
                source_type, content = "string", input

            elif url:
                try:
                    response = requests.get(url)
                    response.raise_for_status()
                    source_type, content = "url", response.text
                except requests.RequestException as e:
                    raise click.ClickException(f"Failed to fetch URL {url}: {e}")

            elif allow_stdin:
                if not sys.stdin.isatty():  # Piped stdin
                    source_type, content = "stdin", sys.stdin.read()
                else:  # Interactive prompt
                    print("Press Ctrl+D (or Ctrl+Z then Enter on Windows) to finish.")
                    stdin_data = "\n".join(sys.stdin.readlines()).strip()
                    if not stdin_data:
                        raise click.UsageError("No input provided.")
                    source_type, content = "stdin", stdin_data
            else:
                raise click.UsageError("No input provided. Use --file or provide input string.")

            # Call original with extra args
            return func(*args, source_type=source_type, content=content, **kwargs)

        return wrapper
    return decorator


@disk_cache(max_cache_age=3600)
def get_size(path, ignore_hidden=False):
    """Return the total byte size of ``path`` (file or directory tree).

    Results are cached on disk for one hour via :func:`disk_cache`.

    :param path: File or directory to measure.
    :param ignore_hidden: Skip dot-files when traversing directories.
    """
    total_size = 0
    if os.path.isfile(path):
        return os.path.getsize(path)

    try:
        with os.scandir(path) as it:
            for entry in it:
                if ignore_hidden and entry.name.startswith('.'):
                    continue
                if entry.is_dir(follow_symlinks=False):
                    total_size += get_size(entry.path, ignore_hidden=ignore_hidden)
                elif entry.is_file(follow_symlinks=False):
                    total_size += get_size(entry.path, ignore_hidden=ignore_hidden)
    except PermissionError:
        pass

    return total_size