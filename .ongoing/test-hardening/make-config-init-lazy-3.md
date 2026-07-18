# Stop initialising user config at import time

**Goal**: Defer `ptools.settings`' module-scope config reads so importing a ptools module no longer writes to the user's home directory.

**In scope**: the module-scope dereferences at `src/ptools/settings.py:44-49`, and the eager `ConfigFile` construction at `src/ptools/literals.py:10`.

**Out of scope**: `src/ptools/models/default_config.py`, which is already slated for deletion in `.ongoing/dead-code-removal/remove-default-config-model-2.md` — see Notes; `src/ptools/projects.py:16`, which computes a path string but performs no I/O at import; the test-side fixture (`autouse-home-isolation-2.md`).

**Description**: `src/ptools/settings.py:44-49` reads `settings.typed.PIP_EXECUTABLE`, `PTOOLS_DEBUG`, `EDITOR`, `SHELL_EXECUTABLE`, `SHELL_CONFIG` and derives `SHELL_KIND` at module scope, guarded only by `if __name__ != "__main__":` (`settings.py:43`). Dereferencing `.typed` forces the `LazyConfigFile` (`settings.py:40`) to load, which creates the file if it is absent — defeating the laziness the wrapper's name promises.

Because this runs at import, no pytest fixture can intercept it: collection imports the module before any fixture body executes. Verified 2026-07-18 with a throwaway `HOME`:

- `HOME=$(mktemp -d) python -c "import ptools.dev"` creates `$HOME/.ptools/settings.json`.
- `HOME=$(mktemp -d) python -c "import ptools.literals"` creates `$HOME/.ptools/literals.json`, via the eager `ConfigFile('literals', quiet=True)` at `literals.py:10`.

`ptools.settings` is reached transitively rather than directly — no test imports it by name, but `import ptools.dev` and `import ptools.proc` both pull it in (confirmed via `sys.modules`), which is how `tests/test_dev.py:11`, `tests/lib/test_proc_filter_wizard.py:18` and `tests/lib/test_proc_app_filter_wizard.py` reach it. `test-command-registry-1.md` will import every command module, widening this.

Beyond test isolation, import-time I/O means any consumer that merely imports a ptools module — the docs build, the requirements generator's `walk_packages` sweep (`scripts/generate_requirements.py:71-76`), a shell-completion hook — writes to the invoking user's home as a side effect.

**Acceptance criteria**:
- `HOME=$(mktemp -d) python -c "import ptools.dev"` creates no files in that `HOME`; same for `ptools.literals`.
- The module-level names in `settings.py` remain importable for existing consumers, or every consumer is updated in the same PR (`grep -rn "from ptools.settings import" src/` for the list).
- `literals.py`'s config is constructed on first use rather than at import.
- Full suite still passes (551 tests as of 2026-07-18).

**Depends on**: none — but `autouse-home-isolation-2.md` should land first, so the fixture catches anything this PR does not.

**Notes**: the values at `settings.py:44-49` are read as plain module globals by consumers, so the shape of the fix matters — a module-level `__getattr__` (PEP 562) preserves the `from ptools.settings import EDITOR` call sites without turning them into function calls, whereas converting them to accessor functions is a wider, more invasive change. `src/ptools/models/default_config.py:11` also constructs a `ConfigFile` and writes defaults at `:16`, but `load_default_config` has zero callers anywhere in `src/` or `tests/` (verified), so it writes nothing today and is better deleted than fixed; leave it to the dead-code task rather than duplicating it here.

**Status**: proposed — not approved
