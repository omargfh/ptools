# `ptools dev doctor` — diagnose missing optional dependencies

**Goal**: Add a `ptools dev doctor` command that reports which optional libraries/binaries/API keys announced across `ptools` are actually missing in the current environment.

**In scope**: a new `doctor` subcommand in `src/ptools/dev.py`; imports the full `ptools` package tree (same discovery approach `scripts/generate_requirements.py` already uses) then walks `ptools.utils.require.announced_requirements()`, re-checking each requirement for availability.

**Out of scope**: auto-installing anything found missing (`.venv` here has no `pip` — see `AGENTS.md` Gotchas — and that's `ptools dev install`'s job anyway); changing what individual `@require.*` decorators announce.

**Description**: `utils/require.py`'s `announce()`/`announced_requirements()` registry (`require.py:58-80`) already collects every optional library, binary, and API-key requirement declared via `@require.library`/`@require.binary`/`@require.key` across `ptools` — but the only consumer today is `scripts/generate_requirements.py`, which prints a requirements-file-shaped dump, not a live "is this satisfied right now" check. A user hitting a missing-dependency error inside some subcommand currently has to debug it after the fact; `doctor` gives a one-shot health report using the same `_require_library`/`_require_binary` checks the decorators themselves use (`require.py:88-98`).

**Acceptance criteria**:
- `ptools dev doctor` imports the full `ptools` package tree and reports, per announced requirement, whether it is currently satisfied.
- Output distinguishes missing optional libraries, missing binaries, and missing/unset API keys, and names the pypi package / binary / key alias needed to fix each.
- Exit code is non-zero if anything is missing, 0 if everything checked is satisfied — so the command is scriptable.
- Makes no installation attempt and no network access.

**Depends on**: none

**Notes**: `KeyRequirement` checking needs the store-lookup logic `_require_key` uses (`require.py:100-136`), but `announced_requirements()` only records the dataclass shape (`name`, `aliases`, `logical_operator`) — confirm which stores are reachable from `dev.py` without triggering unrelated key-prompt side effects (e.g. `prompt_install` flows) before wiring key checks in.

**Status**: proposed — not approved
