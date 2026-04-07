"""Prompt parser that expands embedded ptools commands into plain text."""
from .commands import file as File
from .grammar import parser, PromptTransformer
from .commands import Commands

__version__ = "0.1.0"


def parse_prompt(prompt: str, context=None) -> str:
    """Parse ``prompt``, run any embedded commands, and return the rendered string.

    :param prompt: Raw user prompt that may contain ptools-llm command syntax.
    :param context: Optional dict of variables exposed to embedded commands.
    """
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