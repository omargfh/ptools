"""Named file stores with a registry kept separate from the files it indexes.

Layout::

    ~/.ptools/registry/<name>.json     key -> path relative to the object root
    ~/.ptools/storage/<name>/<path>    the objects themselves

Each side lives behind its own :class:`StorageRoot`, so a key, a parent
directory or a registry entry can never resolve to a file outside the
directory it belongs to.
"""
import os
from pathlib import Path

from ptools.utils.config import LazyConfigFile

PTOOLS_HOME = Path(os.path.expanduser("~/.ptools"))


class PathEscapeError(ValueError):
    """A path resolved outside the :class:`StorageRoot` that owns it."""


class StorageRoot:
    """A directory that only hands out paths inside itself."""

    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def resolve(self, *parts: str) -> Path:
        """Join *parts* under the root, refusing absolute parts and escapes."""
        if not parts or any(not p for p in parts):
            raise ValueError("Path parts must be non-empty.")
        if any(os.path.isabs(p) for p in parts):
            raise PathEscapeError(f"Absolute paths are not allowed: {parts!r}")
        candidate = self.root.joinpath(*parts).resolve()
        if not candidate.is_relative_to(self.root):
            raise PathEscapeError(f"{'/'.join(parts)!r} escapes {self.root}")
        return candidate

    def relative(self, path: Path) -> str:
        """Portable, root-relative form of *path* for storing in a registry."""
        return path.relative_to(self.root).as_posix()


class FileStorageClient:
    def __init__(self, name: str):
        self.name = name
        self._objects = StorageRoot(PTOOLS_HOME / "storage" / name)
        self._registry_root = StorageRoot(PTOOLS_HOME / "registry")
        # Registry file is itself resolved through its root, then handed
        # to LazyConfigFile as a plain (name, path) pair.
        self._registry = LazyConfigFile(
            name,
            path=str(self._registry_root.root),
            quiet=True,
        )

    def _path_of(self, key: str) -> Path | None:
        """Stored location of *key*, re-validated against the object root."""
        rel = self._registry.get(key)
        return None if rel is None else self._objects.resolve(rel)

    def list_objects(self, prefix: str = "") -> list[str]:
        return sorted(k for k in self._registry.data if k.startswith(prefix))

    def exists(self, key: str) -> bool:
        path = self._path_of(key)
        return path is not None and path.is_file()

    def get_file_path(self, key: str) -> Path:
        path = self._path_of(key)
        if path is None:
            raise KeyError(f"Key '{key}' not found in '{self.name}'.")
        return path

    def get_object(self, key: str) -> str | None:
        if not self.exists(key):
            return None
        return self.get_file_path(key).read_text(encoding="utf-8")

    def stream_object(self, key: str):
        if not self.exists(key):
            return
        with self.get_file_path(key).open("r", encoding="utf-8") as f:
            yield from f

    def put_object(self, key: str, value, parent: str | None = None) -> Path:
        parts = (parent, key) if parent else (key,)
        path = self._objects.resolve(*parts)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(value), encoding="utf-8")
        self._registry.set(key, self._objects.relative(path))
        return path

    def delete_object(self, key: str) -> None:
        path = self.get_file_path(key)  # raises KeyError if unregistered
        self._registry.delete(key)
        if path.is_file():
            path.unlink()
        # Clean up empty parent directories up to the object root
        parent = path.parent
        while parent != self._objects.root and not any(parent.iterdir()):
            parent.rmdir()
            parent = parent.parent