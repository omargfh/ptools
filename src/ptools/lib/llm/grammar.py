from lark import Lark, Transformer, v_args

command_grammar = r"""
?start: text

?text: (command | WORD)+

command: COMMAND argument_list? COMMAND_DELIMITER -> command
        | COMMAND greedy_arguments?               -> command

argument_list: arg+     -> args

greedy_arguments: arg              -> single_arg

arg: kwarg | posarg

kwarg: NAME "=" VALUE
posarg: VALUE

NAME: /[a-zA-Z_][a-zA-Z0-9_]*/
VALUE: /[^@,\s]+/ | ESCAPED_STRING

COMMAND: /@[a-zA-Z_][a-zA-Z0-9_]*/
COMMAND_DELIMITER: "@/"

WORD: /[^\s@][^\s]*/

%import common.ESCAPED_STRING
%import common.WS
%ignore WS
"""

parser = Lark(command_grammar, start="start")

class PromptTransformer(Transformer):
    def WORD(self, token): return {'text': str(token)}
    def COMMAND(self, token): return str(token)
    def COMMAND_DELIMITER(self, token): return str(token)
    def NAME(self, token): return str(token)
    def VALUE(self, t):
        v = str(t)
        if v[0] in ('"', "'", '`') and v[-1] in ('"', "'", '`'):
            return v[1:-1]
        return v
    def kwarg(self, items): return { 'name': items[0], 'value': items[1] }
    def posarg(self, items): return items[0]
    def arg(self, items): return items[0]

    def text(self, items):
        return items

    def command(self, items):
        command_name = items[0][1:]
        args = items[1] if len(items) > 1 else []
        return {'command': command_name, 'args': args}

    def args(self, items):
        return [self._parse_arg(item) for item in items]

    def single_arg(self, items):
        return [self._parse_arg(items[0])]

    def _parse_arg(self, arg):
        if '=' in arg:
            name, value = arg.split('=', 1)
            return (name, value)
        return arg

if __name__ == "__main__":
    import json
    prompt = 'Hello @greet name=Rob @greet name="Alice" age=15 @/ How are you? @echo "This is a test" @file path="example.txt" 1:10 @/'
    tree = parser.parse(prompt)
    transformer = PromptTransformer()
    result = transformer.transform(tree)
    print(json.dumps(result, indent=2))

    from ptools.lib.llm.commands.file import *
    prompt = 'Hi @file pyproject.toml 1:10 @/ No way'

    tree = parser.parse(prompt)
    transformer = PromptTransformer()
    result = transformer.transform(tree)

    result_prompt = ''
    for part in result:
        if 'text' in part:
             result_prompt += part['text'] + ' '
        elif 'command' in part and part['command'] == 'file':
            fn = file_command.wrap(part)
            result_prompt += fn() + ' '
    print(result_prompt)