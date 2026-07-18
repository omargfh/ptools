# Make env vars actually override persisted settings

**Goal**: Implement the env-over-file precedence `src/ptools/settings.py` documents, instead of the reverse it currently has.

**In scope**: `SettingsModel`'s field defaults (`src/ptools/settings.py:31-38`) and the settings resolution path; a real `get`/`set` API to back the module docstring.

**Out of scope**: `config_to_CLI` and the `ptools settings` CLI surface; the module-scope constant dereference at `settings.py:43-49` (see `defer-settings-module-constants-3.md`); other `ConfigFile` consumers.

**Description**: `settings.py:4-8` documents the resolution order as:

> 1. Environment variable (highest - useful for one-off overrides)
> 2. Persistent global config file at `~/.ptools/settings.json`
> 3. Hard-coded default (lowest)

and `settings.py:18-21` reinforces it: "A single env var still wins over the stored value, so you can temporarily override without losing the persisted default."

The implementation inverts this. `settings.py:34-38` reads `os.environ` as pydantic **field defaults**:

```python
EDITOR: str = os.environ.get("EDITOR", "vim")
```

A field default only applies when the key is absent from the validated input. `typed` is `self.model.model_validate(self.data)` (`utils/config.py:241`), and `self.data` is loaded from `~/.ptools/settings.json` — so any key present in the file wins, permanently.

Verified 2026-07-18 with a scratch `HOME` containing `{"EDITOR": "stored-nano"}`:

```
$ HOME=<scratch> EDITOR=env-code python -c "from ptools import settings; print(settings.EDITOR)"
stored-nano
```

The documented one-off override does not work. `EDITOR=code ptools proc` does not change the editor `proc.py:5` resolves.

It is worse than a read-order bug, because the file gets populated on first run. `ConfigFile.__init__` writes the fully-defaulted model to disk when the file is absent (`utils/config.py:124-127`). Verified on a fresh `HOME` with `EDITOR=env-code`: `~/.ptools/settings.json` is created containing `"EDITOR": "env-code"` — every one of the five keys, env-derived, frozen. So a single env-var-prefixed invocation permanently bakes that value in and disables the env var from then on.

Being class-level, the defaults are also evaluated once at import. Mutating `os.environ` afterwards has no effect (verified: `typed.EDITOR` still returned the import-time value).

The documented precedence is the correct one — it is what every consumer expects from `EDITOR`, and `settings.py:18-21` sells it explicitly. Fix the code to match the docs, not the other way around.

Related, and part of the same fix: `settings.py:11-16` documents `:func:`get`` and `:func:`set`` as the API. Neither exists (verified: `hasattr(settings, 'get')` and `hasattr(settings, 'set')` are both `False`), so the docstring's own example, `settings.set("PIP_EXECUTABLE", "uv pip")`, raises `AttributeError`. A `get(name)` that consults `os.environ` first, then `settings.data`, then the model default is both the precedence fix and the missing function.

**Acceptance criteria**:
- With `{"EDITOR": "stored-nano"}` in `~/.ptools/settings.json`, `EDITOR=env-code` resolves `EDITOR` to `env-code`.
- With the same file and no `EDITOR` in the environment, it resolves to `stored-nano`.
- With neither, it resolves to the hard-coded default (`vim`).
- Setting `os.environ["EDITOR"]` after `ptools.settings` is imported changes what the next resolution returns.
- Running any `ptools` command with an env var set does not persist that value into `~/.ptools/settings.json`.
- `settings.get` and `settings.set` exist and behave as `settings.py:11-16` describes; the docstring's example runs.
- Each env var name in the resolution path still matches today's: `PIP_EXECUTABLE`, `PTOOLS_DEBUG`, `EDITOR`, `PTOOLS_SHELL`, `PTOOLS_SHELL_CONFIG` (note the last two differ from their field names, `settings.py:37-38`).

**Depends on**: none

**Notes**: Moving env reads out of the field defaults means `SettingsModel` defaults become the hard-coded tier only — check that `detect_shell()`/`detect_shell_config()` (`settings.py:37-38`) still run lazily rather than at import, since they shell out. Existing `~/.ptools/settings.json` files already contain baked-in env-derived values from first run; decide whether those are honoured as intentional (the env var will now override them anyway, so this is likely a non-issue) or whether a note belongs in the `ptools settings` help. `PTOOLS_DEBUG` is parsed as `== "1"` today (`settings.py:35`) — keep that exact truthiness rule so `PTOOLS_DEBUG=true` doesn't silently change meaning.

**Status**: proposed — not approved
