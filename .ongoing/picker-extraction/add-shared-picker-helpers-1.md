# Add shared select/text picker helpers to lib/tui/select.py

**Goal**: Give `ptools.lib.tui.select` the `select`/`text` adapter pair that four modules currently each define for themselves — without changing any caller yet.

**In scope**: New helper functions in `src/ptools/lib/tui/select.py` and their tests.

**Out of scope**: Migrating callers (see `migrate-picker-callers-2.md`); `SelectApp`/`ask_text` behaviour; the `projects.py` picker call sites.

**Description**: The same thin adapter over `SelectApp`/`ask_text` is defined four times (verified 2026-07-18):

| Site | `_select` | `_text` |
| --- | --- | --- |
| `src/ptools/proc.py` | `:40-47` | `:50-54` |
| `src/ptools/touch.py` | `:326-331` | `:334-336` |
| `src/ptools/literals.py` | `:23-28` | `:31-33` |
| `src/ptools/utils/config.py` | `:587-593` (nested `select`) | via `ask_value`, `:617-649` |

`_text` is byte-identical across `proc.py`, `touch.py`, and `literals.py` — same signature, same one-line body, same docstring ("Prompt for a single line of text with a dim placeholder example."). `_select` in `proc.py` and `touch.py` is likewise identical apart from the annotation. AGENTS.md's rule is "extract at the third occurrence"; this is the fourth, and it is already a documented convention ("Reuse `ptools.lib.tui.select.SelectApp` / `ask_text` for any new interactive prompt") that stops one level short of the adapter everyone actually writes.

They have already drifted, which is the concrete cost:

- **`output=` is missing from two of the four.** `config.py:587` and `projects.py:300` thread a TTY-preferring prompt_toolkit output; `proc.py:47` and `touch.py:331` do not. The reason it matters is documented at `config.py:407-418` and `projects.py:281-287`: `always_prefer_tty=True` renders the picker to a real terminal instead of into a pipe the caller is capturing a value from. Any command whose stdout is piped and whose picker lacks `output=` writes raw UI into that pipe.
- **`literals.py:23-28` silently diverges.** It builds `LiteralsApp` (a `SelectApp` subclass, `literals.py:16-20`) with `selected_text="Selected: {}"`, so it is a variant rather than a copy — the shared helper must accommodate it, not assume uniformity.
- **`touch.py:326`'s annotation is wrong.** It declares `options: list[tuple[str, str]]`, but `touch.py:384-392` and `:399-400` pass 3-tuples. `SelectApp` genuinely accepts both — `_normalize` at `select.py:105-108` unpacks `value, label, *rest` — so the annotation is the thing that's wrong, and each copy is free to get it wrong independently. `proc.py:40` writes the looser `list[tuple]`.

Extract into `src/ptools/lib/tui/select.py`, next to the classes they wrap. This PR adds them only; nothing changes behaviour.

**Acceptance criteria**:
- `ptools.lib.tui.select` exports a select helper and a text helper covering every current call shape: `options`, `message`/`title`, `selected`, `placeholder`, `default`, `output`, and `selected_text` (or an `app_cls` hook) for the `literals.py` variant.
- The select helper's options parameter is annotated to accept both 2- and 3-tuples, matching `_normalize` (`select.py:105-108`).
- A `picker_output()` helper returns the `always_prefer_tty=True` output, with the rationale from `config.py:407-418` carried into its docstring.
- Helpers are covered by tests using `create_pipe_input`/`DummyOutput`, per `SelectApp`'s documented testing hook (`select.py:55-57`).
- No existing module is modified; the full suite passes.

**Depends on**: none

**Notes**: `config.py:407-418`'s `_picker_output` is the existing implementation to lift. Keep the helpers' internal imports lazy the way `proc.py:45` and `config.py:589` already do — `prompt_toolkit` is a heavy import and `main.py`'s `LazyGroup` dispatch exists to avoid paying for it. Decide whether the text helper keeps `.strip() or None` (as `config.py:614,649` apply at the call site) or leaves that to callers; `proc.py`/`touch.py`/`literals.py` return the raw string today, so folding it in would be a behaviour change and belongs in the migration PR if anywhere.

**Status**: proposed — not approved
