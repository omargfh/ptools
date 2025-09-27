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
        
        formatting = """
        When responding, ensure the output is suitable for readability in a terminal environment.
        Do not use markdown or any other markup.
        Prefer plain text responses.
        Prefer dashes over asterisks for bullet points.
        Prefer tabs over ``` for code blocks.
        Use indentation for nested lists or code blocks.
        Avoid using emojis or special characters.
        Use new lines to separate paragraphs.
        Use numbered lists for ordered items.
        Use single quotes for quotations.
        Use double quotes for direct speech.
        Use parentheses for additional information or asides.
        Use colons to introduce lists or explanations.
        """

        response = self.provider.run(messages=[
            {
                "role": "system",
                "content": (system_prompt + formatting).strip()
            },
            *history,
        ], temperature=self.profile.temperature,
           max_tokens=self.profile.max_tokens,
           top_p=self.profile.top_p,
           presence_penalty=self.profile.presence_penalty,
        )
        
        for chunk in response:
            yield chunk
            
        response = ''.join(response)

        self.chat_file.add_message(role="assistant", content=response)