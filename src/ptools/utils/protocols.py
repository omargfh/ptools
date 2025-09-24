from typing import Protocol, Any

class ImplementsGet(Protocol):
    def get(self, key: str, default: Any = None) -> Any:
        ...