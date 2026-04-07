"""Built-in ``@command`` implementations injected into LLM prompts."""

__version__ = "0.1.0"

from .file import file_command
from .shell import shell_command
from .save import save_command, save_code_command

Commands = {
    file_command.name: file_command,
    shell_command.name: shell_command,
    save_command.name: save_command,
    save_code_command.name: save_code_command,
}
commands = list(Commands.values())