# Fix the "Building the docs" section of getting-started.rst

**Goal**: Make `docs/getting-started.rst`'s build instructions describe commands that actually work.

**In scope**: The "Building the docs" section of `docs/getting-started.rst` (lines 23-40).

**Out of scope**: `docs/Makefile` itself (covered by `.ongoing/docs-build-target/fix-makefile-html-1.md`); any other section of `getting-started.rst`.

**Description**: The section makes two claims that don't hold.

1. `docs/getting-started.rst:32` introduces a code block with "or equivalently, using the provided Makefile:", but the block at `:36` contains `ptools dev docs` — not a `make` invocation. `ptools dev docs` does exist (verified 2026-07-18: it is listed in `.venv/bin/ptools dev --help` as "Build the Sphinx documentation under ``docs/``"), so the command is real and the prose label is simply wrong about what it is.
2. `docs/getting-started.rst:38-40` states "A convenience :file:`Makefile` is also provided ``make -C docs html`` is equivalent." It is not equivalent: `make -C docs html` prints `make: Nothing to be done for 'html'` and exits 0 without producing any output, because `html` sits in `docs/Makefile`'s `.PHONY` line with no recipe. AGENTS.md already records this under Gotchas, and the root-cause fix is planned separately.

This is the user-facing half of that gotcha: the published site currently tells readers to run a command that silently does nothing. The sentence at `:38-40` is also missing punctuation between "provided" and the literal, which is how the two independent claims got fused into one sentence.

**Acceptance criteria**:
- No sentence in `docs/getting-started.rst` claims `make -C docs html` builds the docs unless `.ongoing/docs-build-target/fix-makefile-html-1.md` has landed and the command demonstrably produces `docs/_build/html/index.html`.
- The prose label above the `ptools dev docs` block names that command rather than the Makefile.
- Every command quoted in the section runs successfully from the repository root.

**Depends on**: `.ongoing/docs-build-target/fix-makefile-html-1.md` — coordinate, don't block. If that PR lands first, this one rewords `:38-40` to describe the now-working target. If this one lands first, it should drop the `make -C docs html` claim outright rather than document a broken command; the other PR can then re-add it.

**Notes**: `docs/getting-started.rst` is rendered into the published site by the `Docs` workflow, so this text ships to readers. `sphinx-build -b html docs docs/_build/html` at `:30` is correct as written and needs no change.

**Status**: proposed — not approved
