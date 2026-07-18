# Remove the unused models/default_config.py

**Goal**: Delete `src/ptools/models/default_config.py`, which has zero importers and writes to the user's real home directory as a side effect of being called at all.

**In scope**: `src/ptools/models/default_config.py`, the now-empty `src/ptools/models/` directory (including its stale `__pycache__`), and the `src/ptools/models/` row in `AGENTS.md:34`.

**Out of scope**: `src/ptools/utils/config.py` and its `ConfigFile` constructor semantics; the `model=` validation hook that `ConfigFile` already supports (`utils/config.py:89`); any other Pydantic schema in the repo.

**Description**: `src/ptools/models/default_config.py` is 18 lines defining a `DefaultConfig` BaseModel with a single field (`verbose: bool = False`) and a `load_default_config()` helper. Nothing imports either symbol. The directory has no `__init__.py`, so `ptools.models` is not even a regular package — only the implicit-namespace-package rules make `from ptools.models.default_config import ...` work at all. `AGENTS.md:34` nonetheless lists `src/ptools/models/` as "Pydantic default-config schemas", implying a live layer that does not exist.

Beyond being dead, it is a latent hazard. `load_default_config()` at `default_config.py:11` constructs `ConfigFile("ptools", quiet=True)`, and `ConfigFile.__init__` is not a read-only operation: `utils/config.py:93-96` expands the default `path="~/.ptools"` and calls `os.makedirs(Path(self.file_path).parent, exist_ok=True)` unconditionally, then `utils/config.py:120-127` either seeds the file from the packaged starter or creates and writes a fresh one. `default_config.py:14-16` then calls `default_config.set(k, v)` for every missing key, writing again. So merely calling this function — from a test, a REPL, or a future caller — creates and mutates `~/.ptools/ptools.json` in the developer's actual home. The `quiet=True` argument suppresses the "Created new config file" message, so it does this silently.

The functionality it gestures at is already available without this module: `ConfigFile` accepts a `model:` parameter (`utils/config.py:89`) and validates through it (`utils/config.py:138`), which is the supported way to attach a Pydantic schema to a config file.

**Acceptance criteria**:
- `src/ptools/models/` no longer exists.
- `grep -rn "default_config\|ptools.models" src/ tests/ docs/ scripts/` returns no matches.
- `.venv/bin/python3 -m pytest` passes with an unchanged test count (372 at time of writing).
- `.venv/bin/ptools --help` and every subcommand's `--help` are unaffected.
- `AGENTS.md` no longer claims a `src/ptools/models/` layer.

**Depends on**: none

**Notes**: Deadness verified 2026-07-18 with `grep -rn "default_config\|from ptools.models\|import models" src tests scripts docs --include="*.py" --include="*.rst"`, which returned only the five self-references inside `src/ptools/models/default_config.py` itself (lines 9, 11, 12, 15, 16) and nothing else. Directory contents confirmed with `ls -la src/ptools/models/` → `default_config.py` plus `__pycache__` only; no `__init__.py`.

The home-directory write is a property of `ConfigFile.__init__`, not of this module — every `ConfigFile(...)` construction in the codebase has it. What makes it notable here is that this module's only exported function does nothing *but* construct one and write to it, so there is no path where importing and calling it is side-effect-free. Worth remembering if this module is ever resurrected: any test touching it needs `HOME` redirected (see `tests/conftest.py` for the existing pattern).

If the owner wants a typed default-config schema later, the replacement is `ConfigFile("ptools", model=DefaultConfig)` rather than a separate loader function.

**Status**: proposed — not approved
