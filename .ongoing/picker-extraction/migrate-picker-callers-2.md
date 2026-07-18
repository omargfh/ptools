# Migrate the four picker adapters onto the shared helpers

**Goal**: Delete the four local `_select`/`_text` copies in favour of the shared helpers, fixing the drift between them.

**In scope**: `src/ptools/proc.py:40-54`, `src/ptools/touch.py:326-336`, `src/ptools/literals.py:23-33`, `src/ptools/utils/config.py:587-593`, and their call sites.

**Out of scope**: The helpers themselves (see `add-shared-picker-helpers-1.md`); `projects.py:225,300`, which call `SelectApp` directly and are not part of the duplicated pair; any change to what the pickers display.

**Description**: Replace each local adapter with the shared helper added by the previous PR. Two of the four migrations are behaviour changes, and they are the point of the exercise:

**`proc.py` and `touch.py` gain `output=`.** Neither threads a TTY-preferring output today (`proc.py:47`, `touch.py:331`), so if either command's stdout is a pipe, prompt_toolkit falls back to a `PlainTextOutput` that writes picker UI into the pipe. `config.py:407-418` and `projects.py:281-287` both document this failure mode and the `always_prefer_tty=True` fix. Adopting the shared helper closes the gap by default — verify each affected command still renders correctly when stdout is *not* a pipe, since that is the common case.

**`touch.py`'s annotation stops lying.** `touch.py:326` declares `list[tuple[str, str]]` while `:384-392` and `:399-400` pass 3-tuples. The shared helper's annotation covers both, so the mismatch disappears rather than being restated.

The other two are mechanical: `literals.py:23-28` needs its `LiteralsApp` + `selected_text="Selected: {}"` variant expressed through the helper's hook, and `config.py:587-593`'s nested `select` closure collapses to a direct call (its callers at `:610-615` and `:617-649` already pass `output` explicitly).

**Acceptance criteria**:
- No `_select` or `_text` definition remains in `proc.py`, `touch.py`, or `literals.py`; no nested `select` remains in `config.py`'s `config_to_CLI`.
- Every picker in those four modules is invoked with a TTY-preferring output.
- `ptools proc`, `ptools touch`, `ptools lget`, and `ptools settings get` still render their pickers and return the same values when run on a terminal.
- Each of those commands, run with stdout redirected to a file, writes only its intended output to that file — no picker UI.
- `literals.py`'s picker still shows its `Selected: {}` confirmation line.
- The full suite passes; existing picker tests are updated rather than deleted.

**Depends on**: `add-shared-picker-helpers-1.md`

**Notes**: Test headlessly with `app.run_test()`-style pilot input or `create_pipe_input`/`DummyOutput` (`select.py:55-57`) rather than a real terminal, per AGENTS.md. The "stdout redirected to a file" criterion is the one that actually catches the `output=` regression class and is worth a test rather than a manual check. Migrate one module per commit inside the PR so a rendering regression bisects cleanly — `config.py` last, since it has the most call sites.

**Status**: proposed — not approved
