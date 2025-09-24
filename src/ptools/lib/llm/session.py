from ptools.lib.llm.client import ChatClient
from ptools.lib.llm.history import PassThroughHistoryTransformer
from ptools.lib.llm.entities import LLMChatFile, LLMProfile
class ChatSession():
    def __init__(
        self,
        provider: ChatClient,
        profile: LLMProfile | None = None,
        chat_file: LLMChatFile | None = None,
        history_transformer = PassThroughHistoryTransformer(),
    ):
        self.provider  = provider
        self.profile   = profile
        self.chat_file = chat_file or LLMChatFile.new_file()
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
