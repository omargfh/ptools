# Get the `tmp` development command out of the user-facing help

**Goal**: Stop `ptools --help` advertising `tmp` as "Temporary command for testing purposes." — either by deleting the command or by adding hidden-command support to `LazyGroup`.

**In scope**: The `"tmp"` entry in `src/ptools/main.py:95-98`, `src/ptools/tmp.py`, and — if the hide option is chosen — `LazyGroup.list_commands` (`main.py:129-131`) and `LazyGroup.format_commands` (`main.py:132-140`). The `flow read` docstring at `src/ptools/flow.py:48` is in scope for a one-line wording fix only.

**Out of scope**: Any other command in the `COMMANDS` dict; the lazy-import mechanism itself (`main.py:107-111`); `docs/cli.rst` (it renders the live Click tree, so it follows automatically).

**Description**: `src/ptools/main.py:95-98` registers `tmp` in the top-level `COMMANDS` dict with the short help "Temporary command for testing purposes.", and `LazyGroup.format_commands` (`main.py:132-140`) unconditionally renders every key of `COMMANDS` into `ptools --help`. A user running `ptools --help` therefore sees a command that announces itself as not for them, sitting in the same list as `vault` and `proc`.

`src/ptools/tmp.py` is 31 lines: it makes a `tempfile.mkdtemp(prefix="ptools-")`, substitutes the path into the given command (`tmp.py:22`), and runs it with `shell=True` in that directory (`tmp.py:28`). It is genuinely useful as a scratch-dir runner — `ptools tmp code` opens an editor in a fresh temp dir — so this is not a deadness finding like the other two files in this task. The problem is purely that its self-description and its presence in the public help are inconsistent with it being shipped.

There is a second, smaller instance of the same smell: `flow read`'s docstring at `src/ptools/flow.py:48` opens with "Development command to read from stdin and print the StreamValue representation." Because `docs/cli.rst` renders docstrings via `sphinx_click`, that sentence is published documentation telling users the command is not for them. Unlike `tmp`, `flow read` is registered normally (`flow.py:576`) and belongs in the CLI; only the wording needs fixing.

**The design question**: hiding is not free. `LazyGroup` has no hidden-command support — `list_commands` (`main.py:129-131`) returns `sorted(COMMANDS)` with no filtering, and `format_commands` (`main.py:132-140`) builds its rows straight from that list and the cached `short_help` strings. Click's usual `hidden=True` on the command object cannot help, because `format_commands` never loads the command; it reads only the dict. So hiding `tmp` requires either a `"hidden": True` key in the `COMMANDS` entries plus a filter in `format_commands`, or dropping the cached-short-help optimization and resolving each command to ask it. The first is a handful of lines and preserves lazy loading; the second defeats the purpose of `LazyGroup`.

So the three options are:

1. **Delete `tmp`.** Smallest diff, no new mechanism. Loses a working tool the owner presumably uses.
2. **Add a `hidden` key to `COMMANDS` and filter in `format_commands`.** Keeps `tmp` invokable, removes it from help, and gives the repo a reusable mechanism for any future dev-only command. Costs ~4 lines in `main.py`.
3. **Keep it and rewrite the short help** to describe what it actually does ("Run a command in a fresh temporary directory."). Zero mechanism, and arguably the honest fix — the command is not a testing stub, it is a scratch-dir runner with a bad name and a bad description.

**Recommendation: option 3 for `tmp`'s description, with option 2 only if the owner wants it genuinely hidden.** The command's behavior (`tmp.py:19-28`) is a legitimate shipped feature; the "for testing purposes" text is stale wording from when it was a stub, not an accurate label. Fixing the description costs one line and resolves the reported problem — the user-facing help no longer advertises a non-feature — without adding a hiding mechanism the repo does not otherwise need.

**Acceptance criteria**:
- `.venv/bin/ptools --help` contains no command described as "for testing purposes" or "temporary command".
- If option 1: `ptools tmp` exits non-zero with Click's "No such command" error, and `grep -rn "tmp" src/ptools/main.py` returns nothing.
- If option 2: `ptools --help` does not list `tmp`, but `ptools tmp echo hi` still runs and succeeds; a second entry marked hidden would also be omitted, proving the mechanism is general rather than special-cased on the name.
- If option 3: the `tmp` row in `ptools --help` describes the temp-directory behavior, and `ptools tmp echo hi` is unchanged.
- `.venv/bin/ptools flow read --help` no longer opens with "Development command".
- `.venv/bin/python3 -m pytest` passes; `tests/test_main_cli.py` in particular must be checked, as it asserts against the top-level command list.

**Depends on**: none

**Notes**: Verified 2026-07-18. `sed -n '88,145p' src/ptools/main.py` confirms the `tmp` entry at lines 95-98 and shows `format_commands` (lines 132-140) building rows from `COMMANDS[name]["short_help"]` with no hidden/filter branch — hiding therefore requires a code change, it is not a config toggle. `cat -n src/ptools/tmp.py` confirms 31 lines and the `shell=True` subprocess at line 28. `sed -n '44,55p' src/ptools/flow.py` confirms the "Development command" docstring at line 48.

Note `tmp.py:28` runs with `shell=True` on a user-supplied string. That is fine for a local personal tool and is not a reason to delete it, but it is a reason not to grow the command's surface.

If option 1 is chosen, check `tests/test_main_cli.py` for a hardcoded expected command list before deleting.

**Status**: proposed — not approved
