# Test that every registered command actually loads

**Goal**: Add a test that resolves every `COMMANDS` entry through `_load_command` and asserts the result is a `click.Command`.

**In scope**: a test in `tests/test_main_cli.py` looping over `COMMANDS` (`src/ptools/main.py:18-103`) and calling `_load_command` (`main.py:106-110`).

**Out of scope**: making `_load_command` itself validate the resolved attribute's type (see Notes); invoking each command; adding tests for individual subcommand behaviour.

**Description**: `_load_command` (`main.py:106-110`) splits a `"module:attribute"` string, imports the module and returns `getattr(module, attribute)`. Nothing in the suite exercises it for a real command. `tests/test_main_cli.py` has five tests, and all of them stay on the metadata: help text (`:8-20`), an unknown command (`:23-26`), sorted listing (`:29-32`), and an unknown lookup returning `None` (`:35-37`). Two of those iterate `COMMANDS` but only assert the name appears in help output (`:19-20`) or that `list_commands` is sorted (`:32`) — neither imports the target module, so a typo in an `import_path`, a renamed attribute, or a module that raises on import would all pass CI while breaking the command for users.

This bug class has already shipped. Commit `5e4f5b4` is "fix(cli): register vault command"; its body records that vault existed since `428e431` but was never wired into the CLI group, leaving the command invisible for multiple commits. The failure mode here is adjacent and cheaper to catch.

Verified 2026-07-18: all 21 current entries resolve and every result is a `click.Command`, so this is regression prevention, not a bug fix — the test should be green on `main` the day it lands.

**Acceptance criteria**:
- A test iterates every `COMMANDS` entry, calls `_load_command` on its `import_path`, and asserts `isinstance(result, click.Command)`.
- The test fails if an entry's module cannot be imported, its attribute does not exist, or the attribute is not a `click.Command`.
- The test names the offending command when it fails (parametrize over `COMMANDS`, or assert with the key in the message) — a bare traceback on entry 14 of 21 is not actionable.
- Passes against current `main` (21 entries, verified 2026-07-18).

**Depends on**: none

**Notes**: `_load_command` does not check that the resolved attribute is a `click.Command`; a wrong-but-importable attribute currently surfaces later as a confusing Click error. Hardening the loader is a defensible follow-up, but it is a source change with its own error-message design, so keep it out of this test-only PR. This test imports every command module, so it also pulls `ptools.settings` in transitively — see `autouse-home-isolation-2.md`, which matters more once this test exists.

**Status**: proposed — not approved
