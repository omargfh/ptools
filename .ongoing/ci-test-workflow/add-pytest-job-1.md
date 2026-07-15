# Add a CI job that runs the test suite

**Goal**: Add a CI workflow that runs `pytest` on push and pull requests.

**In scope**: a new `.github/workflows/test.yml` that checks out the repo, sets up Python 3.10 (matching `pyproject.toml`'s `requires-python`), installs the package, and runs `pytest`.

**Out of scope**: a lint/typecheck job — no lint tool is configured in the repo yet, and pyright isn't installed in `.venv` (separate task). Changes to `docs.yml`.

**Description**: `.github/workflows/docs.yml` is the only workflow in the repo; it builds and deploys Sphinx docs and does not run tests. `pyproject.toml` declares `testpaths = ["tests"]` and 372 tests currently collect and pass locally, but nothing enforces that on push or PR — a regression can land on `main` undetected.

**Acceptance criteria**:
- New workflow triggers on `push` to `main` and on `pull_request`.
- Workflow installs the project (editable or otherwise) and runs `pytest` against `tests/`.
- Workflow fails if any test fails or fails to collect.
- Workflow passes against current `main` (372 tests, verified locally on 2026-07-14).

**Depends on**: none

**Notes**: `tests/conftest.py` adds `src/` to `sys.path` directly, so a plain `pip install -e .` (or even just having `src` on the path via `pyproject.toml`'s `pythonpath`) is enough — no extra test-only dependency group exists or is needed today.

**Status**: proposed — not approved
