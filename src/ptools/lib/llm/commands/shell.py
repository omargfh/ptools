from __future__ import annotations
from typing import List
import subprocess

from ptools.lib.llm.command import Command, CommandArgument, CommandSchema

class ShellCommand:
    @staticmethod
    def call(command: str, streams: tuple[bool, bool] = (True, False), timeout: int | None = None, check: bool = False, context=None):
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout, check=check)
            output = ""
            if streams[0]:  # stdout
                output += result.stdout
            if streams[1]:  # stderr
                output += result.stderr
            return output
        except Exception as e:
            return f"Exception occurred: {e}"

def parse_stream(value: str) -> bool:
    streams = value.lower().split(',')
    return 'stdout' in streams, 'stderr' in streams

shell_command = Command(
    name="shell",
    description="Execute a shell command.",
    possible_schemas=[
        CommandSchema(arguments=[
            CommandArgument(name="command", required=True, nargs='*', parser=' '.join, parser_name='str'),
        ], call=ShellCommand.call),
        CommandSchema(arguments=[
            CommandArgument(name="command", required=True, nargs='*', parser=' '.join, parser_name='str'),
            CommandArgument(name="streams", required=False, kind='kwarg', parser=parse_stream, parser_name='str'),
            CommandArgument(name="timeout", required=False, kind='kwarg', parser=int),
            CommandArgument(name="check", required=False, kind='kwarg', parser=bool),
        ], call=ShellCommand.call)
    ]
)


if __name__ == "__main__":
    sc = shell_command.wrap({
        'command': 'shell',
        'args': [
            'seq','4'
        ]
    })
    print(sc())