# Rebuild `ptools kill` on proc actions

**Goal**: Replace the `subprocess`-and-`kill -9` implementation in `src/ptools/kill.py` with calls into `ptools.lib.proc.actions`, so `ptools kill` stops shelling out, stops defaulting to SIGKILL, and stops swallowing every error.

**In scope**: `src/ptools/kill.py:15-37` (`kill_port`) and `src/ptools/kill.py:39-64` (`kill_process`).

**Out of scope**: `src/ptools/fs.py` (PR 1 of this task); `src/ptools/proc.py`'s `kill` command; whether `ptools kill` should continue to exist as a separate top-level command (PR 3); `src/ptools/lib/proc/actions.py` itself — this PR consumes it, it does not change it.

**Description**: `src/ptools/kill.py` is the oldest of the three kill implementations and the only one that never touches Python's signal API. `kill_port` (`kill.py:15-37`) runs `lsof -i :PORT` to test occupancy, then `lsof -t -i :PORT` to get PIDs, then `subprocess.run(["kill", "-9", pid])`. `kill_process` (`kill.py:39-64`) runs `pgrep NAME` and loops `kill -9` over the results.

Three concrete defects follow from that:

1. **SIGKILL is the only option.** Both commands hardcode `kill -9` (`kill.py:33`, `kill.py:58`). There is no `--force` flag because force is unconditional — processes never get a chance to clean up. Both other implementations default to SIGTERM and gate SIGKILL behind `--force`/`-9` (`proc.py:318`, `fs.py:385`, `actions.py:31`).
2. **`lsof -t -i :PORT` output is passed unsplit.** `kill.py:28-31` calls `.strip()` on the multi-line result and hands the whole string to `kill -9` as a single argv element. With more than one PID on the port, that argument is not a number and the `kill` invocation fails. The message at `kill.py:34` still reports success, because the return code is never checked. `actions.kill_by_port` (`actions.py:152-167`) already handles this correctly: it splits the output and filters with `isdigit()` (`actions.py:162`), and it additionally passes `-sTCP:LISTEN` (`actions.py:156`) so it targets listeners rather than every socket on the port.
3. **Errors are swallowed.** Both commands wrap their body in `except Exception` and `click.echo` the message (`kill.py:36-37`, `kill.py:63-64`) — never `err=True`, never a non-zero exit. `ptools kill port 3000` exits 0 whether it killed something, killed nothing, or failed outright, which makes it unusable in a script.

The replacements already exist. `actions.kill_by_port(port, force=False)` (`actions.py:152`) covers `kill port` exactly, and it is already the implementation the TUI uses (`src/ptools/lib/proc/app.py:815`) — so today the same user-facing operation has one correct implementation behind the TUI and one broken implementation behind the CLI. `actions.terminate(pid, force=False)` (`actions.py:30`) covers the per-PID signalling in `kill process`; `pgrep` can stay as the name lookup, or the module can reuse `proc.py`'s query path.

Both commands should also gain `--force/-9` (defaulting to SIGTERM) and the `os.getpid()` exclusion that `proc.py:357` has, since `pgrep ptools` will match the running process.

**Acceptance criteria**:
- `src/ptools/kill.py` contains no `subprocess` call that invokes `kill`; both commands go through `ptools.lib.proc.actions`.
- `ptools kill port <port with two or more listeners> --dry-run` lists every PID individually rather than one concatenated string.
- `ptools kill port <port>` sends SIGTERM by default; `ptools kill port <port> -9` sends SIGKILL.
- `ptools kill process <name>` never signals the PID of the running `ptools` process.
- A failed kill writes to stderr and exits non-zero; `ptools kill port <unused port> ; echo $?` prints a non-zero status.
- `ptools kill port` and `ptools kill process` produce output consistent with `actions`' message style (`"Sent SIGTERM to PID N."`), so all three frontends read alike.
- `.venv/bin/python3 -m pytest` passes.

**Depends on**: none — independent of `fs-watchers-kill-safety-1.md`, though both should land before `retire-duplicate-kill-surface-3.md`.

**Notes**: Verified 2026-07-18. `sed -n '1,70p' src/ptools/kill.py` confirms the `lsof`/`pgrep` shell-outs, the hardcoded `kill -9` at lines 33 and 58, the unsplit `.stdout.strip()` at lines 28-31, and the `except Exception` swallows at lines 36-37 and 63-64. `cat -n src/ptools/lib/proc/actions.py` confirms `kill_by_port` at line 152 with the `isdigit()` split at line 162 and `-sTCP:LISTEN` at line 156. `grep -rn "kill_by_port" src tests` returns exactly two hits — its definition and `src/ptools/lib/proc/app.py:815` — proving the CLI does not use it while the TUI does. Self-PID guard absence confirmed with `grep -rn "getpid" src/ptools/` → only `src/ptools/proc.py:357`.

`grep -rln "kill" tests/` returns nothing: there is no test coverage on `ptools kill` at all, so behavior changes here are unguarded. Add at least a `--dry-run`/no-match test for both subcommands as part of this PR.

Adding `--dry-run` to `kill port`/`kill process` is implied by the acceptance criteria above and is worth doing here rather than in a follow-up, since it is what makes the change testable without signalling real processes.

**Status**: proposed — not approved
