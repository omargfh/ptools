# Extend keyring error handling to the vault commands

**Goal**: Stop `ptools vault bury`/`dig` from printing an `EncryptionError` traceback when the system keyring is unreachable.

**In scope**: The keyring-backed `Encryption(...)` construction at `src/ptools/vault.py:80` (`bury`) and `:105` (`dig`).

**Out of scope**: `seal`/`unseal` (`vault.py:22,48`), which use `PasswordEncryption` and never touch the keyring; the secrets group handler itself.

**Description**: `handle-encryption-errors-2.md` added a `SecretsGroup.invoke()` handler converting `EncryptionError` into a one-line `Error:`. That handler is installed on the **secrets** group only. `vault.py:80,105` construct `Encryption(service_name="com.ptools.vault")` directly, so `bury` and `dig` retain the exact traceback exposure that PR removed elsewhere — verified 2026-07-19 on staging.

`wrap-errors-3.md` wrapped vault's crypto/IO failures in `ClickException`, so some of this may already be covered; confirm which paths still escape before writing code.

**Acceptance criteria**:
- An unreachable/failing keyring produces a one-line `Error:` and a non-zero exit from both `bury` and `dig`, with no traceback.
- The message distinguishes "keyring unreachable" from "wrong key / corrupt ciphertext" — collapsing them would tell a user their data is corrupt when the keyring is merely locked.
- Tests use a fake keyring backend and `tmp_path` only; no test touches the real keychain.

**Depends on**: none — `handle-encryption-errors-2.md` and `wrap-errors-3.md` have both landed.

**Notes**: Flagged by the secrets PR's own report as a gap its scope did not cover.

**Status**: proposed — not approved
