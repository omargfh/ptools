# Replace `eval()` with `ast.literal_eval` in vault decryption

**Goal**: Stop `ptools vault unseal` and `ptools vault dig` from executing arbitrary code found in their input file.

**In scope**: swapping `eval(f.read())` for `ast.literal_eval(f.read())` at `src/ptools/vault.py:39` and `:74`, the `import ast`, and a regression test in `tests/test_vault.py`.

**Out of scope**: changing the on-disk format (still a Python dict repr — see Notes). Error-message quality for a malformed file — that is `wrap-errors-3.md`.

**Description**: `src/ptools/vault.py:39` and `:74` both read a file and hand its entire contents to `eval()`, commented `# Use eval to convert string back to dict`. This is arbitrary code execution on untrusted input, verified by execution: a file whose contents are `__import__("os").system("echo PWNED")` runs the command on `ptools vault unseal`. The threat model is real for this command specifically — a sealed vault file is exactly the kind of artifact a user syncs between machines, commits, or receives from someone else, and `unseal` is the operation you run on a file you did not write.

`ast.literal_eval` is a sufficient replacement, not a partial one. The serialized form is produced by `str(encrypted_blob)` at `vault.py:26,45,62,79`, where `encrypted_blob` is the dict returned by `Encryption.encrypt` (`utils/encrypt.py:67-73`) or `PasswordEncryption.encrypt` (`utils/encrypt.py:132-139`) — in both cases a flat `dict[str, str]` of hex strings. That is entirely within `literal_eval`'s grammar, so every file the current code can write, the new code can still read.

**Acceptance criteria**:
- Neither `eval(` nor the stale comment remains in `src/ptools/vault.py`.
- A regression test writes `__import__("os").system("touch pwned")` (or equivalent observable side effect) into a file, runs `vault unseal` against it, and asserts the side effect did **not** occur and the exit code is non-zero.
- The round-trip tests from `add-round-trip-tests-1.md` still pass unchanged — a file sealed by the current code is still readable after the change.
- `.venv/bin/python3 -m pytest` passes.

**Depends on**: `add-round-trip-tests-1.md` — the round-trip tests are what prove `literal_eval` did not break the happy path.

**Notes**: `literal_eval` raises `ValueError`/`SyntaxError` on a malformed file rather than the current `NameError`/arbitrary behavior; until `wrap-errors-3.md` lands, that surfaces as a traceback. The regression test should therefore assert on the exit code and the absent side effect, not on message text. Storing the blob as JSON instead of a dict repr would be a cleaner format long-term but changes the on-disk representation and breaks existing sealed files — deliberately not attempted here.

**Status**: proposed — not approved
