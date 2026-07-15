# `ptools touch new` — scaffold a template interactively

**Goal**: Add a `ptools touch new` wizard that creates a new `touch.yaml` template entry, using an editor for the multi-line template body.

**In scope**: a new `new` subcommand in `src/ptools/touch.py`; prompts (via `SelectApp`/`ask_text`, matching `touch wizard`) for `command`, `group`, `name`, `description`, and output extension; opens an editor for `template_string`; appends the resulting `TouchItem` to the user's `touch` config.

**Out of scope**: editing or removing existing templates; hand-authoring `arguments`/`ArgumentSpec` metadata beyond what `model_post_init`'s Jinja2 `_undeclared_vars` discovery already infers; `GroupMeta` (`name`/`description`) editing for new groups.

**Description**: The only way to add a template today is hand-editing `~/.ptools/touch.yaml` (or the packaged `src/ptools/starters/touch.yaml`) — there is no CLI path to create one, even though `touch wizard`/`w` (just built) makes *using* templates fully interactive. Template bodies are multi-line Jinja2 (see the Vue SFC entry in `src/ptools/starters/touch.yaml`), which doesn't fit `ask_text`'s single-line prompt. Per explicit direction: author the template body in an editor rather than a text prompt. Click ships `click.edit()` (confirmed present, `click` 8.3.1 in `.venv`) for exactly this shape — it opens `$EDITOR` (or a platform default) with the given seed text, handles temp-file creation/cleanup, and returns `None` if the file is left unchanged/empty. Use `click.edit(editor=os.environ.get("EDITOR", "vim"))` so the user's ask ("use vim... when giving the user the option to craft a template") is the default when `$EDITOR` isn't set, without hardcoding vim over the user's actual editor preference.

**Acceptance criteria**:
- `ptools touch new` prompts for command name, group, display name, description, and output extension using the same `SelectApp`/`ask_text` primitives as `touch wizard`.
- The template body is authored via `click.edit(editor=os.environ.get("EDITOR", "vim"))`; an aborted or empty edit cancels the wizard without writing anything.
- A command-name collision with an existing entry is rejected with a clear error *before* the editor opens, not after the user has already written the template.
- On completion, the new entry is appended to the user's `touch.yaml` config and is selectable from a subsequent `ptools touch wizard` invocation.
- The new template's undeclared Jinja2 variables are populated via the existing `model_post_init` discovery — no separate argument-registration step for the common case.

**Depends on**: none

**Notes**: ground the write path in whatever `LazyConfigFile` read/write method the rest of `touch.py` already uses to persist `TouchConfig.values` — don't add a parallel persistence path.

**Status**: proposed — not approved
