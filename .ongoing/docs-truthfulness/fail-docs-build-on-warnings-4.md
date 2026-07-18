# Make the docs workflow fail on Sphinx warnings

**Goal**: Turn Sphinx warnings into CI failures so a silently incomplete docs site can't deploy again.

**In scope**: The `Build HTML docs` step in `.github/workflows/docs.yml`, and the `html_static_path` warning that must be cleared first (`docs/conf.py:91`).

**Out of scope**: The `ptools.lib.llm` import failures (see `fix-llm-autosummary-imports-3.md`); adding a test job (see `.ongoing/ci-test-workflow/add-pytest-job-1.md`); the docs theme or content.

**Description**: `.github/workflows/docs.yml:33` runs:

```
sphinx-build -b html --keep-going docs docs/_build/html
```

`--keep-going` only has an effect alongside `-W`, and `-W` is not passed — so warnings are printed and ignored. Verified 2026-07-18 with sphinx-build 8.1.3: the workflow's exact command exits `0` against the current tree despite four warnings; adding `-W` makes the same build exit `1`. That is why the `[autosummary] failed to import` warnings have been able to ship a docs site with two modules missing, with a green check on every push.

One other warning must be cleared for `-W` to be viable:

```
WARNING: html_static_path entry '_static' does not exist
```

`docs/conf.py:91` sets `html_static_path = ["_static"]` but `docs/_static/` does not exist in the repo (verified 2026-07-18). Either create it with a `.gitkeep` or drop the setting — there are currently no static assets to serve, so removing the line is the smaller change.

**Acceptance criteria**:
- `sphinx-build -b html -W --keep-going docs docs/_build/html` exits `0` against `main`.
- The workflow step passes `-W`, and a deliberately introduced warning (e.g. a broken cross-reference) makes the `build` job fail rather than deploy.
- No `html_static_path entry '_static' does not exist` warning.

**Depends on**: `fix-llm-autosummary-imports-3.md` — must land first. Adding `-W` while the two autosummary imports still fail would leave `main`'s docs job permanently red.

**Notes**: Keep `--keep-going` when adding `-W` so one warning doesn't mask the rest of the build's output. If `-W` proves too blunt, `suppress_warnings` in `docs/conf.py` narrows it per-category, but prefer fixing warnings over suppressing them — a suppressed category is the same silent-incompleteness failure mode this PR exists to close.

**Status**: proposed — not approved
