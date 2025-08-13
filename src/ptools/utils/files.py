import os
import click
import sys

from functools import wraps
from typing import Optional


def resolve_input(allow_stdin=True):
    def decorator(func):
        """
        Decorator that adds --file and INPUT arg, and injects `source_type` and `content`
        into the wrapped function automatically.
        """
        @click.argument('input', required=False)
        @click.option('--file', '-f', 'file_path', help="Path to input file")
        @wraps(func)
        def wrapper(*args, input: Optional[str] = None, file_path: Optional[str] = None, **kwargs):
            # Decide source
            provided = [x is not None for x in (input, file_path)]
            if sum(provided) > 1:
                raise click.UsageError("Provide only one of: string, file path, or stdin.")

            if file_path:
                if not os.path.isfile(file_path):
                    raise click.FileError(file_path, hint="File does not exist.")
                with open(file_path, "r", encoding="utf-8") as f:
                    source_type, content = "file", f.read()

            elif input is not None:
                source_type, content = "string", input

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