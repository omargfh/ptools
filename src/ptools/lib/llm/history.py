from abc import ABC, abstractmethod

class HistoryTransformer(ABC):
    @abstractmethod
    def transform(self, history: list[dict]) -> list[dict]:
        """Transform the chat history."""
        pass

class PassThroughHistoryTransformer(HistoryTransformer):
    def transform(self, history: list[dict]) -> list[dict]:
        return history