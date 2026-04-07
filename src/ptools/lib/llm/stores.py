"""On-disk stores that index API keys, LLM profiles, and chat files."""
import os
from pathlib import Path
import random

from ptools.utils.config import KeyValueStore
from ptools.lib.llm.entities import LLMProfile, LLMChatFile

__version__ = "0.1.0"

key_store = KeyValueStore(name=os.path.join('llm', 'keys'), quiet=True, encrypt=True)

class ProfilesStore(KeyValueStore):
    """Key/value store of LLM profile names to JSON files on disk."""

    @property
    def config_dir(self) -> Path:
        """Return the directory in which profile JSON files are kept."""
        return Path(self.file_path).parent

    def get_profile_path_from_name(self, name: str) -> str:
        """Return the JSON path used for profile ``name``."""
        return os.path.join(self.config_dir, 'profiles', name + '.json')

    def get_profile_by_name(self, name: str) -> LLMProfile | None:
        """Load the profile registered as ``name`` or return ``None`` if missing."""
        file_path = self.get_profile_path_from_name(name)
        if not os.path.exists(file_path):
            return None
        return LLMProfile.from_json(file_path)

    def add(self, name: str, profile: LLMProfile) -> None:
        """Persist ``profile`` under ``name``, raising if the name already exists."""
        if self.get(name):
            raise ValueError(f"Profile with name '{name}' already exists.")
        file_path = self.get_profile_path_from_name(name)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w') as f:
            f.write(profile.model_dump_json(indent=4))
        self.set(name, file_path)

profiles_store = ProfilesStore(name=os.path.join('llm', 'profiles'), quiet=True, encrypt=False)

class ChatsStore(KeyValueStore):
    """Key/value store of chat-file names to their on-disk paths."""

    def get_chat_by_name(self, name: str) -> LLMChatFile | None:
        """Load the chat file registered under ``name``, refreshing the index entry."""
        chat_file = LLMChatFile.from_json(name)
        self.set(name, chat_file.file.file_path)
        return chat_file

    def new_chat(self, name: str | None = None) -> LLMChatFile:
        """Create and register a new persisted chat file (random name if none given)."""
        chat_file = LLMChatFile.new_file(name=name)
        self.set(chat_file.name, chat_file.file.file_path)
        return chat_file

    def no_persist_chat(self) -> LLMChatFile:
        """Return an in-memory chat file that is not persisted or indexed."""
        return LLMChatFile.new_file(persist=False)

    def delete_chat(self, name: str) -> None:
        """Remove the chat file registered as ``name`` from disk and the index."""
        path = self.get(name)
        os.remove(path)
        self.delete(name)


chats_store = ChatsStore(name=os.path.join('llm', 'chat_files'), quiet=True, encrypt=True)

if __name__ == "__main__":
    chat_file = ChatsStore.new_chat(name="test_chat")
    chat_file.add_message("user", "Hello, how are you?")
    chat_file.set_metadata("topic", "greeting")
    print(chat_file)