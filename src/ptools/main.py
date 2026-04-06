from importlib import import_module

import click
from click.formatting import HelpFormatter

COMMANDS = {
    "clip": {
        "import_path": "ptools.clip:cli",
        "short_help": "Copy input data to clipboard.",
    },
    "dev": {
        "import_path": "ptools.dev:cli",
        "short_help": "Developer options for power tools.",
    },
    "flow": {
        "import_path": "ptools.flow:cli",
        "short_help": "Pythonic FP-flavored workflow engine.",
    },
    "fs": {
        "import_path": "ptools.fs:cli",
        "short_help": "Filesystem manipulation tools.",
    },
    "json": {
        "import_path": "ptools.json:cli",
        "short_help": "JSON manipulation tools.",
    },
    "kill": {
        "import_path": "ptools.kill:cli",
        "short_help": "Kill tools.",
    },
    "lget": {
        "import_path": "ptools.literals:cli",
        "short_help": "Select a literal from a configured collection.",
    },
    "llm": {
        "import_path": "ptools.llm:cli",
        "short_help": "Interact with a chat interface.",
    },
    "llm-opts": {
        "import_path": "ptools.llm:opts",
        "short_help": "AI related commands.",
    },
    "projects": {
        "import_path": "ptools.projects:cli",
        "short_help": "Manage project shortcuts.",
    },
    "rsync": {
        "import_path": "ptools.rsync:cli",
        "short_help": "rsync power tools.",
    },
    "secrets": {
        "import_path": "ptools.secrets:cli",
        "short_help": "Manage secrets configuration.",
    },
    "shell": {
        "import_path": "ptools.shell:cli",
        "short_help": "Shell configuration helpers.",
    },
    "time": {
        "import_path": "ptools.time:cli",
        "short_help": "Timing utilities for power tools.",
    },
    "touch": {
        "import_path": "ptools.touch:cli",
        "short_help": "UNIX touch powered with Jinja2 templates.",
    },
    "watch": {
        "import_path": "ptools.watch:cli",
        "short_help": "Watch for changes and rerun commands.",
    },
}


def _load_command(import_path: str) -> click.Command:
    module_name, attribute = import_path.split(":", maxsplit=1)
    module = import_module(module_name)
    return getattr(module, attribute)


class LazyGroup(click.Group):
    def list_commands(self, ctx: click.Context) -> list[str]:
        return sorted(COMMANDS)

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
        command_info = COMMANDS.get(cmd_name)
        if command_info is None:
            return None
        return _load_command(command_info["import_path"])

    def format_commands(self, ctx: click.Context, formatter: HelpFormatter) -> None:
        rows = [
            (name, COMMANDS[name]["short_help"])
            for name in self.list_commands(ctx)
        ]
        if rows:
            with formatter.section("Commands"):
                formatter.write_dl(rows)


@click.group(cls=LazyGroup)
@click.version_option()
def cli():
    """power tools command line interface."""
    pass
