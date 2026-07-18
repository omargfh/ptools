# Refresh (or de-hardcode) the test count in AGENTS.md

**Goal**: Stop AGENTS.md from asserting a test count that is off by ~180.

**In scope**: The `Test` bullet at `AGENTS.md:44`, and the two stale citations in `.ongoing/ci-test-workflow/add-pytest-job-1.md:9,15`.

**Out of scope**: Adding or changing any test; the CI test workflow itself.

**Description**: `AGENTS.md:44` reads:

> **Test**: `.venv/bin/python3 -m pytest` (verified — 372 tests collected; …)

Actual count is 551 (verified 2026-07-18 on a clean `main`, `.venv/bin/python3 -m pytest --collect-only -q`). The claim carries a "verified" marker, which makes it worse than an unmarked stale number — it invites agents to trust it without re-checking.

`.ongoing/ci-test-workflow/add-pytest-job-1.md` inherited the same figure in two places, including an acceptance criterion ("Workflow passes against current `main` (372 tests, verified locally on 2026-07-14)") that no longer describes `main`.

The rest of the surrounding claims hold — `~20 independent subcommands` in the Repo section is accurate (`ptools.main.COMMANDS` has 21 entries, verified 2026-07-18), and `pythonpath = ["src"]` is set at `pyproject.toml:45`.

**Acceptance criteria**:
- `AGENTS.md:44` either states a count matching `.venv/bin/python3 -m pytest --collect-only -q` at the time of the change, or states none.
- `.ongoing/ci-test-workflow/add-pytest-job-1.md`'s acceptance criterion no longer names a count that contradicts `main`.
- Any count that remains carries the command and date that produced it.

**Depends on**: none

**Notes**: This will re-rot. The exact figure earns nothing that "the suite passes" doesn't, so prefer dropping the number and keeping the command — a count is the kind of claim AGENTS.md value #9 ("Docs don't lie") makes expensive to hold. If a number is kept for a CI acceptance criterion, phrase it as "no fewer than the count on `main` at merge time" rather than a literal.

**Status**: proposed — not approved
