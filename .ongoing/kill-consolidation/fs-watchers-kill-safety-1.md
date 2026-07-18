# Route `fs watchers kill`/`killname` through proc actions and add a self-PID guard

**Goal**: Fix the safety asymmetry where `ptools fs watchers killname` can signal the running `ptools` process itself, by routing both `fs` kill commands through `ptools.lib.proc.actions` and excluding the current PID.

**In scope**: `src/ptools/fs.py:383-407` (`watchers_kill`) and `src/ptools/fs.py:411-471` (`watchers_killname`).

**Out of scope**: `src/ptools/kill.py` and `src/ptools/proc.py` (later PRs in this task); the matching semantics of `killname` — the substring match over `command`/`exec_path`/`label` (`fs.py:426-433`) must behave identically after this change; `_get_watcher_data` and the label CRUD at `fs.py:476`.

**Description**: `src/ptools/lib/proc/actions.py` already exists as the shared home for process actions — its module docstring (`actions.py:1-6`) says so explicitly: "Process actions shared by the `proc` CLI and TUI. Every action returns a human-readable success message and raises `ActionError` with a human-readable reason on failure, so both frontends can surface results uniformly." `fs.py` does not use it. It is a third independent `os.kill` implementation.

`watchers_kill` (`fs.py:383-407`) inlines `import signal, os`, picks `SIGKILL`/`SIGTERM`, calls `os.kill`, and hand-writes the same three error branches `actions._kill` already provides at `actions.py:21-27` — down to nearly identical message strings ("Permission denied for PID {pid}. Try with sudo." appears verbatim in both `fs.py:405` and `actions.py:27`). It adds a bare `except Exception` at `fs.py:406`.

`watchers_killname` (`fs.py:411-471`) repeats the same block a fourth time at `fs.py:459-471`, inside a loop over matched processes.

The safety-relevant part is the asymmetry between the three implementations. `src/ptools/proc.py:357` does `targets.pop(os.getpid(), None)  # never kill ourselves` before signalling anything. `grep -rn "getpid" src/ptools/` returns that line and nothing else — it is the only self-PID guard in the entire source tree. So `ptools fs watchers killname ptools` (or any substring matching the running process's command or exec path) will attempt to signal the `ptools` process executing the command. Since the match is a substring over `exec_path` as well as `command` (`fs.py:428-432`), a broad needle like `py` or a path fragment can hit it without the user intending to.

`watchers_killname` also has no confirmation gate. `watchers_kill` has `@click.confirmation_option` (`fs.py:386`), and `proc kill` prompts unless `--yes` (`proc.py:371`), but `killname` — the one that can match many processes at once — kills immediately unless `--dry-run` is passed.

The fix: replace both inline `os.kill` blocks with `actions.terminate(pid, force=force)` wrapped in `except actions.ActionError`, matching the pattern `proc.py:376-379` already uses, and filter `os.getpid()` out of the match list in `killname` before the confirmation and the kill loop.

Note both commands carry `@require.os(["darwin"])` (`fs.py:387`, `fs.py:423`) because `_get_watcher_data` shells out to macOS tooling. `actions.terminate` is portable and does not narrow that; the decorator stays as is.

**Acceptance criteria**:
- Neither `watchers_kill` nor `watchers_killname` calls `os.kill` directly; both go through `ptools.lib.proc.actions`.
- `ptools fs watchers killname <substring matching the running ptools process> --dry-run` does not list the current process's PID.
- The same command without `--dry-run` does not signal the current process.
- `ptools fs watchers killname` prompts for confirmation before killing, or requires an explicit `--yes`/`-y`; `--dry-run` still bypasses the prompt because it kills nothing.
- Success and error output for `ptools fs watchers kill <pid>` is unchanged for the three existing cases (success, `ProcessLookupError`, `PermissionError`).
- `--dry-run` output format for `killname` is unchanged, including the `label="..."` and `(N fds)` fragments (`fs.py:452-454`).
- `.venv/bin/python3 -m pytest` passes.

**Depends on**: none

**Notes**: Verified 2026-07-18. `sed -n '375,475p' src/ptools/fs.py` shows both inline `os.kill` implementations (lines 399 and 461) and confirms `killname` has no confirmation option and no self-PID filter. `cat -n src/ptools/lib/proc/actions.py` confirms `terminate` at line 30, `kill_tree` at line 36, `ActionError` at line 17, and the duplicated error strings at lines 25-27. The self-PID asymmetry was verified with `grep -rn "getpid" src/ptools/`, which returns exactly one line: `src/ptools/proc.py:357`.

There is currently no test anywhere covering kill behavior — `grep -rln "kill" tests/` returns nothing. This PR is the right place to add the first one: a `--dry-run` test asserting the current PID is excluded needs no real signals and can be written against `CliRunner`.

This PR is deliberately first in the task: it is the smallest slice, it is the only safety-relevant one, and it does not depend on any decision about which command should ultimately own name-based killing.

**Status**: proposed — not approved
