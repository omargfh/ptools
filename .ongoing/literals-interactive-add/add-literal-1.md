# Interactive add for `ptools literals`

**Goal**: Add a wizard to create a new literal entry without hand-editing `literals.json`.

**In scope**: a new subcommand alongside `lget` in `src/ptools/literals.py`; prompts for a collection (pick an existing one via `SelectApp`, or name a new one via `ask_text`), then a key and a value; persists to the `literals` `ConfigFile` instance `lget` already reads (`config = ConfigFile('literals', quiet=True)`).

**Out of scope**: editing or deleting existing literals; any change to `lget`'s clipboard-copy behavior.

**Description**: `lget`/`--choose-collection` only *selects* from `all_collections = config.data` — building the collection in the first place (e.g. the `cli_emojis`/`filesystem_emojis` groups in the packaged starter, `src/ptools/starters/literals.json`) is entirely manual JSON editing today. `touch.py`'s wizard work established the `SelectApp`/`ask_text` pattern this should reuse for picking-or-creating a collection and entering the new key/value pair.

**Acceptance criteria**:
- Running the add command with no arguments offers a picker over existing collections plus a "new collection" option (`ask_text` for its name).
- Prompts for a key and a value (the value is what `lget` later copies to clipboard).
- A key that already exists in the chosen collection is rejected with a clear error rather than silently overwritten.
- The new entry is visible to `ptools lget <collection>` on the next invocation (persisted through the same `ConfigFile` instance, not an in-memory-only change).

**Depends on**: none

**Notes**: confirm `ConfigFile`'s actual write/setter method in `utils/config.py` before implementing — reuse it rather than mutating `config.data` in place and hoping it's the persisted reference.

**Status**: proposed — not approved
