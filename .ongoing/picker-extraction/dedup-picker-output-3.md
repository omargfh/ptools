# Collapse the three TTY picker-output constructors

**Goal**: Have one `always_prefer_tty` output constructor instead of three near-identical ones.

**In scope**: `src/ptools/utils/config.py:469-480` (`_picker_output`) and `src/ptools/projects.py:287` (inline `create_output(always_prefer_tty=True)`), both redirected to `src/ptools/lib/tui/select.py:287` (`picker_output`).

**Out of scope**: The picker adapters themselves; any change to which output a command actually chooses.

**Description**: Verified 2026-07-19 on staging, three constructors now do the same thing:

- `src/ptools/lib/tui/select.py:287` — `picker_output()`, the shared one
- `src/ptools/utils/config.py:469` — `_picker_output()`, a local duplicate whose docstring already cites `projects.py`
- `src/ptools/projects.py:287` — the call inlined directly

AGENTS.md value 6 says extract at the third occurrence; this is exactly the third. `migrate-picker-callers-2.md` left all three in place because `projects.py` was out of its scope and `config.py`'s in-scope range covered only the nested `select` closure.

**Acceptance criteria**:
- `config.py` and `projects.py` call `ptools.lib.tui.select.picker_output()`; no other definition of the same thing remains.
- `grep -rn "always_prefer_tty" src/` shows exactly one construction site.
- Interactive behavior is unchanged — the picker still renders on the terminal when stdout is redirected.

**Depends on**: none — `add-shared-picker-helpers-1.md` and `migrate-picker-callers-2.md` have both landed.

**Notes**: Pure dedup, no behavior change intended. `projects.py` carries a comment explaining why `always_prefer_tty=True` is needed; move it to the shared helper rather than dropping it.

**Status**: proposed — not approved
