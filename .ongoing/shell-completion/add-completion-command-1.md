# `ptools shell completion` — generate and install shell completion

**Goal**: Add a `ptools shell completion` command that prints, and optionally installs, Click's shell completion script for the `ptools` binary.

**In scope**: a new subcommand in `src/ptools/shell.py`, reusing the existing `Shell` class's append-to-rc-file mechanism to install the completion `eval` line, the same way other `shell.py` commands manage blocks in the user's shell config.

**Out of scope**: changing `Shell`'s existing default-config-file get/set behavior; completion for anything other than the `ptools` command itself.

**Description**: Click 8.1+ (pinned in `pyproject.toml`, `8.3.1` installed) generates shell completion scripts via the `_<PROG>_COMPLETE=<shell>_source <prog>` convention (`click.shell_completion`). `shell.py` already owns the pattern for appending managed blocks to a user's shell rc file for other shell-config helpers, but nothing wires a subcommand to Click's own completion generator.

**Acceptance criteria**:
- `ptools shell completion --shell bash|zsh|fish` prints the completion script for that shell to stdout.
- `ptools shell completion --shell zsh --install` appends the corresponding `eval "$(_PTOOLS_COMPLETE=zsh_source ptools)"` (or per-shell equivalent) to the user's configured shell rc file via the existing `Shell` append mechanism, without duplicating the block on a second run.
- Works for at least bash and zsh; fish's completion syntax differs enough that it should be verified separately if included, not assumed to work by analogy.

**Depends on**: none

**Notes**: verify the exact completion env-var name Click derives from the installed entry-point name (`ptools` → `_PTOOLS_COMPLETE`) against the actual `click.shell_completion` API at implementation time rather than hardcoding it from memory.

**Status**: proposed — not approved
