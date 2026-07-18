# Stop settings.py's module constants from defeating LazyConfigFile

**Goal**: Remove the import-time `settings.typed` dereference so importing a `ptools` submodule doesn't force a config read.

**In scope**: `src/ptools/settings.py:43-51` and the five import sites that consume the constants.

**Out of scope**: The precedence fix itself (see `fix-settings-env-precedence-2.md`); `LazyConfigFile`'s implementation.

**Description**: `settings.py:40` declares the store lazily —

```python
settings = LazyConfigFile("settings", quiet=True, model=SettingsModel)
```

— and `LazyConfigFile` exists specifically to defer `ConfigFile.__init__`'s disk I/O until first attribute access (`utils/config.py:347-350`, whose docstring gives startup performance as the rationale).

`settings.py:43-49` then throws that away:

```python
if __name__ != "__main__":
    PIP_EXECUTABLE = settings.typed.PIP_EXECUTABLE
    ...
    SHELL_KIND = detect_shell_kind(SHELL_EXECUTABLE)
```

Touching `settings.typed` triggers `LazyConfigFile.__getattribute__` (`utils/config.py:379-383`), which runs the deferred `__init__`. That means every importer pays the full cost at import: `os.makedirs`, a read and parse of `~/.ptools/settings.json`, model validation, and on a fresh machine a **file creation and write** (`utils/config.py:124-127`). `detect_shell_kind` at `:49` adds more work on top.

`if __name__ != "__main__"` is always true for an imported module, so the guard never protects anything, and the `else` branch at `:50-51` re-assigns `cli` to the identical expression already evaluated at `:41` — dead code either way.

The blast radius is small enough to fix cleanly: the constants are imported at exactly four call sites — `proc.py:5`, `tmp.py:3`, `dev.py:19`, `lib/proc/app.py:57` (verified 2026-07-18). All import `EDITOR`, `PIP_EXECUTABLE`, or `PTOOLS_DEBUG` by name, which is precisely the pattern that forces eager evaluation.

`main.py`'s `LazyGroup` dispatch exists to keep startup cheap; a module-scope config read in a module that four subcommands import undercuts it.

**Acceptance criteria**:
- Importing `ptools.settings` performs no filesystem access — no read of, and no write to, `~/.ptools/settings.json`.
- Importing `ptools.proc`, `ptools.dev`, and `ptools.tmp` likewise perform none at import time.
- `ptools --help` on a `HOME` with no `~/.ptools/` does not create `settings.json`.
- The four consumer call sites still resolve the same values at the point of use.
- The vacuous `if __name__ != "__main__"` guard and its duplicate `else` branch are gone.

**Depends on**: `fix-settings-env-precedence-2.md` — land that first. It introduces the `get()` accessor that gives consumers something to call at use-time, which is what makes removing the module constants straightforward rather than a separate redesign.

**Notes**: The four call sites use `from ptools.settings import EDITOR`, so the constants can't be made lazy in place — a module-level `__getattr__` (PEP 562) would preserve the import syntax while deferring, or the sites can move to `settings.get("EDITOR")` at point of use. The latter is more honest and composes with the precedence fix: a value read at use-time actually reflects the current environment, which `fix-settings-env-precedence-2.md` requires anyway. Note `dev.py` may genuinely need `PIP_EXECUTABLE` early; check before assuming every site can defer.

**Status**: proposed — not approved
