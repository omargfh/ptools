"""Pluggable transformers that rewrite chat history before sending it to a model."""
from abc import ABC, abstractmethod

__version__ = "0.1.0"


class HistoryTransformer(ABC):
    """Abstract base for chat-history rewriters (e.g. truncation, summarization)."""

    @abstractmethod
    def transform(self, history: list[dict]) -> list[dict]:
        """Return a rewritten copy of ``history``."""
        pass

class PassThroughHistoryTransformer(HistoryTransformer):
    """Identity transformer used as a default when no rewriting is needed."""

    def transform(self, history: list[dict]) -> list[dict]:
        """Return ``history`` unchanged."""
        return history

class HistoryTransformerFactory():
    """Lookup table that resolves transformer instances by their registered name."""

    transformers = {
        "pass_through": PassThroughHistoryTransformer,
    }
    @staticmethod
    def get_transformer(name: str) -> HistoryTransformer:
        """Instantiate the transformer registered under ``name``.

        :raises ValueError: if ``name`` is not registered.
        """
        transformer_class = HistoryTransformerFactory.transformers.get(name)
        if not transformer_class:
            raise ValueError(f"Unknown transformer: {name}")
        return transformer_class()

    @staticmethod
    def list_transformers() -> list[str]:
        """Return the names of every registered transformer."""
        return list(HistoryTransformerFactory.transformers.keys())