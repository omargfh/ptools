import os
from pathlib import Path
import random

from ptools.utils.config import KeyValueStore
from ptools.lib.llm.entities import LLMProfile, LLMChatFile

key_store = KeyValueStore(name=os.path.join('llm', 'keys'), quiet=True, encrypt=True)

class ProfilesStore(KeyValueStore):
    @property
    def config_dir(self) -> Path:
        return Path(self.file_path).parent

    def get_profile_path_from_name(self, name: str) -> str:
        return os.path.join(self.config_dir, 'profiles', name + '.json')
    
    def get_profile_by_name(self, name: str) -> LLMProfile | None:
        file_path = self.get_profile_path_from_name(name)
        if not os.path.exists(file_path):
            return None
        return LLMProfile.from_json(file_path)
    
    def add(self, name: str, profile: LLMProfile) -> None:
        if self.get(name):
            raise ValueError(f"Profile with name '{name}' already exists.")
        file_path = self.get_profile_path_from_name(name)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w') as f:
            f.write(profile.model_dump_json(indent=4))
        self.set(name, file_path)

profiles_store = ProfilesStore(name=os.path.join('llm', 'profiles'), quiet=True, encrypt=False)

class ChatsStore(KeyValueStore):
    def get_chat_by_name(self, name: str) -> LLMChatFile | None:
        chat_file = LLMChatFile.from_json(name)
        self.set(name, chat_file.file.file_path)
        return chat_file

    def new_chat(self, name: str | None = None) -> LLMChatFile:
        chat_file = LLMChatFile.new_file(name=name)
        self.set(chat_file.name, chat_file.file.file_path)
        return chat_file
    
    def no_persist_chat(self) -> LLMChatFile:
        return LLMChatFile.new_file(persist=False)

    def delete_chat(self, name: str) -> None:
        path = self.get(name)
        os.remove(path)
        self.delete(name)


chats_store = ChatsStore(name=os.path.join('llm', 'chat_files'), quiet=True, encrypt=True)

if __name__ == "__main__":
    chat_file = ChatsStore.new_chat(name="test_chat")
    chat_file.add_message("user", "Hello, how are you?")
    chat_file.set_metadata("topic", "greeting")
    print(chat_file)