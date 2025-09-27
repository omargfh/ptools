from __future__ import annotations

from ptools.lib.llm.command import Command, CommandArgument, CommandSchema

class SaveCommand:
    @staticmethod
    def call(
        path: str,
        last: int | None = None,
        capture_code: bool = False, 
        user_only: bool = False,
        assistant_only: bool = False,
        context=None
    ):
        if last is not None and last > 1 and capture_code:
            raise ValueError("Error: capture_code can only be used when last is 1.")

        if user_only and assistant_only:
            raise ValueError("Error: Cannot use both user_only and assistant_only.")

        history = context['history']() if context and 'history' in context else []
        if not history:
            raise ValueError("No chat history available.")

        filtered_history = []
        for message in reversed(history):
            if user_only and message.role != 'user':
                continue
            if assistant_only and message.role != 'assistant':
                continue
            filtered_history.append(message)
            if last and len(filtered_history) >= last:
                break
        
        filtered_history.reverse()
        
        content = "\n".join([f"{m.role.capitalize()}:\n{m.content}" for m in filtered_history])
        if capture_code:
            import re
            content = filtered_history[-1].content
            
            code_blocks = re.findall(r'```(?:\w*\n)?(.*?)```', content, re.DOTALL)
            code_blocks += re.findall(r'(?:\n(?: {4}|\t).+)+', content)
            
            if len(code_blocks) == 1:
                content =  code_blocks[0].strip()
            elif len(code_blocks) > 1:
                raise ValueError("Error: Multiple code blocks found in the last assistant message.")

        try:
            with open(path, 'w') as f:
                f.write(content)
        except Exception as e:
            raise ValueError(f"Error writing to file: {e}")
        
        return ""
    
save_command = Command(
    name="save",
    description="Save the current chat history to a file.",
    possible_schemas=[
         CommandSchema(arguments=[
            CommandArgument(name="path", required=True),
        ], call=SaveCommand.call),
        CommandSchema(arguments=[
            CommandArgument(name="path", required=True),
            CommandArgument(name="last", required=False, parser=int),
            CommandArgument(name="capture_code", required=False, parser=bool),
            CommandArgument(name="user_only", required=False, parser=bool),
            CommandArgument(name="assistant_only", required=False, parser=bool),
        ], call=SaveCommand.call)
    ]
)

save_code_command = Command(
    name="dump",
    description="Save the current chat history to a file.",
    possible_schemas=[
        CommandSchema(arguments=[
            CommandArgument(name="path", required=True),
        ], call=lambda *args, **kwargs: SaveCommand.call(*args, last=1, capture_code=True, assistant_only=True, **kwargs))
    ]
)