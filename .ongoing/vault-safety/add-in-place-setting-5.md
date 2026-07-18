# Add a `VAULT_IN_PLACE` setting to opt out of overwriting the input file

**Goal**: Let a user set `VAULT_IN_PLACE=false` so that omitting `OUTPUT_FILE` writes to stdout instead of overwriting `INPUT_FILE`.

**In scope**: a `VAULT_IN_PLACE: bool = True` field on `SettingsModel` (`src/ptools/settings.py:31-38`), its module-level constant export (`settings.py:43-49`), wiring the four commands' `output_file` fallback (`vault.py:24,43,60,78`) to honor it, docstring updates mentioning the opt-out, and tests for both branches.

**Out of scope**: a per-invocation `--stdout` flag. Changing the default — in-place stays the default.

**Description**: In-place overwrite is the intended default (`fix-docstrings-4.md` makes the help text say so), but it is currently unconditional: `output_file = output_file or f"{input_file}"` at `vault.py:24,43,60,78` offers no way to preview a result without writing it. Since `seal` and `bury` produce a dict repr and `unseal`/`dig` produce the original plaintext, "print it instead" is a genuinely useful mode — for piping, for inspecting a file before committing to overwriting it, and for scripting.

`SettingsModel` is the established place for this. The existing fields (`settings.py:34-38`) follow one pattern: a typed default sourced from `os.environ.get(...)`, resolved in the env-var → `~/.ptools/settings.json` → hard-coded-default order documented at `settings.py:4-8`, exported as a module constant at `settings.py:43-49`, and manageable via the generated `ptools settings` CLI (`settings.py:41`, built by `config_to_CLI` at `utils/config.py:514`). `PTOOLS_DEBUG` (`settings.py:35`) is the precedent for a bool field, including its `== "1"` env parsing.

The write paths differ per command and must be handled individually: `seal`/`bury` write text (`vault.py:25-26,61-62`), `unseal`/`dig` write bytes (`vault.py:44-45,79-80`). The stdout branch for `unseal`/`dig` should emit the decrypted string, which `Encryption.decrypt` already returns as UTF-8 (`utils/encrypt.py:86,159`), rather than re-encoding it.

**Acceptance criteria**:
- `VAULT_IN_PLACE` exists on `SettingsModel` with default `True`, follows the same env-var pattern as the neighbouring fields, and is exported as a module constant.
- `ptools settings list` shows `VAULT_IN_PLACE`, and `ptools settings set VAULT_IN_PLACE false` persists it to `~/.ptools/settings.json`.
- With the setting at its default, all four commands overwrite `INPUT_FILE` when `OUTPUT_FILE` is omitted — the tests from `add-round-trip-tests-1.md` pass unmodified.
- With `VAULT_IN_PLACE=false`, all four commands write their result to stdout and leave `INPUT_FILE` byte-identical.
- Passing an explicit `OUTPUT_FILE` writes to that path regardless of the setting's value.
- The four docstrings describe both branches and name the setting.
- `.venv/bin/python3 -m pytest` passes.

**Depends on**: `fix-docstrings-4.md` — that PR rewrites the same four docstrings this one amends; landing them in the other order creates an avoidable conflict.

**Notes**: `ptools settings set VAULT_IN_PLACE` needs no extra work to be usable interactively — commit `4571fed` made `config_to_CLI` render a two-row true/false picker for any key the model declares as `bool`, so declaring the field with a `bool` annotation is sufficient. `tests/test_settings.py:23-31` already has the `_reload_settings` helper for testing a new field — `ptools.settings` persists model defaults to disk at import time, so tests must pin `$HOME` to a fresh `tmp_path` and `importlib.reload` the module, as that file's header docstring explains. Read the setting at call time rather than binding it at import in `vault.py`, so an env-var override applies without a reload.

**Status**: proposed — not approved
