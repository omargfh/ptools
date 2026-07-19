# Accept common truthy spellings in boolean env settings

**Goal**: Stop `SETTING=true` from evaluating to `False`.

**In scope**: The boolean branch of the env-var parser at `src/ptools/settings.py:83`.

**Out of scope**: Non-boolean settings; the config-file path (only env-var parsing is affected); renaming any setting.

**Description**: `src/ptools/settings.py:83` parses booleans as `return value == "1"`, so `"1"` is the only truthy spelling. Verified 2026-07-19 on staging:

    VAULT_IN_PLACE='true'  -> False        PTOOLS_DEBUG='true'  -> False
    VAULT_IN_PLACE='True'  -> False        PTOOLS_DEBUG='True'  -> False
    VAULT_IN_PLACE='1'     -> True         PTOOLS_DEBUG='1'     -> True

This is long-standing and applies to every boolean setting, but `add-in-place-setting-5.md` newly attached it to a destructive-operation toggle: a user who exports `VAULT_IN_PLACE=true` intending to keep the in-place default silently gets the stdout branch instead. The direction of harm is mild today (stdout is the safer branch), but the setting does the opposite of what the user wrote, and the next boolean setting may not fail safe.

**Acceptance criteria**:
- `true`, `True`, `TRUE`, `yes`, `on`, `1` all parse truthy; `false`, `no`, `off`, `0`, empty all parse falsy.
- An unrecognised value is rejected loudly rather than silently treated as false.
- `PTOOLS_DEBUG` and `VAULT_IN_PLACE` both keep their current defaults when the env var is unset.
- `tests/test_settings.py`'s existing `"1"`-only assertions are updated, not deleted — they encode the old rule deliberately.

**Depends on**: none

**Notes**: Found while verifying `add-in-place-setting-5.md`. That PR applied the existing convention consistently and added a test asserting it, so this is a change to the convention itself, not a defect in that PR. Check whether any docstring or `--help` text promises a spelling that does not work.

**Status**: proposed — not approved
