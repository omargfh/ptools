from enum import Enum
import os

import pydantic

from ptools.utils.config import KeyValueStore
from ptools.utils.xml_repr import xmlclass

class LLMHistoryType(Enum):
    full = 'full'
    last = 'last'
    none = 'none'
    
    def __repr__(self):
        return self.value

class LLMProfile(pydantic.BaseModel):
    top_p: float = 0.9
    temperature: float = 0.7
    max_tokens: int = 2048
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0

    system_prompt: str | None = None
    history_length: int | None = None

    @classmethod
    def from_json(cls, file_path: str) -> "LLMProfile":
        import json
        with open(file_path, 'r') as f:
            data = json.load(f)
        return cls(**data)

@xmlclass
class LLMMessage(pydantic.BaseModel):
    role: str
    content: str

    def __xml__attrs__(self):
        return {
            'role': self.role,
            'children': self.content,
        }

@xmlclass
class LLMChatFile(pydantic.BaseModel):
    name: str
    messages: list[LLMMessage] = []
    metadata: dict = {}

    file: KeyValueStore | None

    model_config = {
        "arbitrary_types_allowed": True,
        "json_encoders": {
            KeyValueStore: lambda v: v.file_path if v else None
        }
    }
    
    @pydantic.model_validator(mode='after')
    def validate_model(self):
        if self.file is None:
            raise ValueError("file must be provided and be a KeyValueStore instance.")
        return self

    @classmethod
    def from_json(cls, name: str) -> "LLMChatFile":
        relative_path = os.path.join('llm', 'chat_files', name)
        cf = KeyValueStore(name=relative_path, quiet=True, encrypt=True)

        if not cf.get('name'):
            cf.set('name', name)

        messages = cf.get('messages', [])
        metadata = cf.get('metadata', {})

        return cls(name=name, messages=messages, metadata=metadata, file=cf)

    @staticmethod
    def new_file(name: str | None = None) -> "LLMChatFile":
        if not name:
            import random
            name = f"tmp_chat_{random.randint(1000, 9999)}"

        relative_path = os.path.join('llm', 'chat_files', f"{name}")
        cf = KeyValueStore(name=relative_path, quiet=True, encrypt=True)

        cf.set('name', name)
        if not cf.get('messages'):
            cf.set('messages', [])
        if not cf.get('metadata'):
            cf.set('metadata', {})

        return LLMChatFile.from_json(name)

    def add_message(self, role: str, content: str):
        self.messages.append(LLMMessage(role=role, content=content))
        self.file.set('messages', [m.model_dump() for m in self.messages])

    def set_metadata(self, key: str, value):
        self.metadata[key] = value
        self.file.set('metadata', self.metadata)

    def __xml__attrs__(self):
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