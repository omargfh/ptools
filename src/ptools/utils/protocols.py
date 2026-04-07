"""Structural typing protocols shared across :mod:`ptools.utils`."""
from typing import Protocol, Any

__version__ = "0.1.0"


class ImplementsGet(Protocol):
    """Anything with a ``get(key, default=None)`` method (``dict``, config, etc.)."""

    def get(self, key: str, default: Any = None) -> Any:
        """Return the value for ``key`` or ``default`` if missing."""
        ...