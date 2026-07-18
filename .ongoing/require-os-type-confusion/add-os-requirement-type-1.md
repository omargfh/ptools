# Introduce a dedicated OS requirement type

**Goal**: Make `require.os()` announce an `OSRequirement` instead of a `BinaryRequirement`, so OS gates stop being reported as missing executables.

**In scope**: a new `OSRequirement` dataclass in `src/ptools/utils/require.py`, its addition to the `Requirement` union (`require.py:56`), and switching the `announce(...)` call inside `require.os()` (`require.py:267-270`) to use it.

**Out of scope**: how `dev doctor` and `scripts/generate_requirements.py` render the new type (`report-os-in-doctor-2.md`, `render-os-in-generator-3.md`); the runtime gate `_require_os` (`require.py:139-155`), which is already correct; registry deduplication (`dedup-requirement-registry-4.md`).

**Description**: `require.os()` gates a command on `platform.system().lower()` (`require.py:274` → `require.py:148-151`), but announces its OS names as a `BinaryRequirement` (`require.py:267-270`) — a type whose docstring reads "One or more executables that must be on `$PATH`" (`require.py:40-41`). Both registry consumers therefore treat `darwin` as an executable name. Verified on macOS 2026-07-18:

- `ptools dev doctor` checks the announcement with `shutil.which("darwin")` (`dev.py:356`), which can never succeed. It prints `[MISSING] darwin` and exits 1 on a healthy machine — while `dev.py:286-288` documents the exit code as scriptable ("Missing libraries or binaries make this command exit non-zero, so it's scriptable").
- `python scripts/generate_requirements.py` lists it under "System binaries (install via your OS package manager)" (`generate_requirements.py:119-122`), emitting four `#   - darwin` lines, one per `@require.os(["darwin"])` in `src/ptools/fs.py` (`fs.py:343,354,387,423`).

Both consumers select requirements by `isinstance` (`dev.py:330-332`, `generate_requirements.py:90-92`), so correcting only the announced type fixes both symptoms at once: OS entries stop being mistaken for binaries. Rendering them properly is deliberately left to the follow-ups, so this PR is a pure type correction with no output-formatting decisions in it.

**Acceptance criteria**:
- `require.os()` announces an `OSRequirement`; no `BinaryRequirement` is announced by any `@require.os(...)` decorator.
- `ptools dev doctor` exits 0 on macOS with no `[MISSING] darwin` line (it exits 1 today).
- `python scripts/generate_requirements.py` emits no `darwin` line (four today).
- Runtime behaviour is unchanged: a command decorated `@require.os(["darwin"])` still raises on a non-`darwin` platform and still runs on macOS.
- A test asserts `require.os()` announces `OSRequirement`.

**Depends on**: none

**Notes**: `require.os()` is the only announcement site that is wrong — `library()`, `binary()` and `key()` each announce their matching type. Make `OSRequirement` a frozen dataclass like its siblings (`require.py:40-53`): `dev.py:330-335` dedups announcements with `dict.fromkeys`, which requires hashability. `clear_announcements()` (`require.py:83-85`) exists for exactly this kind of registry test. `tests/test_dev.py:12` imports the three requirement types directly and will need the fourth.

**Status**: proposed — not approved
