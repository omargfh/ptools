# Restore ptools.lib.llm.stores/decorators to the published API docs

**Goal**: Remove the import-time keyring/decryption side effect that makes Sphinx drop two `ptools.lib.llm` modules from the API docs.

**In scope**: The module-level store instantiations at `src/ptools/lib/llm/stores.py:11`, `:43`, `:71`, and whatever minimal deferral mechanism they need.

**Out of scope**: `docs/conf.py`'s `autodoc_mock_imports` list; making the docs build fail on warnings (see `fail-docs-build-on-warnings-4.md`); `EncryptionError`'s base class.

**Description**: Building the docs emits (verified 2026-07-18, `python -m sphinx -b html docs <out>`):

```
WARNING: [autosummary] failed to import ptools.lib.llm.decorators.
* EncryptionError: Failed to decrypt config file ~/.ptools/llm/keys.json: catching classes that do not inherit from BaseException is not allowed
WARNING: [autosummary] failed to import ptools.lib.llm.stores.
```

Both modules import fine outside Sphinx, so this is not broken code. The actual chain is:

1. `stores.py:11` runs `KeyValueStore(name='llm/keys', quiet=True, encrypt=True)` at **module import time**. `ConfigFile.__init__` reads and decrypts the file if it exists (`utils/config.py:119-127`, decrypt at `:175`) or creates and encrypts it if it doesn't (`:124-127`). Either branch reaches the system keyring. `stores.py:71` does the same with `encrypt=True`.
2. `docs/conf.py:61-77` lists `keyring` and `Crypto` in `autodoc_mock_imports`, so under Sphinx `keyring.errors.KeyringError` is a `MagicMock`. The `except keyring.errors.KeyringError` at `utils/encrypt.py:48` then raises `TypeError: catching classes that do not inherit from BaseException is not allowed`.
3. `utils/config.py:176-177` rewraps that as `EncryptionError`, which subclasses `BaseException` (`utils/encrypt.py:10`), so it escapes ordinary `except Exception` handling as well.
4. autosummary reports the import failure and both modules are omitted from the published site. `decorators.py:12` imports from `.stores`, which is why it fails too.

Reproduced in isolation (2026-07-18) by mocking only `keyring`/`Crypto` and importing `ptools.lib.llm.stores`: it raises the same `EncryptionError`.

Un-mocking `keyring`/`Crypto` is **not** a sufficient fix, and this is the key finding. Both are core dependencies (`pyproject.toml:9-10`) so CI does install them, but a GitHub runner has no keyring backend. Verified 2026-07-18 with a real `keyring` and `PYTHON_KEYRING_BACKEND=keyring.backends.fail.Keyring`: the import still fails, with `EncryptionError: Failed to access keyring service: No recommended backend was available`. The import-time side effect is the root cause, not the mocking.

The repo already has the mechanism for this: `LazyConfigFile` (`utils/config.py:347-383`) defers `ConfigFile.__init__` until the first attribute access, and its docstring gives exactly this rationale. `KeyValueStore` is a semantic alias for `ConfigFile` (`utils/config.py:814-820`) with no lazy counterpart, so the fix is either to add one or to declare these stores as `LazyConfigFile`.

**Acceptance criteria**:
- `python -m sphinx -b html docs <out>` emits no `[autosummary] failed to import` warning for `ptools.lib.llm.stores` or `ptools.lib.llm.decorators`.
- Both modules appear in the generated API pages under `docs/api/generated/`.
- `import ptools.lib.llm.stores` succeeds with `keyring` mocked, and with a real `keyring` under `PYTHON_KEYRING_BACKEND=keyring.backends.fail.Keyring` — i.e. importing the module touches neither the keyring nor `~/.ptools/`.
- Existing `ptools llm` behaviour is unchanged; the stores still resolve on first use.

**Depends on**: none

**Notes**: `src/ptools/literals.py:10` has the same import-time pattern (`ConfigFile('literals', quiet=True)`) but is unencrypted and does not currently break the docs build — leave it unless it is free to convert. Two follow-ups worth raising separately rather than folding in here: `EncryptionError` subclassing `BaseException` (`utils/encrypt.py:10`) means callers' `except Exception` blocks silently miss it, and the blanket `except Exception` at `utils/encrypt.py:50` is what converts a plain `TypeError` into a misleading "Failed to initialize encryption key" message.

**Status**: proposed — not approved
