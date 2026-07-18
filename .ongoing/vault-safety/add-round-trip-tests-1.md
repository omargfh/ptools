# Add a test suite for `ptools vault`

**Goal**: Create `tests/test_vault.py` covering seal→unseal and bury→dig round-trips plus the wrong-password failure path, with no behavior change to `src/ptools/vault.py`.

**In scope**: a new `tests/test_vault.py` driving all four commands through `click.testing.CliRunner`; a keyring fixture that monkeypatches `keyring.get_password`/`keyring.set_password` so `bury`/`dig` never touch the real system keyring.

**Out of scope**: any change to `src/ptools/vault.py`. Replacing `eval` (`replace-eval-2.md`), error wrapping (`wrap-errors-3.md`), docstring corrections (`fix-docstrings-4.md`).

**Description**: `src/ptools/vault.py` has no test file — `grep -rl vault tests/` returns nothing, and `tests/` contains no `test_vault.py`. All four commands (`seal` `vault.py:14`, `unseal` `vault.py:32`, `bury` `vault.py:50`, `dig` `vault.py:67`) default to writing over the input file (`vault.py:24,43,60,78`), so every subsequent PR in this task edits code whose only safety net is manual testing.

One behavior is load-bearing and untested: on a wrong password, `enc.decrypt(...)` at `vault.py:41` raises from pycryptodome's GCM verification (`utils/encrypt.py:157`) *before* `open(output_file, "wb")` at `vault.py:44` runs. Because the default `output_file` is the input file, that ordering is the only reason a mistyped password does not truncate the ciphertext to zero bytes. Nothing currently enforces it; a later refactor that hoists the `open` above the `decrypt` would silently turn a typo into data loss. This PR pins it.

**Acceptance criteria**:
- `tests/test_vault.py` exists and passes under `.venv/bin/python3 -m pytest tests/test_vault.py`.
- Round-trip test: `seal` an explicit `output_file`, then `unseal` it with the same password, and assert the recovered bytes equal the original plaintext.
- In-place round-trip test: `seal` with `output_file` omitted, assert the input path's contents changed, then `unseal` it in place and assert the original plaintext is restored.
- `bury`/`dig` round-trip test passes against a monkeypatched keyring, and the real `keyring` backend is never called.
- Wrong-password test: `unseal` an in-place sealed file with the wrong password, assert a non-zero exit code **and** assert the input file's bytes are byte-identical to before the call.
- No file under `src/` is modified by this PR.

**Depends on**: none

**Notes**: `PasswordEncryption` uses `PBKDF2(..., count=1000000)` (`utils/encrypt.py:122,150`), measured at ~0.6s per derivation on this machine — a seal+unseal round trip costs ~1.2s. Keep the number of password-based cases small, or share one sealed fixture across assertions, so the suite's runtime does not balloon. `tests/conftest.py:28` already provides an `isolated_home` fixture pinning `$HOME` and `$USER`; `tmp_cwd` (`tests/conftest.py:20`) covers the file-creation cases.

**Status**: proposed — not approved
