# Report OS requirements in `ptools dev doctor`

**Goal**: Add an OS section to `doctor` so `@require.os(...)` gates are visible and checked instead of silently dropped.

**In scope**: an operating-system section in `doctor` (`src/ptools/dev.py:280-378`) that filters `OSRequirement` out of the registry and checks it against `platform.system().lower()`; the corresponding update to `doctor`'s docstring example.

**Out of scope**: the `OSRequirement` type itself (`add-os-requirement-type-1.md`); generator rendering (`render-os-in-generator-3.md`).

**Description**: After `add-os-requirement-type-1.md`, `doctor` filters the registry by `isinstance` for libraries, binaries and keys only (`dev.py:326-335`), so `OSRequirement` announcements are recorded but never displayed. That is the right trade for the type fix — the false `[MISSING] darwin` disappears — but it leaves a genuine OS mismatch invisible, which matters because the four `darwin` gates in `src/ptools/fs.py` (`fs.py:343,354,387,423`) are the only thing standing between a Linux user and a command that cannot work there.

This PR restores visibility using the correct check: compare against `platform.system().lower()`, mirroring `_require_os` (`require.py:148-151`), never `shutil.which`. Follow the existing section pattern — dedup with `dict.fromkeys`, sort for stable output, join multi-name requirements with the logical operator (`dev.py:355-363`) — and count a mismatch toward `missing_count` (`dev.py:376-377`) so the documented scriptable exit code stays meaningful.

**Acceptance criteria**:
- `doctor` prints an operating-system section listing each announced `OSRequirement`, and `(none announced)` when there are none.
- On macOS the four `darwin` gates render as satisfied and `doctor` exits 0.
- A simulated non-matching OS marks the requirement missing and makes `doctor` exit non-zero.
- `doctor`'s docstring example output (`dev.py:294-304`) reflects the new section — `docs/cli.rst` renders the live Click tree via `sphinx_click`, so this docstring is published documentation.

**Depends on**: `add-os-requirement-type-1.md`

**Notes**: `tests/test_dev.py` patches the registry wholesale via `_patch_registry` (`tests/test_dev.py:15`), which stubs both `_import_all_ptools_submodules` and `announced_requirements`, so an OS case can be tested without importing real ptools modules or depending on the host platform.

**Status**: proposed — not approved
