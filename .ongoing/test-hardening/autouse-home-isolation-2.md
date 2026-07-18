# Make HOME isolation autouse in the test suite

**Goal**: Make `$HOME` isolation automatic for every test so the suite stops writing into the developer's real home directory.

**In scope**: promoting the isolation behaviour of `isolated_home` (`tests/conftest.py:26-32`) to an autouse fixture; updating the four test files that request it explicitly if the fixture is renamed.

**Out of scope**: the import-time config writes that an autouse fixture cannot intercept — see `make-config-init-lazy-3.md`; `tmp_cwd` (`tests/conftest.py:19-23`), which is about the working directory, not `$HOME`.

**Description**: `tests/conftest.py` defines `isolated_home` (`:26-32`), which points `$HOME` at a tmp dir and pins `$USER`, but it is opt-in. Only 4 of 51 test files request it, so every other test that touches user config resolves paths against the real home. `ptools`'s config layer writes to `~/.ptools/` — `src/ptools/projects.py:16` hardcodes `os.path.expanduser("~/.ptools/projects.json")`, and `ConfigFile` seeds starter data on first run (`src/ptools/utils/config.py:31-44`).

Verified 2026-07-18 against a throwaway `HOME`: a full run creates `$HOME/.ptools/settings.json`. Two facts should be recorded honestly alongside that. First, the suite passes against a clean `HOME` (551 tests, 20 consecutive green runs), so this is a latent isolation defect, not a currently-failing one. Second, an autouse fixture is necessary but not sufficient: `src/ptools/settings.py:44-49` dereferences `settings.typed.*` at module scope, so the write happens at import time, before any fixture body runs. Confirmed directly — `HOME=$(mktemp -d) python -c "import ptools.dev"` creates `.ptools/settings.json`, and the same for `ptools.literals` creating `.ptools/literals.json` via the eager `ConfigFile` at `src/ptools/literals.py:10`.

So this PR closes the fixture-time hole and shrinks the blast radius; `make-config-init-lazy-3.md` closes the import-time one. Doing the fixture first is still worthwhile: it is a small, self-contained change that protects every test that writes config during the test body, which is the majority.

**Acceptance criteria**:
- Every test runs with `$HOME` pointed at a per-test tmp dir without opting in.
- A run against a pristine `HOME` leaves no new files in it apart from those created at import time (which this PR does not claim to fix).
- The 4 files that currently request `isolated_home` still pass, whether they keep requesting it or not.
- Full suite still passes (551 tests as of 2026-07-18).

**Depends on**: none

**Notes**: `monkeypatch.setenv` is function-scoped, so the autouse fixture must be function-scoped too; a session-scoped fixture cannot use `monkeypatch`. Keeping `isolated_home` as a no-op alias avoids touching the 4 existing call sites in the same PR. Pin `$USER` as the current fixture does (`conftest.py:31`) so behaviour stays deterministic.

**Status**: proposed — not approved
