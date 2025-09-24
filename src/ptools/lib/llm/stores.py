import os
from pathlib import Path
import random

from ptools.utils.config import ConfigFile
from ptools.lib.llm.schemas import LLMProfile, LLMChatFile

key_store = ConfigFile(name=os.path.join('llm', 'keys'), quiet=True, encrypt=True)

class ProfilesConfigFile(ConfigFile):
    @property
    def config_dir(self) -> Path:
        return Path(self.file_path).parent

    def get_profile_by_name(self, name: str) -> LLMProfile | None:
        file_path = self.get(name)
        return LLMProfile.from_json(file_path) if file_path else None

profiles_store = ProfilesConfigFile(name=os.path.join('llm', 'profiles'), quiet=True, encrypt=False)

class ChatsConfigFile(ConfigFile):
    def get_chat_by_name(self, name: str) -> LLMChatFile | None:
        chat_file = LLMChatFile.from_json(name)
        self.set(name, chat_file.file.file_path)
        return chat_file

    def new_chat(self, name: str | None = None) -> LLMChatFile:
        chat_file = LLMChatFile.new_file(name=name)
        self.set(chat_file.name, chat_file.file.file_path)
        return chat_file

    def delete_chat(self, name: str) -> None:
        path = self.get(name)
        os.remove(path)
        self.delete(name)


chats_store = ChatsConfigFile(name=os.path.join('llm', 'chat_files'), quiet=True, encrypt=True)

if __name__ == "__main__":
    chat_file = ChatsConfigFile.new_chat(name="test_chat")
    chat_file.add_message("user", "Hello, how are you?")
    chat_file.set_metadata("topic", "greeting")
    print(chat_file)