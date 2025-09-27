from .commands import file as File
from .grammar import parser, PromptTransformer
from .commands import Commands

def parse_prompt(prompt: str, context=None) -> str:
    tree = parser.parse(prompt)
    transformer = PromptTransformer()
    result = transformer.transform(tree)
    if not isinstance(result, list):
        result = [result]

    parts = []
    default_context = {
        "prompt": prompt
    }
    context = {
        **context,
        **default_context
    } if context else default_context
    
    for item in result:
        if 'text' in item:
            parts.append(item.get('text'))
        elif 'command' in item:
            cmd_name = item.get('command')
            cmd_cls = Commands.get(cmd_name)
            if cmd_cls:
                cmd_instance = cmd_cls.wrap(item, context=context)
                parts.append(cmd_instance())
            else:
                parts.append(f"[Unknown command: {cmd_name}]")

    if parts[-1] and parts[-1][-1] != '\n':
        parts[-1] += '\n'

    return ' '.join(parts)