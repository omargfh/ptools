from ptools.lib.llm.client import ChatClient
from ptools.lib.llm.stores import chats_store, profiles_store
from ptools.lib.llm.history import PassThroughHistoryTransformer

class ChatSession():
    def __init__(
        self,
        provider: ChatClient,
        profile: str | None = None,
        chat_file: str | None = None,
        history_transformer = PassThroughHistoryTransformer(),
    ):
        self.provider = provider
        self.profile = profiles_store.get_profile_by_name(profile)
        self.chat_file = chats_store.get_chat_by_name(chat_file) if chat_file else chats_store.new_chat()
        if not self.chat_file.file:
            raise ValueError("Chat file is not properly initialized.")
        self.history_transformer = history_transformer

    def send_message(self, content: str) -> str:
        self.chat_file.add_message(role="user", content=content)

        system_prompt = self.profile.system_prompt \
            if self.profile else "You are a helpful assistant."

        messages = self.chat_file.messages
        history  = self.history_transformer.transform(messages)
        response = self.provider.run(messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            *history,
        ])

        self.chat_file.add_message(role="assistant", content=response)

        return response
