"""Template-driven ``touch`` command: create files from Jinja2 templates.

Loads a user config (``~/.ptools/touch.yaml``) describing a list of
:class:`TouchItem` entries and dynamically registers one Click subcommand
per entry under the :data:`cli` group. Each subcommand renders its
template to the output path the user provides.

.. note::
    Because commands are registered in a loop, the per-iteration ``item``
    value **must** be bound as a default argument on the handler
    (``def handler(..., _item=item, ...)``). Without that binding, every
    registered command would close over the same variable by reference
    and all end up using the last iteration's :class:`TouchItem` —
    producing identical output for every command. See
    ``tests/test_touch.py::TestCommandRegistration`` for a regression
    test.
"""

from __future__ import annotations

import os
import pathlib
import re
import shutil
import tempfile

import click
from jinja2 import Environment, Template, meta
from pydantic import BaseModel, computed_field, field_serializer, model_validator, BeforeValidator

import ptools.utils.require as require
from ptools.lib.tui.select import picker_output, select, text
from ptools.utils.cases import CaseConverter, cases
from ptools.utils.config import LazyConfigFile
from ptools.utils.decorator_compistor import DecoratorCompositor
from ptools.utils.print import FormatUtils

# Optional: syntax-highlighted wizard previews when pygments is around.
_pygments_available = require.optional_library("pygments", pypi_name="Pygments")

messages = {
    "UNEXPECTED ERROR": FormatUtils.error("An unexpected error occurred. Please check your configuration and try again."),
    "INFER_FAILED": FormatUtils.error("Could not infer a command for the given output path. Please specify the command explicitly."),
    "NO_TEMPLATES": FormatUtils.warning("No touch templates configured. Add entries to ~/.ptools/touch.yaml first."),
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


class ArgumentSpec(BaseModel):
    """Metadata for one template variable.

    ``help`` feeds the generated ``--option`` help text, ``example`` is
    shown as a dim placeholder in the wizard, and ``default`` is used
    when the variable is not provided (CLI and wizard alike). Plain
    string argument values in the config are shorthand for ``help``.
    """

    help: str = "<value>"
    example: str = ""
    default: str = ""


class GroupMeta(BaseModel):
    """Per-group metadata rendered in the wizard's group picker."""

    # Display name shown in the picker; falls back to the group key.
    name: str = ""
    description: str = ""


class TouchItem(BaseModel):
    command: str
    aliases: list[str] = []
    group: str = "default"
    description: str
    template_string: str
    arguments: dict[str, str | ArgumentSpec] = {}
    file_name_options: FileNameOptions = FileNameOptions()
    # Display name shown in the wizard; falls back to the command.
    name: str = ""
    # Example output path, shown as the wizard's placeholder.
    example: str = ""

    # Populated in model_post_init — not user-supplied.
    _undeclared_vars: set[str] = set()

    model_config = {"arbitrary_types_allowed": True}

    @field_serializer("template")
    def serialize_template(self, template: Template) -> str:
        """Serialize the Jinja2 Template object to its source string."""
        return self.template_string

    @computed_field
    @property
    def template(self) -> Template | None:
        """Return the Jinja2 Template object, or None if not initialized."""
        return Template(self.template_string)

    def model_post_init(self, context) -> None:
        super().model_post_init(context)

        env = Environment()
        parsed = env.parse(self.template_string)
        self._undeclared_vars = meta.find_undeclared_variables(parsed)

        # Discovered vars become arguments (explicit values take
        # precedence); plain-string specs are shorthand for help text.
        explicit = {
            name: spec if isinstance(spec, ArgumentSpec) else ArgumentSpec(help=spec)
            for name, spec in self.arguments.items()
        }
        self.arguments = {
            **{var: ArgumentSpec() for var in self._undeclared_vars},
            **explicit,
        }

class TouchConfig(BaseModel):
    values: list[TouchItem] = []
    groups_meta: dict[str, GroupMeta] = {}


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


def perform_touch(
    item: TouchItem,
    output_raw: str,
    casing: str | None,
    args: dict[str, str],
) -> None:
    """Resolve the output path and write *item*'s rendered template to it.

    Shared by the per-template subcommands and the interactive wizard so
    both go through identical overwrite/render/write behavior.
    """
    resolved = resolve_output(output_raw, item.file_name_options, casing, args)

    if resolved.exists():
        click.confirm(f"'{resolved}' already exists. Overwrite?", abort=True)

    resolved.parent.mkdir(parents=True, exist_ok=True)
    ctx = build_template_context(resolved, args)

    if item.template is None:
        click.echo(FormatUtils.error(f"Template for command '{item.command}' is not initialized."))
        return

    try:
        rendered = item.template.render(**ctx)
        resolved.write_text(rendered)
        click.echo(FormatUtils.success(f"File '{resolved}' created."))
    except Exception as e:
        click.echo(FormatUtils.error(f"Error writing '{resolved}': {e}"))


def _make_command(item: TouchItem) -> click.Command:
    """Build a Click command for a single :class:`TouchItem`."""
    fopts = item.file_name_options

    extra_options = DecoratorCompositor.from_list(
        [
            click.option(
                f"--{name}",
                type=str,
                required=False,
                default=spec.default or None,
                help=spec.help,
            )
            for name, spec in item.arguments.items()
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
    def handler(output: str, casing: str | None, _item=item, **kwargs):
        args = {k: v for k, v in kwargs.items() if v is not None}
        perform_touch(_item, output, casing, args)

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


def _highlight_preview(code: str, filename: str) -> str:
    """Syntax-highlight *code* for the terminal preview.

    Uses pygments when it is installed and has a lexer registered for
    *filename*; otherwise returns the code unchanged.
    """
    if not _pygments_available():
        return code

    from pygments import highlight
    from pygments.formatters import Terminal256Formatter
    from pygments.lexers import get_lexer_for_filename
    from pygments.util import ClassNotFound

    try:
        lexer = get_lexer_for_filename(filename)
    except ClassNotFound:
        return code
    return highlight(code, lexer, Terminal256Formatter())


# Context names the wizard never prompts for: template builtins that are
# functions (prompting for a string would shadow them and break rendering).
WIZARD_SKIPPED_VARS = {"convert_case", "env"}
# Context names whose values are derived from the output path/environment;
# prompting for them is an optional override.
DERIVED_VARS = {"file_stem", "file_suffix", "file_path", "file_name", "cwd", "home", "user"}


def _select_item(
    items: list[TouchItem], groups_meta: dict[str, GroupMeta], output=None
) -> TouchItem | None:
    """Pick a template in two arrow-key steps: group first, then template.

    The group step is skipped when only one group is configured. Returns
    ``None`` if the user cancels either step. ``output`` is a
    TTY-preferring prompt_toolkit output (see
    :func:`~ptools.lib.tui.select.picker_output`).
    """
    groups: dict[str, list[TouchItem]] = {}
    for item in sorted(items, key=lambda x: x.group):
        groups.setdefault(item.group, []).append(item)

    def meta(group_key: str) -> GroupMeta:
        return groups_meta.get(group_key, GroupMeta())

    if len(groups) == 1:
        group = next(iter(groups))
    else:
        group = select(
            [
                (
                    key,
                    f"{meta(key).name or key} ({len(members)})",
                    meta(key).description,
                )
                for key, members in groups.items()
            ],
            "Select a group:",
            output=output,
        )
        if group is None:
            return None

    members = groups[group]
    command = select(
        [(m.command, m.name or m.command, m.description) for m in members],
        f"Select a template ({meta(group).name or group}):",
        output=output,
    )
    if command is None:
        return None
    return next(m for m in members if m.command == command)


def _prompt_output(item: TouchItem, output=None) -> str:
    """Prompt for the output path until a non-empty answer is given."""
    example = item.example or f"my-file{item.file_name_options.extension}"
    while True:
        value = text("Output path:", placeholder=f"e.g. {example}", output=output).strip()
        if value:
            return value


def _prompt_arguments(item: TouchItem, output=None) -> dict[str, str]:
    """Prompt for each template variable; blank answers are omitted.

    A blank answer takes the argument's configured default when there is
    one; otherwise the variable falls back to the derived context values
    (``file_stem``, ``cwd``, ...) or renders empty.
    """
    args: dict[str, str] = {}
    for name, spec in sorted(item.arguments.items()):
        if name in WIZARD_SKIPPED_VARS:
            continue
        if spec.default:
            placeholder = f"default: {spec.default}"
        elif spec.example:
            placeholder = f"e.g. {spec.example}"
        elif spec.help != "<value>":
            placeholder = spec.help
        elif name in DERIVED_VARS:
            placeholder = "leave blank to use the derived value"
        else:
            placeholder = "optional"
        value = text(f"{name}:", placeholder=placeholder, output=output)
        if value:
            args[name] = value
        elif spec.default:
            args[name] = spec.default
    return args


@cli.command(name="wizard")
def wizard():
    """Interactively create a file from a configured template.

    Pick a group and a template with the arrow keys (enter confirms,
    escape cancels), then answer prompts for the output path, filename
    casing, and template variables. The rendered file is previewed
    before anything is written.

    \b
    Example:
      $ ptools touch wizard
      ? Select a group:
      ❯ docs (2)
        web (1)
      ? Select a template (docs):
      ❯ rfc - RFC document template
      ? Output path: /tmp/ptools-doc-examples/button
      ...
    """
    items = config.typed.values
    if not items:
        click.echo(messages["NO_TEMPLATES"])
        return

    output = picker_output()
    item = _select_item(items, config.typed.groups_meta, output)
    if item is None:
        click.echo(FormatUtils.warning("No template selected."))
        return
    fopts = item.file_name_options

    output_raw = _prompt_output(item, output)

    casing_choice = select(
        [(c, c) for c in ("keep", *cases)],
        "Filename casing:",
        selected=fopts.casing or "keep",
        output=output,
    )
    if casing_choice is None:
        click.echo(FormatUtils.warning("Cancelled."))
        return
    casing = None if casing_choice == "keep" else casing_choice

    args = _prompt_arguments(item, output)

    resolved = resolve_output(output_raw, fopts, casing, args)

    if item.template is None:
        click.echo(FormatUtils.error(f"Template for command '{item.command}' is not initialized."))
        return

    rendered = item.template.render(**build_template_context(resolved, args))

    click.echo()
    click.echo(FormatUtils.bold(f"Preview of '{resolved}':"))
    click.echo(FormatUtils.highlight("-" * 60, "cyan"))
    click.echo(_highlight_preview(rendered, resolved.name))
    click.echo(FormatUtils.highlight("-" * 60, "cyan"))

    click.confirm(f"Write to '{resolved}'?", abort=True, default=True)
    perform_touch(item, output_raw, casing, args)


cli.add_command(wizard, "w")

# Sentinel option value for "create a new group" in the new-template wizard's
# group picker (never collides with a real group key).
_NEW_GROUP = "__new_group__"


def _prompt_nonempty(message: str, placeholder: str = "", output=None) -> str:
    """Prompt via :func:`~ptools.lib.tui.select.text` until a non-blank answer is given."""
    while True:
        value = text(message, placeholder=placeholder, output=output).strip()
        if value:
            return value


def _group_picker_options(
    items: list[TouchItem], groups_meta: dict[str, GroupMeta]
) -> list[tuple[str, str, str]]:
    """Build ``(value, label, description)`` options for every known group.

    Mirrors the group-option shape ``_select_item`` builds for picking a
    template, including groups that only exist in ``groups_meta`` (no
    templates yet).
    """
    groups: dict[str, list[TouchItem]] = {}
    for item in items:
        groups.setdefault(item.group, []).append(item)
    for key in groups_meta:
        groups.setdefault(key, [])

    def meta(group_key: str) -> GroupMeta:
        return groups_meta.get(group_key, GroupMeta())

    return [
        (key, f"{meta(key).name or key} ({len(members)})", meta(key).description)
        for key, members in sorted(groups.items())
    ]


# A couple of DERIVED_VARS entries used as illustrative examples in the
# new-template editor seed - pulled from the set (not hardcoded
# independently) so the seed can't silently drift out of sync with it.
_SEED_EXAMPLE_VARS = tuple(v for v in ("file_stem", "cwd") if v in DERIVED_VARS)

# Matches a Jinja2 `{# ... #}` comment (non-greedy, spans lines).
_JINJA_COMMENT_RE = re.compile(r"\{#.*?#\}", re.DOTALL)


def _safe_filename_stub(name: str) -> str:
    """Sanitize *name* for use as a temp-file basename.

    Defensive: the command name comes from free-text input and nothing
    upstream restricts its characters, but it becomes a real filename
    here (e.g. a stray ``/`` would otherwise try to create a subdirectory).
    """
    return re.sub(r"[^\w.-]", "_", name) or "template"


def _template_seed(command: str) -> str:
    """Seed text for a new template's editor buffer.

    Written as a Jinja2 ``{# ... #}`` comment: the lexer strips comments
    before ``model_post_init``'s undeclared-variable discovery ever runs,
    so the illustrative ``{{ var }}`` examples inside it are never
    mistaken for real template variables and never leak into rendered
    output.
    """
    examples = " or ".join(f"{{{{ {var} }}}}" for var in _SEED_EXAMPLE_VARS)
    builtins_desc = " and ".join(
        f"`{var}(...)`" for var in sorted(WIZARD_SKIPPED_VARS)
    )
    return (
        "{#\n"
        f"  Jinja2 template for the `{command}` touch command.\n"
        "\n"
        f"  Interpolate values with double curly braces, e.g. {examples}.\n"
        "  Any other {{ name }} you reference below becomes a prompted\n"
        "  argument automatically - no separate registration step needed.\n"
        "\n"
        f"  {builtins_desc} are also available as functions inside the template.\n"
        "\n"
        "  Replace this comment with your template body.\n"
        "#}\n"
    )


def _is_blank_template(content: str) -> bool:
    """True if *content* has no real body once Jinja ``{# #}`` comments are stripped."""
    return not _JINJA_COMMENT_RE.sub("", content).strip()


def _author_template_body(command: str) -> str | None:
    """Open ``$EDITOR`` (or vim) on a ``<command>.jinja`` file and return its content.

    ``click.edit(filename=...)`` edits that file in place and always
    returns ``None`` - its text-returning mode only applies when no
    ``filename`` is given (see click's ``termui.edit`` docstring) - so the
    file is created here, in a scratch temp dir, named after the command
    and seeded with syntax help, and its post-edit content is read back
    directly rather than relying on ``click.edit``'s return value.

    Returns ``None`` if the author left the file with no real body
    (unchanged, emptied, or comment-only) - i.e. cancelled.
    """
    seed = _template_seed(command)
    tmpdir = tempfile.mkdtemp(prefix="ptools-touch-new-")
    try:
        path = os.path.join(tmpdir, f"{_safe_filename_stub(command)}.jinja")
        pathlib.Path(path).write_text(seed)
        click.edit(filename=path, editor=os.environ.get("EDITOR", "vim"))
        content = pathlib.Path(path).read_text()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    if _is_blank_template(content):
        return None
    return content


@cli.command(name="new")
def new():
    """Interactively author a new touch template.

    Prompts for the command name, group, display name, description, and
    output extension, then opens ``$EDITOR`` (or vim, if unset) to author
    the Jinja2 template body. Undeclared Jinja2 variables in the body are
    auto-discovered as arguments, same as hand-authored config entries.
    The new entry is appended to the user's touch.yaml config and is
    immediately usable via ``touch wizard``.

    \b
    Example:
      $ ptools touch new
      ? Command name: rfc
      ? Select a group:
      ❯ docs (2)
        + New group
      ? Display name: RFC Document
      ? Description: RFC document template
      ? Output extension: .md
      (opens $EDITOR to author the template body)
      Added new template 'rfc'.
    """
    items = config.typed.values
    groups_meta = config.typed.groups_meta
    existing_commands = {item.command for item in items}

    output = picker_output()
    command_name = _prompt_nonempty("Command name:", placeholder="e.g. rfc", output=output)
    if command_name in existing_commands:
        raise click.ClickException(
            f"A template with command '{command_name}' already exists."
        )

    group_options = _group_picker_options(items, groups_meta) + [
        (_NEW_GROUP, "+ New group", "Create a new group")
    ]
    group_choice = select(group_options, "Select a group:", output=output)
    if group_choice is None:
        click.echo(FormatUtils.warning("Cancelled."))
        return
    if group_choice == _NEW_GROUP:
        group = _prompt_nonempty("New group name:", placeholder="e.g. docs", output=output)
    else:
        group = group_choice

    name = text("Display name:", placeholder="e.g. RFC Document", output=output)
    description = text("Description:", placeholder="e.g. RFC document template", output=output)

    extension = text("Output extension:", placeholder="e.g. .md", output=output).strip()
    if extension and not extension.startswith("."):
        extension = f".{extension}"

    template_string = _author_template_body(command_name)
    if template_string is None:
        click.echo(FormatUtils.warning("Cancelled: no template body was written."))
        return

    fopts = FileNameOptions(extension=extension) if extension else FileNameOptions()
    new_item = TouchItem(
        command=command_name,
        group=group,
        description=description,
        template_string=template_string,
        name=name,
        file_name_options=fopts,
    )

    # Persist through ConfigFile.set() rather than mutating config.typed in
    # place: config.typed rebuilds a fresh TouchConfig from config.data on
    # every access, so a plain-list append wouldn't survive. The `template`
    # field (a live Jinja2 Template object, populated in model_post_init) is
    # excluded from the dump: it isn't YAML-serializable and is rebuilt from
    # template_string on next load anyway.
    updated_values = [*items, new_item]
    config.set(
        "values", [item.model_dump(exclude={"template"}) for item in updated_values]
    )

    click.echo(FormatUtils.success(f"Added new template '{new_item.command}'."))