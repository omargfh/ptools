"""Pydantic data models for chat profiles, messages, and on-disk chat files."""
from enum import Enum
import os

import pydantic

from ptools.utils.config import KeyValueStore, DummyKeyValueStore
from ptools.utils.xml_repr import xmlclass

from ptools.lib.llm.constants import model_choices

__version__ = "0.1.0"


class LLMHistoryType(Enum):
    """How much chat history to include when sending the next request."""

    full = 'full'
    last = 'last'
    none = 'none'

    def __repr__(self):
        return self.value

class LLMProfile(pydantic.BaseModel):
    """Sampling parameters and system prompt that pin down a model's behavior."""

    top_p: float = 0.9
    temperature: float = 0.7
    max_tokens: int = 2048
    presence_penalty: float = 0.0
    model: str | None = None

    system_prompt: str | None = "You are a helpful assistant."

    @classmethod
    def from_json(cls, file_path: str) -> "LLMProfile":
        """Load a profile from a JSON file on disk."""
        import json
        with open(file_path, 'r') as f:
            data = json.load(f)
        return cls(**data)

    @pydantic.model_validator(mode='after')
    def validate_model(self):
        """Reject unknown model identifiers against :data:`model_choices`."""
        if self.model and self.model not in model_choices:
            raise ValueError(f"Model '{self.model}' is not supported. Choose from: {', '.join(model_choices)}")
        return self

@xmlclass
class LLMMessage(pydantic.BaseModel):
    """A single ``role``/``content`` chat turn rendered as ``<LLMMessage role="...">``."""

    role: str
    content: str

    def __xml__attrs__(self):
        """Return the XML attributes used by :class:`XMLRepr`."""
        return {
            'role': self.role,
            'children': self.content,
        }

@xmlclass
class LLMChatFile(pydantic.BaseModel):
    """A persisted chat transcript backed by an encrypted :class:`KeyValueStore`."""

    name: str
    messages: list[LLMMessage] = []
    metadata: dict = {}

    file: KeyValueStore | DummyKeyValueStore| None

    model_config = {
        "arbitrary_types_allowed": True,
        "json_encoders": {
            KeyValueStore: lambda v: v.file_path if v else None,
            DummyKeyValueStore: lambda v: "DummyKeyValueStore",
        }
    }

    @pydantic.model_validator(mode='after')
    def validate_model(self):
        """Ensure the chat file is bound to a backing key/value store."""
        if self.file is None:
            raise ValueError("file must be provided and be a KeyValueStore instance.")
        return self

    @staticmethod
    def get_relative_path_by_name(name: str) -> str:
        """Return the on-disk path for a chat file with the given ``name``."""
        return os.path.join('llm', 'chat_files', name)

    @classmethod
    def from_json(cls, name: str) -> "LLMChatFile":
        """Load (and lazily create) the chat file backed by ``name`` on disk."""
        relative_path = LLMChatFile.get_relative_path_by_name(name)
        cf = KeyValueStore(name=relative_path, quiet=True, encrypt=True)

        if not cf.get('name'):
            cf.set('name', name)

        messages = cf.get('messages', [])
        metadata = cf.get('metadata', {})

        return cls(name=name, messages=messages, metadata=metadata, file=cf)

    @staticmethod
    def new_file(name: str | None = None, persist=True) -> "LLMChatFile":
        """Create a brand-new chat file, optionally persisted under ``name``.

        :param name: Optional file name; a random one is generated if omitted.
        :param persist: When ``False``, returns an in-memory chat file backed
            by :class:`DummyKeyValueStore` so nothing is written to disk.
        """
        if not name:
            import random
            name = f"tmp_chat_{random.randint(1000, 9999)}"

        if not persist:
            return LLMChatFile(
                name=name,
                messages=[],
                metadata={},
                file=DummyKeyValueStore()
            )

        relative_path = LLMChatFile.get_relative_path_by_name(name)

        cf = KeyValueStore(name=relative_path, quiet=True, encrypt=True)

        cf.set('name', name)
        if not cf.get('messages'):
            cf.set('messages', [])
        if not cf.get('metadata'):
            cf.set('metadata', {})

        return LLMChatFile.from_json(name)

    def add_message(self, role: str, content: str):
        """Append a new message and persist the updated transcript."""
        self.messages.append(LLMMessage(role=role, content=content))
        self.file.set('messages', [m.model_dump() for m in self.messages])

    def set_metadata(self, key: str, value):
        """Update a metadata field on the chat file and persist it."""
        self.metadata[key] = value
        self.file.set('metadata', self.metadata)

    def __xml__attrs__(self):
        """Return XML attributes including child messages for :class:`XMLRepr`."""
        return {
            'children': self.messages,
            'name': self.name,
            'count': len(self.messages),
            **self.metadata,
        }

    def __repr__(self):
        return self.__xml__()

if __name__ == "__main__":
    chat = LLMChatFile(
        name="example_chat",
        messages=[
            LLMMessage(role="user", content="Hello, how are you?"),
            LLMMessage(role="assistant", content="I'm good, thank you! How can I assist you today?")
        ]
    )
    print(chat)