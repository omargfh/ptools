"""Tiny lazy-value wrapper used to defer expensive initialization."""
from typing import Generic, TypeVar, Callable, Optional

__version__ = "0.1.0"

T = TypeVar('T')


class Lazy(Generic[T]):
    """Wraps a zero-argument callable and memoizes its first result.

    Reading :attr:`value` invokes ``func`` exactly once; subsequent
    accesses return the cached result without re-running it.

    :param func: The thunk that produces the lazy value.
    """

    def __init__(self, func: Callable[[], T]):
        self.func = func
        self._value: Optional[T] = None
        self._evaluated = False

    @property
    def value(self) -> T:
        """Return the cached value, computing it on first access."""
        if not self._evaluated:
            self._value = self.func()
            self._evaluated = True
        return self._value  # type: ignore
