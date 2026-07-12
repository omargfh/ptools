"""Template-driven ``touch`` command: create files from Jinja2 templates.

Loads a user config (``~/.ptools/touch.yaml``) describing a list of
:class:`TouchItem` entries and dynamically registers one Click subcommand
per entry under the :data:`cli` group. Each subcommand renders its
template to the output path the user provides.

.. note::
    Because commands are registered in a loop, the per-iteration
    ``obj``/``fopts`` values **must** be bound as default arguments on
    ``touch_command`` (``def touch_command(..., obj=obj, fopts=fopts)``).
    Without that binding, every registered command would close over the
    same variables by reference and all end up using the last iteration's
    :class:`TouchItem` — producing identical output for every command.
    See ``tests/test_touch.py::TestCommandRegistration`` for a regression
    test.
"""

from __future__ import annotations

import os
import pathlib

import click
from jinja2 import Environment, Template, meta
from pydantic import BaseModel, model_validator

from ptools.utils.cases import CaseConverter, cases
from ptools.utils.config import LazyConfigFile
from ptools.utils.decorator_compistor import DecoratorCompositor
from ptools.utils.print import FormatUtils

messages = {
    "UNEXPECTED ERROR": FormatUtils.error("An unexpected error occurred. Please check your configuration and try again."),
    "INFER_FAILED": FormatUtils.error("Could not infer a command for the given output path. Please specify the command explicitly."),
}

class FileNameOptions(BaseModel):
    dir_okay: bool = False
    file_arg: str = "{dir}/output.txt"
    extension: str = ".txt"
    allow_empty_extension: bool = False
    allow_arbitrary_extension: bool = True
    casing: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _set_defaults(cls, values: dict) -> dict:
        dir_okay = values.get("dir_okay", False)
        file_okay = values.get("file_okay", True)
        file_arg = values.get("file_arg")

        if dir_okay and not file_okay and not file_arg:
            raise ValueError(
                "file_arg must be provided when dir_okay is True and file_okay is False"
            )
        return values


class TouchItem(BaseModel):
    command: str
    aliases: list[str] = []
    group: str = "default"
    description: str
    template_string: str
    arguments: dict[str, str] = {}
    file_name_options: FileNameOptions = FileNameOptions()

    # Populated in model_post_init — not user-supplied.
    template: Template | None = None
    _undeclared_vars: set[str] = set()

    model_config = {"arbitrary_types_allowed": True}

    def model_post_init(self, context) -> None:
        super().model_post_init(context)

        env = Environment()
        parsed = env.parse(self.template_string)
        self._undeclared_vars = meta.find_undeclared_variables(parsed)

        # Discovered vars become arguments (explicit values take precedence).
        self.arguments = {
            **{var: "<value>" for var in self._undeclared_vars},
            **self.arguments,
        }
        self.template = Template(self.template_string)


class TouchConfig(BaseModel):
    values: list[TouchItem] = []
    groups_meta: dict[str, dict] = {}


def set_extension(filepath: pathlib.Path, opts: FileNameOptions) -> pathlib.Path:
    """Apply extension rules from *opts* to *filepath*."""
    suffix = filepath.suffix
    has_extension = suffix != ""
    has_required = filepath.name.endswith(opts.extension)

    if not opts.allow_empty_extension and not has_extension:
        return filepath.with_name(filepath.name + opts.extension)

    if not opts.allow_arbitrary_extension and not has_required:
        return filepath.with_suffix(opts.extension)

    return filepath


def resolve_output(
    output_raw: str,
    fopts: FileNameOptions,
    casing_override: str | None,
    args: dict[str, str],
) -> pathlib.Path:
    """Turn the raw CLI argument into a fully-resolved output path."""
    output = pathlib.Path(output_raw)

    if output.is_dir() and not fopts.dir_okay:
        raise click.BadParameter(
            f"'{output}' is a directory, but dir_okay is False for this command."
        )

    if output.is_dir():
        filename = args.get(fopts.file_arg, "output.txt")
        output = output / filename

    output = set_extension(output, fopts)

    casing = casing_override or fopts.casing
    if casing is not None:
        output = output.with_name(
            CaseConverter.convert(output.stem, casing) + output.suffix
        )

    return output


def build_template_context(output: pathlib.Path, args: dict[str, str]) -> dict:
    """Merge file metadata, environment, and user-supplied args into one context dict."""
    file_vars = {
        "file_stem": output.stem,
        "file_suffix": output.suffix,
        "file_path": str(output),
        "file_name": output.name,
    }
    env_vars = {
        "cwd": str(pathlib.Path.cwd()),
        "home": str(pathlib.Path.home()),
        "user": os.environ.get("USER", ""),
    }
    builtins = {
        "convert_case": CaseConverter.convert,
        "env": os.environ.get,
    }
    return {**builtins, **env_vars, **file_vars, **args}


def _make_command(item: TouchItem) -> click.Command:
    """Build a Click command for a single :class:`TouchItem`."""
    fopts = item.file_name_options

    extra_options = DecoratorCompositor.from_list(
        [
            click.option(
                f"--{name}",
                type=str,
                required=False,
                help=help_text,
            )
            for name, help_text in item.arguments.items()
        ]
    )

    @click.argument(
        "output",
        type=click.Path(exists=False, file_okay=True, dir_okay=fopts.dir_okay),
        required=True,
    )
    @click.option(
        "-c",
        "--casing",
        type=click.Choice(cases),
        default=fopts.casing,
        help="Convert the filename to the specified casing.",
    )
    @extra_options.decorate()
    def handler(output: str, casing: str | None, _item=item, _fopts=fopts, **kwargs):
        args = {k: v for k, v in kwargs.items() if v is not None}
        resolved = resolve_output(output, _fopts, casing, args)

        if resolved.exists():
            click.confirm(
                f"'{resolved}' already exists. Overwrite?", abort=True
            )

        resolved.parent.mkdir(parents=True, exist_ok=True)
        ctx = build_template_context(resolved, args)

        if _item.template is None:
            FormatUtils.error(f"Template for command '{_item.command}' is not initialized.")
            return

        try:
            rendered = _item.template.render(**ctx)
            resolved.write_text(rendered)
            FormatUtils.success(f"File '{resolved}' created.")
        except Exception as e:
            FormatUtils.error(f"Error writing '{resolved}': {e}")

    cmd = click.Command(
        name=item.command,
        callback=handler,
        help=item.description,
        params=handler.__click_params__,  # type: ignore[attr-defined]
    )
    return cmd


def register_commands(group: click.Group, items: list[TouchItem]) -> None:
    """Register all touch items (and their aliases) onto *group*."""
    for item in sorted(items, key=lambda x: x.group):
        cmd = _make_command(item)
        group.add_command(cmd, item.command)

        for alias in item.aliases:
            group.add_command(cmd, alias)

def infer_command(output: str) -> str | None:
    """Infer the command name from the output path, if possible."""
    output_path = pathlib.Path(output)
    extension = output_path.suffix

    for item in config.typed.values:
        if extension == item.file_name_options.extension:
            return item.command
    return None

@click.group(name="touch")
def cli():
    """UNIX touch powered with Jinja2 templates.

    \b
    Example:
      $ ptools touch rfc /tmp/ptools-doc-examples/button --file_stem Button
    """

    pass

config = LazyConfigFile("touch", quiet=True, format="yaml", model=TouchConfig)
register_commands(cli, config.typed.values)

@cli.command(name='i')
@click.argument(
    "output",
    type=click.Path(exists=False, file_okay=True, dir_okay=True),
    required=True,
)
def infer(output):
    """Infer the touch command to use based on the output path."""
    command_name = infer_command(output)
    if command_name:
        command = cli.commands.get(command_name)
        if command:
            ctx = click.get_current_context()
            ctx.invoke(command, output=output)
        else:
            raise click.ClickException(messages["UNEXPECTED ERROR"])
    else:
        click.echo(messages["INFER_FAILED"])