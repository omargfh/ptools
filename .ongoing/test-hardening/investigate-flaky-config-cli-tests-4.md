# Investigate two intermittently failing config CLI tests

**Goal**: Find and fix the source of intermittent failures in `tests/utils/test_config_cli.py`, or establish that they are environmental and record the evidence.

**In scope**: `tests/utils/test_config_cli.py::TestInteractiveFallbacks::test_set_still_validates_a_value_typed_into_the_prompt` (`:221-227`) and `tests/utils/test_config_cli.py::TestEditLoop::test_an_invalid_value_keeps_the_loop_alive`, plus their shared `patch_ask_text` helper and `tty` fixture.

**Out of scope**: broad rework of `test_config_cli.py`, which passes 36/36 in isolation; the interactive prompt implementation in `src/ptools/lib/tui/select.py` unless the investigation implicates it.

**Description**: This is the lowest-confidence item in this task and is scoped as an investigation, not a fix. Observed 2026-07-18 during full-suite runs against a throwaway `HOME`:

- One run failed both named tests (`2 failed, 549 passed`).
- A later run failed one test (`1 failed, 550 passed`).
- Roughly 33 clean-`HOME` full-suite runs in total, of which 2 showed failures — including 20 consecutive green runs at the end, so the reproduction rate is low and it did not reproduce on demand.
- `tests/utils/test_config_cli.py` run on its own passes 36/36, with a clean `HOME` and with the real one.
- No failure was observed under the developer's real `HOME`, but only ~2 full runs were done that way — too few to conclude the two are related.

No root cause was identified and no traceback was captured before the failures stopped reproducing, so the first task is a reliable reproduction. The one substantive lead: both named tests share a shape — drive an invalid value through the patched `ask_text` and assert the validation path (exit code 2 with `Invalid value for 'COUNT'`, `:226-227`). Tests in the same classes that drive valid values were never seen failing. That points at the patched-prompt helper or leaked state between tests rather than at `$HOME`, despite the failures only having been seen in clean-`HOME` runs.

Note the suite has no randomising plugin installed (`pytest_randomly` and `pytest_xdist` are both absent, verified), so ordering is deterministic and cannot be the variable on its own — which makes leaked module state or a genuine timing dependency the more likely explanations.

**Acceptance criteria**:
- Either: a deterministic reproduction is found, the cause is named, and the fix makes the two tests pass across 30 consecutive full-suite runs; or the investigation concludes the failures are environmental, and the evidence and reasoning are recorded in this file before it is closed.
- No test is silently skipped, quarantined, or marked `xfail` to make the symptom go away — that would be weakening the suite rather than fixing it.

**Depends on**: none — but run after `autouse-home-isolation-2.md`, which changes `$HOME` handling for every test and may well change or eliminate this symptom.

**Notes**: to reproduce, loop the full suite against a fresh `HOME` and stop on non-zero exit; budget ~30 runs at ~13s each. If `autouse-home-isolation-2.md` lands first, re-measure before spending time here — the flake may be a symptom of the same shared-state problem, in which case this file should be closed rather than worked.

**Status**: proposed — not approved

## Re-measurement 2026-07-18 (post-merge, staging/ongoing-execution)

Re-ran per the Notes' instruction to re-measure after `autouse-home-isolation-2.md`
landed. Conditions differ from the original observation: the autouse `$HOME`
fixture is now in effect and the suite has grown 551 -> 648 tests.

- 30 consecutive full-suite runs, stop-on-first-failure: **30/30 green**,
  648 passed every run, 0 failures.
- Command: `.venv/bin/python3 -m pytest -q`, looped 30x against the merged
  staging branch.

**This does not close the investigation.** No deterministic reproduction was
found and no root cause was named, so neither acceptance path is satisfied:

- The original rate was ~2 failures / 33 runs (~6%). At that rate a 30-run
  clean streak occurs by chance with probability ~0.94^30 = ~15% — so this
  result is consistent both with the flake being fixed and with it being
  unchanged.
- The original investigation itself recorded a 20-run green streak immediately
  before it stopped reproducing, so long green streaks are a known behaviour of
  this flake rather than evidence against it.

Conclusion: still open, with the failure rate now bounded below the level a
30-run sample can detect. Anyone resuming should either loop substantially more
runs (100+ to meaningfully constrain a ~6% rate) or attack it directly via the
shared `patch_ask_text` helper / leaked module state lead in the Description,
which remains the only substantive hypothesis. Do not close on the strength of
the streak above.
