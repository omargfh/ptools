# Report keyring failures as errors instead of tracebacks

**Goal**: Turn an unreachable or failing system keyring into a one-line `Error:` message across the secrets commands, instead of an `EncryptionError` traceback.

**In scope**: rebasing `EncryptionError` onto `Exception` (`src/ptools/utils/encrypt.py:10`), and catching it at the CLI boundary in `src/ptools/secrets.py` so every command in the group reports it uniformly.

**Out of scope**: retry or fallback behavior when the keyring is down — this PR only changes how the failure is *reported*. Any change to the keyring backend selection. `ptools vault bury`/`dig`, which share the dependency (see Notes).

**Description**: `Encryption._instantiate_encryption` raises `EncryptionError` when the keyring is unreachable (`utils/encrypt.py:49`) or the key cannot be initialized (`utils/encrypt.py:51`). `ConfigFile` re-raises it for undecryptable content (`utils/config.py:177`) and for a missing encryption service (`utils/config.py:169`), and calls `self.encryption.encrypt(...)` unguarded on the write path (`utils/config.py:191`). Nothing catches it: `grep -rn "except EncryptionError" src/ tests/` returns no hits. Every `ptools secrets` command is built on an encrypted `ConfigFile` (`secrets.py:16`), so on a machine where the keyring is locked, absent, or misconfigured, all seven registered subcommands (`secrets.py:246-252`) fail with a traceback rather than a diagnosis.

Two things need fixing, and the order matters:

1. `EncryptionError` subclasses `BaseException` (`utils/encrypt.py:10`), not `Exception`. That is almost certainly unintentional — it is a domain error, not a control-flow signal like `KeyboardInterrupt` — and it means an ordinary `except Exception` handler cannot catch it. Any handler written against the current class would have to name `EncryptionError` or `BaseException` explicitly, and `except BaseException` would swallow Ctrl-C. Rebasing onto `Exception` is safe: no `except EncryptionError` handler exists anywhere in `src/` or `tests/` that could change meaning.
2. With that fixed, the secrets `cli` group can catch it once and re-raise as `click.ClickException`, so every subcommand benefits without seven separate `try` blocks.

The message should say the keyring is unavailable and preserve the underlying cause — the existing strings at `utils/encrypt.py:49,51` already interpolate the original exception.

**Acceptance criteria**:
- `EncryptionError` subclasses `Exception`.
- With the keyring monkeypatched to raise `keyring.errors.KeyringError`, `ptools secrets list`, `get`, and `set` each exit non-zero with a single `Error:` line and no traceback.
- The error message identifies the keyring as the failing component and includes the underlying exception text.
- A `KeyboardInterrupt` during a secrets command is still not swallowed — no `except BaseException` is introduced.
- The missing-key behavior from `fix-get-exit-codes-1.md` is unchanged.
- `.venv/bin/python3 -m pytest` passes.

**Depends on**: `fix-get-exit-codes-1.md` — it creates `tests/test_secrets.py` and the isolated-config fixture this PR's tests reuse.

**Notes**: `ptools vault bury`/`dig` construct `Encryption(service_name="com.ptools.vault")` directly (`vault.py:55,72`) and have the identical exposure. `.ongoing/vault-safety/wrap-errors-3.md` explicitly defers keyring errors to this PR, but the handler proposed here sits on the secrets `cli` group and will not cover vault. Once this lands, either lift the handler somewhere both groups share or add the equivalent to vault — worth deciding during review rather than leaving vault as the one command that still tracebacks.

**Status**: proposed — not approved
