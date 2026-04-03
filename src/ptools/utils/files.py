import os
import click
import sys
import requests

from functools import wraps, lru_cache
from typing import Optional

def resolve_input(allow_stdin=True):
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

class KnownExtensions:
    IMAGE   = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.avif', '.webp', '.tiff', '.ico', '.heic'}
    VIDEO   = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm', '.mpeg'}
    AUDIO   = {'.mp3', '.wav', '.ogg', '.flac', '.aac', '.m4a', '.opus', '.alac', '.wma', '.aiff'}
    BOOK    = {'.pdf', '.epub', '.mobi', '.azw3', '.fb2', '.djvu', '.cbz', '.cbr'}

    CONFIG  = {'.json', '.yaml', '.yml', '.ini', '.cfg', '.toml', '.env', '.xml', '.csv', '.tsv'}
    BINARY  = {'.bin', '.exe', '.dll', '.so',
               '.dylib', '.zip',
               '.tar', '.gz', '.7z', '.rar', '.bz2',
               '.xz', '.msi', '.deb', '.rpm', '.apk', '.jar',
               '.pyc', '.pyo', '.class', '.o', '.obj', '.elf',
               '.AppImage'}
    DISC    = {'.iso', '.img', '.dmg', '.vmdk', '.qcow2', '.box', '.vhd', '.vhdx'}
    KEY     = {'.pem', '.key', '.csr', '.crt', '.cer', '.pfx', '.p12'}
    SYMLINK = {'.lnk', '.symlink', '.shortcut'}

    ICONS  = {
        "FILE": '📄',
        "IMAGE": '🖼️',
        "VIDEO": '🎬',
        "AUDIO": '🎵',
        "BOOK": '📚',
        "CONFIG": '⚙️',
        "BINARY": '📦',
        "DISC": '💿',
        "KEY": '🔑',
        "SYMLINK": '🔗',
        "FOLDER_CLOSED": '📁',
        "FOLDER_OPEN": '📂',
        "UNKNOWN": '❓',
        "DEFAULT": '📄',
    }

    @staticmethod
    def get_icon(extension: str | None, is_dir=False, is_symlink=False, has_children=False) -> str:
        if is_symlink:
            return KnownExtensions.ICONS["SYMLINK"]
        elif is_dir and has_children:
            return KnownExtensions.ICONS["FOLDER_OPEN"]
        elif is_dir:
            return KnownExtensions.ICONS["FOLDER_CLOSED"]

        if not extension:
            return KnownExtensions.ICONS["UNKNOWN"]

        ext = extension.lower()
        if not ext.startswith('.'):
            ext = '.' + ext

        if ext in KnownExtensions.IMAGE:
            return KnownExtensions.ICONS["IMAGE"]
        elif ext in KnownExtensions.VIDEO:
            return KnownExtensions.ICONS["VIDEO"]
        elif ext in KnownExtensions.AUDIO:
            return KnownExtensions.ICONS["AUDIO"]
        elif ext in KnownExtensions.BOOK:
            return KnownExtensions.ICONS["BOOK"]
        elif ext in KnownExtensions.CONFIG:
            return KnownExtensions.ICONS["CONFIG"]
        elif ext in KnownExtensions.BINARY:
            return KnownExtensions.ICONS["BINARY"]
        elif ext in KnownExtensions.DISC:
            return KnownExtensions.ICONS["DISC"]
        elif ext in KnownExtensions.KEY:
            return KnownExtensions.ICONS["KEY"]
        else:
            return KnownExtensions.ICONS["DEFAULT"]

@lru_cache(maxsize=None)
def get_size(path, ignore_hidden=False):
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