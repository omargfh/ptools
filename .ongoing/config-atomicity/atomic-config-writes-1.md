# Write config files atomically

**Goal**: Stop a failure mid-write from truncating a config file to zero bytes, including the file holding encrypted secrets.

**In scope**: The five write sites in `ConfigFile` that open the real config path in `'w'` mode — `src/ptools/utils/config.py:124`, `:217`, `:226`, `:256`, `:283`.

**Out of scope**: `_writes`' serialization/encryption logic itself; concurrent-writer locking; `utils/cache.py`.

**Description**: Every `ConfigFile` mutator truncates the destination before it knows whether it can produce replacement content:

```python
def set(self, key, value):
    self.data[key] = value
    with open(self.file_path, 'w') as f:   # config.py:217 — truncates here
        self._writes(f, self.data)         # encrypt + serialize happen AFTER
```

`open(..., 'w')` truncates on open. `_writes` then does the work that can fail, inside the already-empty handle: `self.encryption.encrypt(...)` at `config.py:191` and `self.serial.dump(...)` at `config.py:205`. The encrypt path reaches the system keyring (`utils/encrypt.py:34-51`), so a locked or unavailable keyring, a serializer error on an unserializable value, or a `SIGINT` in that window all leave a zero-byte file where the config used to be.

Same shape at `:226` (`delete`), `:256` (`clear`), `:283` (`replace`), and `:124` (first-run creation).

This is not hypothetical for secrets: `KeyValueStore(..., encrypt=True)` is how the LLM API-key store is declared (`src/ptools/lib/llm/stores.py:11`), and the vault/secrets commands use the same class. A truncated encrypted store is unrecoverable — there is no backup and the plaintext only ever existed in the keyring-encrypted blob.

The correct pattern already exists in-repo, for a file that matters far less. `utils/cache.py:96-99` writes a throwaway cache atomically:

```python
tmp = str(cache_file_path) + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(to_write, f)
os.replace(tmp, cache_file_path)
```

Lift that into `ConfigFile`. `os.replace` is atomic on POSIX and Windows, so a failure anywhere before it leaves the original file untouched.

**Acceptance criteria**:
- No `ConfigFile` method opens `self.file_path` in a truncating mode; writes go to a temp file in the same directory and land via `os.replace`.
- A test that makes `_writes` raise part-way through `set`/`delete`/`clear`/`replace` leaves the pre-existing file byte-identical.
- A test that makes encryption raise (mock `Encryption.encrypt`) on an encrypted store leaves the prior ciphertext intact and readable.
- The temp file does not survive a failed write.
- Existing config tests pass unchanged.

**Depends on**: none

**Notes**: Put the temp file in the same directory as the target, not the system temp dir — `os.replace` across filesystems raises `OSError`. `cache.py:100-101` swallows all write errors with a bare `except Exception: pass`, which is defensible for a cache and is **not** the part to copy: a config write that fails must still raise. The seeded-starter write at `config.py:114-115` writes a fresh file from packaged bytes and is lower risk, but converting it too keeps the class to a single write path.

**Status**: proposed — not approved
