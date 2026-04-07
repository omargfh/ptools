"""Top-level ``ptools`` CLI entry point.

Defines a :class:`LazyGroup` click group that advertises every
subcommand in :data:`COMMANDS` without importing them eagerly. Each
entry in :data:`COMMANDS` maps a subcommand name to an
``"module:attribute"`` import path that is resolved on first use. This
keeps startup time low even though individual subcommands (notably
:mod:`ptools.llm`) pull in heavy dependencies.
"""

from importlib import import_module

import click
from click.formatting import HelpFormatter

__version__ = "0.1.0"

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
    "settings": {
        "import_path": "ptools.settings:cli",
        "short_help": "Manage power tools settings.",
    },
}


def _load_command(import_path: str) -> click.Command:
    """Import and return the Click command referenced by ``"module:attribute"``."""
    module_name, attribute = import_path.split(":", maxsplit=1)
    module = import_module(module_name)
    return getattr(module, attribute)


class LazyGroup(click.Group):
    """Click group that resolves subcommands from :data:`COMMANDS` on demand.

    Subcommands are stored as ``"module:attribute"`` import paths and only
    imported the first time they are invoked, keeping CLI startup fast
    even when individual commands depend on heavy libraries.
    """

    def list_commands(self, ctx: click.Context) -> list[str]:
        """Return every advertised subcommand name in sorted order."""
        return sorted(COMMANDS)

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
        """Resolve and import ``cmd_name`` from :data:`COMMANDS`, or ``None`` if unknown."""
        command_info = COMMANDS.get(cmd_name)
        if command_info is None:
            return None
        return _load_command(command_info["import_path"])

    def format_commands(self, ctx: click.Context, formatter: HelpFormatter) -> None:
        """Render the subcommand list in ``--help`` using the cached short help strings."""
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
