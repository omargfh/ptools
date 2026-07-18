# Convert vault crypto/IO failures into `ClickException`

**Goal**: Make a wrong password or a malformed vault file exit with a one-line error message instead of a raw traceback.

**In scope**: wrapping the decrypt call in `unseal` (`src/ptools/vault.py:41`) and `dig` (`vault.py:76`), and the file parse in both, so `ValueError`, `KeyError`, `SyntaxError`, and `OSError` become `click.ClickException`. Same treatment for the read/encrypt/write path in `seal` and `bury`.

**Out of scope**: `EncryptionError` from the keyring, which `bury`/`dig` share with the secrets commands — handled once, centrally, in `.ongoing/secrets-error-handling/handle-encryption-errors-2.md`. Any change to which file gets written.

**Description**: A wrong password on `ptools vault unseal` currently produces a 10-frame traceback ending in `ValueError: MAC check failed`, raised from `decrypt_and_verify` at `utils/encrypt.py:157`. Nothing in `vault.py` catches it. After `replace-eval-2.md`, a truncated or non-vault input file adds a second untreated case (`ValueError`/`SyntaxError` from `literal_eval`), and a blob missing a key raises `KeyError` from the `encrypted_data['nonce']` lookups at `utils/encrypt.py:79-81,147,152-154`.

"Wrong password" is the single most likely way a user interacts with this command incorrectly, and the traceback neither says that nor reassures the user that their file survived. `click.ClickException` is the established pattern for this in the repo — `src/ptools/proc.py:315`, `src/ptools/llm.py:70,136,141`, `src/ptools/dev.py:156-160,190` all use it, and Click renders it as `Error: <message>` with exit code 1.

The messages must not overstate what is known: a MAC failure means "wrong password **or** corrupted file", because GCM cannot distinguish the two.

**Acceptance criteria**:
- `ptools vault unseal <file>` with a wrong password prints a single `Error:` line naming wrong-password-or-corrupt-file as the cause, exits non-zero, and prints no traceback.
- `ptools vault unseal <file>` against a file that is not a vault blob prints a single `Error:` line and exits non-zero.
- The wrong-password test from `add-round-trip-tests-1.md` still asserts the input file is byte-identical afterwards — the `try` must not move the `open(output_file, "wb")` call above the `decrypt` call.
- Error messages do not claim the password was wrong when a corrupt file is equally consistent with the evidence.
- `.venv/bin/python3 -m pytest` passes.

**Depends on**: `add-round-trip-tests-1.md`, `replace-eval-2.md`

**Notes**: `EncryptionError` subclasses `BaseException`, not `Exception` (`utils/encrypt.py:10`), so a broad `except Exception` here will not catch keyring failures — that is deliberate and left to the secrets-error-handling task. Do not use a bare `except Exception` around the whole command body; catch the specific exception types so a genuine bug still surfaces as a traceback.

**Status**: proposed — not approved
