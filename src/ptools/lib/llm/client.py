import os
from typing import List, Any

from .entities import LLMMessage

class ChatClient():
    def __init__(self):
        self.system_prompt = "You are a helpful assistant."
        self.client: "OpenAI" | None = None
        self.model: str | None = None

    def run(self, messages: List[LLMMessage], show=True, **kwargs) -> Any:
        stream = self.client.chat.completions.create(
            messages=messages,
            model=self.model,
            stream=True,
            **kwargs
        )

        output = ""
        if kwargs.get("stream", True):
            for chunk in stream:
                if type(chunk.choices[0].delta.content) == str:
                    output += chunk.choices[0].delta.content
                    yield chunk.choices[0].delta.content or ""

            if output[-1] != "\n":
                output += "\n"
                yield "\n"
        else:
            output = stream.choices[0].message.content
            yield output

class OpenAIChatClient(ChatClient):
    def __init__(self, model: str = "gpt-4o-mini"):
        super().__init__()
        from openai import OpenAI
        self.model = model
        self.client =  OpenAI(
            api_key=os.environ.get('OPENAI_API_KEY'),
        )

class GoogleChatClient(ChatClient):
    def __init__(self, model: str = "gemini-1.5-flash"):
        super().__init__()
        from openai import OpenAI
        self.model = model
        self.client = OpenAI(
            api_key=os.environ.get('GOOGLE_API_KEY'),
            base_url="https://generativelanguage.googleapis.com/v1beta/openai"
        )