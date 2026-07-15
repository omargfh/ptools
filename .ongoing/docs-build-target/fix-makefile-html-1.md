# Fix docs/Makefile's html target

**Goal**: Fix `docs/Makefile` so `make html` actually builds the Sphinx docs instead of silently doing nothing.

**In scope**: `docs/Makefile`'s `.PHONY` declaration and/or the `html` target.

**Out of scope**: Sphinx config or content changes; the `docs.yml` CI workflow (which calls `sphinx-build` directly and is unaffected).

**Description**: `docs/Makefile` declares `.PHONY: help Makefile clean html` with no explicit recipe for `html`. Because `html` is already listed in `.PHONY`, make's catch-all `%: Makefile` pattern rule never fires for it, so `make -C docs html` prints `make: Nothing to be done for 'html'` and exits 0 without building anything (verified 2026-07-14). The working build command is `python -m sphinx -M html docs docs/_build`, but that's non-obvious and undocumented in the Makefile itself.

**Acceptance criteria**:
- `make -C docs html` produces a fresh `docs/_build/html/index.html`.
- The target's exit code is non-zero if the underlying Sphinx build fails (today a broken target falsely reports success).

**Depends on**: none

**Notes**: root cause is `html` sitting in the same `.PHONY` line as targets like `clean` that intentionally have no `sphinx-build` recipe. Removing `html` from that `.PHONY` line (or giving it an explicit recipe) should let the catch-all rule apply correctly.

**Status**: proposed — not approved
