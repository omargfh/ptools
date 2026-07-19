# Correct the replacement query offered for the retired kill commands

**Goal**: Make the documented replacement for `ptools fs watchers killname` actually cover what that command matched.

**In scope**: The `ptools proc kill --where ...` guidance in the docstrings left by `retire-duplicate-kill-surface-3.md` (`src/ptools/fs.py`, `src/ptools/kill.py`).

**Out of scope**: Reinstating the retired commands; changing `BARE_MATCH_FIELDS`; the query engine itself.

**Description**: `retire-duplicate-kill-surface-3.md` removed `fs watchers killname` and pointed users at `ptools proc kill --where 'name~NAME | exe~NAME'`. That query is narrower than the matcher it replaced.

Verified 2026-07-19 on staging: `src/ptools/lib/proc/model.py:86-88` defines

    BARE_MATCH_FIELDS = ("name", "comm", "cmd", "label", "bundle", "service", "container", "user")

so a **bare word** covers `label` and `cmd` but **not** `exe`, while the documented field-specific form covers `name` and `exe` but **not** `label` or `cmd`. The retired fs matcher scanned name, resolved `exec_path`, and `label`. Neither form alone reproduces it; `NAME | exe~NAME` does.

This matters because the retirement was justified by equivalence. A user following the current guidance to kill a watcher identified by its label will silently match nothing.

**Acceptance criteria**:
- The docstrings recommend a query covering name, cmd, label and exe (`NAME | exe~NAME`, or an explicit disjunction).
- A test, or a recorded manual check, shows the recommended query matches a process that only matches via `label`.
- No claim of equivalence remains that the query does not actually deliver.

**Depends on**: none

**Notes**: Found while merging `retire-duplicate-kill-surface-3.md`. That PR's own report measured the gap (6 of 8 PIDs reproduced with plain `name~X`) and chose `name~X | exe~X`, which closes the exec_path half but not the label half.

**Status**: proposed — not approved
