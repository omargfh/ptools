# Deduplicate the requirement announcement registry

**Goal**: Stop `announce()` from accumulating identical requirement entries, so consumers do not each have to dedup defensively.

**In scope**: deduplication inside `announce()` / `_REQUIREMENTS` (`src/ptools/utils/require.py:58-69`), and removing the now-redundant dedup in the generator's OS and binary sections if it becomes dead.

**Out of scope**: `doctor`'s library dedup (`dev.py:324-328`), which is deliberately keyed on module name rather than on the whole dataclass and must stay; changing what any decorator announces (`add-os-requirement-type-1.md`).

**Description**: `_REQUIREMENTS` (`require.py:58`) is an append-only module global written at decoration time, and `announce()` appends unconditionally with no dedup (`require.py:61-69`). Decorating N commands with the same requirement therefore leaves N identical entries in the registry. The four `@require.os(["darwin"])` decorators in `src/ptools/fs.py` (`fs.py:343,354,387,423`) are the clearest case: they produce four identical entries.

Consumers currently compensate unevenly. `doctor` dedups with `dict.fromkeys` (`dev.py:330-335`) and so prints `[MISSING] darwin` once. `scripts/generate_requirements.py` does not dedup at all (`generate_requirements.py:118-123`), which is why it emits four `#   - darwin` lines — verified 2026-07-18. Deduping at the source fixes the class of bug rather than the instance, and prevents `render-os-in-generator-3.md`'s new OS section from reproducing exactly the same four-duplicate-lines defect.

All requirement types are frozen dataclasses (`require.py:25-53`), hence hashable and value-comparable, so order-preserving dedup on the whole value is straightforward and does not need per-type rules.

**Acceptance criteria**:
- Announcing the same requirement value twice leaves one entry in `announced_requirements()`.
- First-seen order is preserved; `clear_announcements()` (`require.py:83-85`) still empties the registry.
- Distinct requirements that merely share a name are still kept separate (e.g. two `LibraryRequirement`s differing only in `pypi_name` or `prompt_install`, which `dev.py:320-323` documents as a real case).
- `doctor` output is unchanged, since it already deduped.
- `python scripts/generate_requirements.py` lists each distinct system requirement once.

**Depends on**: none

**Notes**: prefer landing this before `render-os-in-generator-3.md` — that PR regenerates `full_requirements.txt`, and this one changes generator output, so the reverse order forces a second regeneration. Deduping at announce time means a module imported twice under different names can no longer inflate the registry, which is also what makes the generator's `pkgutil.walk_packages` sweep (`generate_requirements.py:71-76`) robust.

**Status**: proposed — not approved
