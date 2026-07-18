# Retire the duplicate name-based kill surface

**Goal**: Pick one canonical command for killing processes by name and retire the other two entry points, so the same operation stops having three spellings with three different flag sets.

**In scope**: The user-facing command surface of `ptools kill process` (`src/ptools/kill.py:39`), `ptools fs watchers killname` (`src/ptools/fs.py:411`), and `ptools proc kill --where` (`src/ptools/proc.py:323`); the `"kill"` entry in `src/ptools/main.py:39-41` if the standalone group is dropped.

**Out of scope**: `ptools proc kill`'s own behavior — it is the intended survivor and does not change; `src/ptools/lib/proc/actions.py`; `ptools fs watchers list` and the watcher label CRUD (`fs.py:349`, `fs.py:476`), which are genuinely `fs`-specific and stay.

**Description**: After PRs 1 and 2 of this task, all three implementations share `ptools.lib.proc.actions` and the safety behavior is uniform. What remains is that the same *feature* is reachable three ways with three different contracts:

| Command | Selector | Flags |
| --- | --- | --- |
| `ptools kill process NAME` | `pgrep` name match | none (see PR 2 for the added ones) |
| `ptools fs watchers killname NAME` | substring over command/exec_path/label, restricted to watcher processes (`fs.py:426-433`) | `--force`, `--dry-run` |
| `ptools proc kill --where 'name~NAME'` | full query expression (`proc.py:344-350`) | `--force`, `--tree`, `--dry-run`, `--yes` |

`ptools proc kill --where 'name~foo'` and `ptools fs watchers killname foo` are the same operation, and `proc kill` is the strict superset: its `--where` grammar expresses the substring match (`name~foo`) plus port, CPU, and boolean combinations (`proc.py:311-313` documents `'port=3000'` and `'name~node & cpu>90'`), and it alone offers `--tree` and a confirmation gate. `proc kill` is also the only one that already had the self-PID guard (`proc.py:357`) before this task.

**Recommendation: `ptools proc kill` is canonical.** It has the richest selector, the most complete flag set, the confirmation prompt, and it is the one already wired to the TUI's action layer. The other two should be reduced to thin aliases or removed:

- `fs watchers killname` — the honest replacement is `proc kill --where 'name~NAME'`. The one thing it can express that `proc kill` cannot is "restrict to processes that hold file-watch descriptors", which is what `_get_watcher_data` provides. If that filter is worth keeping, the right shape is a `proc kill` predicate (e.g. `watcher=true`), not a separate command under `fs`. If it is not worth keeping, delete `killname` and point the docstring of `fs watchers list` at `proc kill`.
- `kill port` — worth keeping as a top-level convenience. `ptools kill port 3000` is meaningfully shorter than `ptools proc kill --where 'port=3000'`, and after PR 2 it is a one-line wrapper over `actions.kill_by_port`. Keeping it costs nothing.
- `kill process` — subsumed with no ergonomic gain; `ptools proc kill --where 'name~NAME'` is barely longer and strictly more capable. Retire it.

That leaves `ptools kill` as a group with a single `port` subcommand. Whether to keep it at top level or fold it in as `ptools proc kill-port` is the remaining open question; folding it in removes an entry from `COMMANDS` (`main.py:39-41`) and puts every process action under one group, at the cost of a longer command for the most common case.

**Acceptance criteria**:
- Exactly one command performs name-based process killing.
- `ptools proc kill --where 'name~<name>' --dry-run` reproduces the process set that `ptools fs watchers killname <name> --dry-run` selected before the change, for at least one real watcher process — or, if the watcher restriction is preserved as a predicate, the predicate reproduces it exactly.
- Any retired command is either gone (Click reports "No such command") or emits a deprecation notice naming its replacement; it must not silently keep working.
- `docs/cli.rst` renders no two commands with the same described purpose (it renders the live tree, so this follows from the command changes).
- `.venv/bin/python3 -m pytest` passes.
- `grep -rn "os.kill\|\"kill\", \"-9\"\|kill -9" src/ptools/` returns matches only inside `src/ptools/lib/proc/actions.py`.

**Depends on**: `fs-watchers-kill-safety-1.md`, `kill-cli-on-proc-actions-2.md` — both must land first. Retiring a command surface before the survivors are safe and share an implementation would mean removing the escape hatch before the replacement is trustworthy.

**Notes**: Verified 2026-07-18. The three implementations were confirmed with `sed -n '1,70p' src/ptools/kill.py`, `sed -n '315,385p' src/ptools/proc.py`, and `sed -n '375,475p' src/ptools/fs.py`. `proc kill`'s flag set is at `proc.py:316-320`; its `--where` examples at `proc.py:311-313`; its self-PID guard at `proc.py:357`. `fs watchers killname`'s substring matching is at `fs.py:426-433`. `grep -rn "getpid" src/ptools/` returns only `proc.py:357`, confirming `proc kill` was the sole guarded implementation. `grep -rln "kill" tests/` returns nothing — no kill behavior is covered by any test.

This PR is a user-facing removal. Unlike PRs 1 and 2, which are pure internal consolidation, this one breaks muscle memory and any scripts using the retired spellings. It needs explicit owner sign-off on *which* command survives before any code is written — the recommendation above is a proposal, not a decision.

The empty test coverage across all three implementations means the equivalence claim in the acceptance criteria has to be verified by hand against real processes (with `--dry-run`), not by a passing suite.

**Status**: proposed — not approved
