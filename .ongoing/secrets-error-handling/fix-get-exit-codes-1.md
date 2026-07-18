# Fix `ptools secrets get` failure exit codes

**Goal**: Make a missing key exit non-zero in both the plain and `--quiet` forms of `ptools secrets get`, and report it as a `ClickException` instead of a raw `KeyError`.

**In scope**: the `else` branch of `get_secret` at `src/ptools/secrets.py:102-105`, and tests for both flag states.

**Out of scope**: `EncryptionError` from an unavailable keyring (`handle-encryption-errors-2.md`). `copy_secret`'s equivalent silent-failure path at `secrets.py:210-213` — same shape, separate command, and it exits 0 today for a different reason.

**Description**: `get_secret` (`secrets.py:87`) handles a missing key in a branch that has no `else` for the quiet case:

```python
else:
    if not quiet:
        click.echo(FormatUtils.warning(f"Secret '{key}' not found."))
        raise KeyError(f"Secret '{key}' not found.")
```

Both paths are wrong, verified by execution:

- `ptools secrets get MISSING` exits 1 with a raw `KeyError` traceback. The correct exit code, the wrong presentation — and it double-reports, echoing a warning and then raising.
- `ptools secrets get MISSING --quiet` exits **0** and prints nothing. This is the serious one: `--quiet` is the machine-readable form, documented in the command's own example as the way to capture a value (`secrets.py:92-93`). A shell doing `TOKEN=$(ptools secrets get API_TOKEN --quiet)` gets an empty string and a success status, so `set -e` does not trip and the empty value flows onward. The flag suppresses output, which is its job; silently converting failure into success is not.

`--quiet` should stay silent and exit non-zero. The plain path should raise `click.ClickException`, matching `src/ptools/proc.py:315`, `src/ptools/llm.py:70`, and `src/ptools/dev.py:156` — Click renders it as `Error: <message>` with exit code 1 and no traceback.

**Acceptance criteria**:
- `ptools secrets get MISSING` exits non-zero, prints a single `Error:` line, and prints no traceback.
- `ptools secrets get MISSING --quiet` exits non-zero and writes nothing to stdout.
- `ptools secrets get EXISTING --quiet` still writes the bare value to stdout and exits 0 — the existing contract at `secrets.py:100-101` is unchanged.
- `ptools secrets get EXISTING` still prints the formatted success line and exits 0.
- The missing-key message is emitted once, not as both a warning echo and an exception.
- `.venv/bin/python3 -m pytest` passes.

**Depends on**: none

**Notes**: There is no `tests/test_secrets.py` today; this PR creates it. Tests should construct `SecretsConfig` against an isolated config so they never read the real `~/.ptools` store — `secrets.py:16` passes `encrypt=True` to `ConfigFile`, which routes through the system keyring, so either point `--config-name` at a temp config with `$HOME` pinned via the `isolated_home` fixture (`tests/conftest.py:28`) or monkeypatch the keyring as in `.ongoing/vault-safety/add-round-trip-tests-1.md`. `SecretsConfig` also caches into a module-level `config_instance` global (`secrets.py:8,13-17`), so tests must not assume a fresh instance per call.

**Status**: proposed — not approved
