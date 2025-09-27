from __future__ import annotations
from typing import List

from ptools.lib.llm.command import Command, CommandArgument, CommandSchema

class FileCommand:
    @staticmethod
    def call(path: str, lines: List[int] | None = None, start: int | None = None, end: int | None = None, context=None):
        try:
            with open(path, 'r') as f:
                content = f.readlines()
                if lines:
                    selected_lines = []
                    for line_spec in lines:
                        if ':' in str(line_spec):
                            start_line, end_line = map(int, line_spec.split(':'))
                            selected_lines.extend(content[start_line-1:end_line])
                        else:
                            selected_lines.append(content[int(line_spec)-1])
                    return ''.join(selected_lines)
                elif start is not None and end is not None:
                    return ''.join(content[start-1:end])
                else:
                    return ''.join(content)
        except Exception as e:
            return f"Error reading file: {e}"

def parse_range(value: str) -> List[int]:
    if ':' in value:
        start, end = value.split(':')
        return [int(start) if start else 1, int(end) if end else None]
    else:
        return [int(value)]

file_command = Command(
    name="file",
    description="Read a file into prompt.",
    possible_schemas=[
        CommandSchema(arguments=[
            CommandArgument(name="path", required=True),
            CommandArgument(name="lines", required=False, parser=parse_range),
        ], call=FileCommand.call),
        CommandSchema(arguments=[
            CommandArgument(name="path", required=True),
            CommandArgument(name="start", required=True, parser=int),
            CommandArgument(name="end", required=True, parser=int),
        ], call=FileCommand.call),
        CommandSchema(arguments=[
            CommandArgument(name="path", required=True),
            CommandArgument(name="start", required=False, parser=int, kind='kwarg'),
            CommandArgument(name="end", required=False, parser=int, kind='kwarg'),
        ], call=FileCommand.call)
    ]
)

if __name__ == "__main__":
    fc = file_command.wrap({
        'command': 'file',
        'args': [
            'pyproject.toml',
            ':3'
        ]
    })
    print(fc())

    fc = file_command.wrap({
        'command': 'file',
        'args': [
            'pyproject.toml',
            {'name': 'start', 'value': 2},
            {'name': 'end', 'value': 5}
        ]
    })
    print(fc())
