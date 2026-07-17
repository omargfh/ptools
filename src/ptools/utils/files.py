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


def _get_size(path, ignore_hidden=False, use_cache=True):
    """Uncached implementation of :func:`get_size`.

    ``use_cache`` is threaded through the recursion so a ``use_cache=False``
    call recomputes the whole subtree fresh rather than summing cached child
    sizes (each subdirectory is otherwise its own cache entry).
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
                    total_size += get_size(entry.path, ignore_hidden=ignore_hidden, use_cache=use_cache)
                elif entry.is_file(follow_symlinks=False):
                    total_size += get_size(entry.path, ignore_hidden=ignore_hidden, use_cache=use_cache)
    except PermissionError:
        pass

    return total_size


_get_size_cached = disk_cache(max_cache_age=3600)(_get_size)


def get_size(path, ignore_hidden=False, use_cache=True):
    """Return the total byte size of ``path`` (file or directory tree).

    Results are cached on disk for one hour via :func:`disk_cache`. The
    path is normalized before the cache key is computed, so spellings
    like ``dir`` and ``dir/`` share one cache entry — and a trailing
    slash on a regular file no longer defeats the ``isfile`` check
    (which used to crash with ``NotADirectoryError``).

    :param path: File or directory to measure.
    :param ignore_hidden: Skip dot-files when traversing directories.
    :param use_cache: When ``False``, bypass the disk cache entirely —
        neither reading nor writing it — and recompute the size fresh. The
        bypass propagates through subdirectories, so the whole subtree is
        measured from disk.
    """
    norm = os.path.normpath(path)
    if use_cache:
        return _get_size_cached(norm, ignore_hidden=ignore_hidden)
    return _get_size(norm, ignore_hidden=ignore_hidden, use_cache=False)