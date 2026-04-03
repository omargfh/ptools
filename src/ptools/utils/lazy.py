from typing import Generic, TypeVar, Callable, Optional

T = TypeVar('T')
class Lazy(Generic[T]):
    def __init__(self, func: Callable[[], T]):
        self.func = func
        self._value: Optional[T] = None
        self._evaluated = False

    @property
    def value(self) -> T:
        if not self._evaluated:
            self._value = self.func()
            self._evaluated = True
        return self._value  # type: ignore
