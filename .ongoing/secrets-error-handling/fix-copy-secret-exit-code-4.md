# Make a missing key fail in secrets copy

**Goal**: Make `ptools secrets copy` exit non-zero on a missing key, matching `secrets get`.

**In scope**: `copy_secret`'s missing-key branch (`src/ptools/secrets.py:231`) and its missing-`pyperclip` branch (`:224-225`).

**Out of scope**: Clipboard backend selection; the rest of the secrets group.

**Description**: `fix-get-exit-codes-1.md` made a missing key exit 1 in `secrets get`, and explicitly listed `copy_secret` as out of scope. It still has the same defect — verified 2026-07-19 on staging:

    value = secrets_config.get_secret(key)
    if value is not None:
        pyperclip.copy(value)
    else:
        click.echo(FormatUtils.warning(f"Secret '{key}' not found."))   # :231, then exits 0

A missing `pyperclip` (`:224-225`) likewise warns and returns 0. Both report failure on stdout while telling the shell everything succeeded, so `ptools secrets copy MISSING && do_next` proceeds as if the clipboard held the secret.

**Acceptance criteria**:
- `ptools secrets copy MISSING` exits non-zero and reports via `ClickException`, not a bare warning.
- A missing `pyperclip` also exits non-zero.
- The error names the key, never the secret value.
- Tests reuse `tests/test_secrets.py`'s isolated-config + fake-keyring fixtures; no real keychain access.

**Depends on**: none — `fix-get-exit-codes-1.md` has landed and established the fixtures.

**Notes**: Same defect class as the `get` fix; the pattern to copy is already in `secrets.py`.

**Status**: proposed — not approved
