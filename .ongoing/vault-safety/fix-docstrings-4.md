# Correct the four vault docstrings to describe in-place editing

**Goal**: Replace the false "printed to stdout" claim in all four `ptools vault` docstrings with an accurate description of the in-place default.

**In scope**: the docstring bodies at `src/ptools/vault.py:17`, `:35`, `:53`, `:70`.

**Out of scope**: any behavior change — in-place is the intended default and stays. Adding a `VAULT_IN_PLACE` opt-out (`add-in-place-setting-5.md`). Adding a `ptools vault` section to `docs/cli.rst` (see Notes).

**Description**: All four commands document `"If OUTPUT_FILE is not provided, the <en|de>crypted data will be printed to stdout."` (`vault.py:17,35,53,70`). None of them do that. Each resolves `output_file = output_file or f"{input_file}"` (`vault.py:24,43,60,78`) and writes to that path, overwriting the input file in place. Nothing in any of the four commands writes to stdout.

The behavior is intended; the documentation is the defect. As written the help text tells a user that omitting `OUTPUT_FILE` is the safe, non-destructive way to preview a result — the exact opposite of what happens. A user who reads the help and trusts it will overwrite a file they meant to inspect.

The corrected text should state plainly that omitting `OUTPUT_FILE` overwrites `INPUT_FILE` in place.

**Acceptance criteria**:
- No docstring in `src/ptools/vault.py` mentions stdout.
- All four docstrings state that omitting `OUTPUT_FILE` overwrites `INPUT_FILE` in place.
- `.venv/bin/ptools vault seal --help`, `unseal --help`, `bury --help`, and `dig --help` each render the corrected text.
- No line outside a docstring is changed.

**Depends on**: none — this is independent of the rest of the task and can land first if the others stall.

**Notes**: Correcting an inaccurate note in the parent brief: `docs/cli.rst` does **not** currently render vault. It carries `.. click::` directives for 19 subcommands (`docs/cli.rst:11`–`128`) but has no `ptools.vault:cli` entry, even though `vault` is registered in `main.py`'s `COMMANDS` dict (`src/ptools/main.py:99-101`). So the general repo rule — docstrings are the docs, because `cli.rst` renders the live Click tree via `sphinx_click` (`docs/cli.rst:4-6`) — is true, but for vault specifically these edits reach users only through `--help` today. Adding the missing `docs/cli.rst` section is a real gap and a good follow-up, but it publishes a new docs page and is a separate change from correcting a lie; it is not bundled here.

**Status**: proposed — not approved
