from abc import ABC, abstractmethod

class HistoryTransformer(ABC):
    @abstractmethod
    def transform(self, history: list[dict]) -> list[dict]:
        """Transform the chat history."""
        pass

class PassThroughHistoryTransformer(HistoryTransformer):
    def transform(self, history: list[dict]) -> list[dict]:
        return history
    
class HistoryTransformerFactory():
    transformers = {
        "pass_through": PassThroughHistoryTransformer,
    }
    @staticmethod
    def get_transformer(name: str) -> HistoryTransformer:
        transformer_class = HistoryTransformerFactory.transformers.get(name)
        if not transformer_class:
            raise ValueError(f"Unknown transformer: {name}")
        return transformer_class()
    
    @staticmethod
    def list_transformers() -> list[str]:
        return list(HistoryTransformerFactory.transformers.keys())