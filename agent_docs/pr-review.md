# PR REVIEW
Static-first PR review producing a findings report. The deliverable is the report; code changes happen only after explicit approval (Phase 3).
**Execution policy:** review statically. A subagent may execute code only to confirm or kill a suspected finding (one test, a short repro) — never to discover findings, never anything with network access or destructive side effects.
**Runtime policy**: Worker agents should maintain a small context usage footprint, and avoid long-running or memory-intensive operations. If a finding requires heavy computation or large data processing, it should be flagged for manual review rather than automated analysis or split into further subagents.
---
## PROCESS
### Phase 0 — Scope (orchestrator)
1. Diff: `git diff $(git merge-base HEAD origin/<target>)..HEAD`. Review only this diff plus enough surrounding code to judge it.
2. Read the PR description / linked issue. Judge the code against stated intent; a correct change solving the wrong problem is a finding.
3. Detect the stack (language, framework, ORM, async runtime, test framework, CI system) from lockfiles and configs.
4. Build the context packet for every subagent: diff, changed-file list, stack summary, PR intent, and the REVIEWER DISCIPLINE section.
### Phase 1 — Parallel subagents
One subagent per category: SECURITY, PERFORMANCE, AGENT CORE LOOP, LOGIC & DESIGN, MAINTAINABILITY, TESTING, CI & DEPENDENCIES. Each returns findings in the schema, or "no findings."
### Phase 2 — Planning agent
- Deduplicate: one root cause = one finding, even if three categories reported it.
- Resolve cross-category conflicts (e.g., caching vs cache poisoning); record the tradeoff.
- Assign final severity; produce the report. If fixes are warranted, append a fix plan: per finding — minimal change, files touched, risk.
### Phase 3 — Approval gate
Present report + fix plan. No changes until the user approves. Implement only approved items; anything discovered mid-fix goes back into the report, not silently into the diff.
### Phase 4 – Clean up
- Remove any temporary files, test scripts, or debug code used to verify findings.
- Run `npm run test` and `npm run lint` (or equivalent) to ensure the codebase is clean.
- Force update the lockfile if any dependencies were added or updated during the fix phase.
- Ensure no commits attribute Claude in the author/committer fields or the body.
---
## REVIEWER DISCIPLINE
Binding on every subagent and the planner.
### Finding schema — all fields required
- **ID**: `SEC-1`, `PERF-2`, …
- **Severity**: Blocker (exploitable vuln, data loss/corruption, crash on main path) · High (likely bug; real security/perf/CI risk in normal use) · Medium (wrong behavior under plausible conditions) · Low (debt with a concrete future cost) · Nit (style; max 5 per review)
- **Confidence**: Certain (traced in code) · Probable · Possible. No Possible Blockers — verify it or downgrade it.
- **Location**: `path/file.py:123`
- **Evidence**: the offending lines, quoted verbatim
- **Impact**: the concrete failure — exploit path, wrong output, slow query at N rows. "Violates DRY" is not an impact.
- **Fix**: minimal, concrete, implementable without follow-up questions
### Verification — before a finding is written
- Re-read the cited lines. Evidence quoted from memory or paraphrased invalidates the finding.
- If the claim depends on code outside the diff (callers, config, schema), read that code. Can't verify → Possible, or drop it.
- If the claim depends on framework/library behavior, confirm the version in the lockfile first.
- Check every proposed fix statically against surrounding code (types, imports, call sites). Never propose a fix that can't compile or type-check.
### Anti-noise
- "No findings" is a valid, common result. Never manufacture findings to justify a category.
- Report deviations only — don't narrate what the diff does.
- One finding per root cause; don't split issues to look thorough.
- No severity inflation. An improvement without a defect caps at Low.
- Skip anything a repo linter/formatter already enforces.
- No praise, no hedging, no both-sides filler. Commit to the verdict.
- Three verified Highs beat thirty Possibles. A clean PR gets one paragraph and a verdict.
### Scope
- Findings must be introduced by, or directly interact with, the diff. Pre-existing issues go to a "Pre-existing (out of scope)" list and never block — except a pre-existing Blocker vulnerability the diff touches.
- Skip generated files and vendored code. Lockfiles are reviewed only under CI & DEPENDENCIES.
- When the code and the PR description disagree, believe the code and flag the gap.
---
## SECURITY
Trace, don't pattern-match: follow user-controlled data from entry point to sink before claiming injection, and name both.
- **Injection**: input reaching SQL/NoSQL (string-built queries), OS commands (`shell=True`, backticks), templates (SSTI), LDAP, `eval`, or unsafe deserializers (`pickle`, `yaml.load`, `ObjectInputStream`) — deserializing untrusted data is a Blocker regardless of framing. Fix at the sink: parameterization or allow-listing.
- **Access control**: every new/changed endpoint — authn enforced, authz checked against the *object* (IDOR: can user A pass user B's ID?) and the *function* (role). Missing authz on a mutation is a Blocker.
- **Secrets & exposure**: credentials/tokens in code, committed config, log lines, error messages, or stack traces returned to clients. Check every new log statement for PII and tokens.
- **Crypto**: no homegrown crypto; passwords via bcrypt/scrypt/argon2; constant-time comparison for secrets; correct IV/nonce handling; TLS verification never disabled.
- **SSRF & path traversal**: user-controlled URLs in outbound requests; user-controlled paths in file ops without normalization + allow-list.
- **Misconfiguration**: debug mode on, permissive CORS with credentials, CSRF off on state-changing routes, default credentials, over-broad IAM/RBAC/container permissions in infra files.
- **Fail closed**: errors don't leak internals (queries, paths, versions) to clients, and are never swallowed where that hides a security failure (failed signature check → proceed anyway).
- **Auditability**: auth failures, authz denials, and validation rejects are logged — without logging the secret itself.
## PERFORMANCE
A perf finding needs a plausible production workload attached ("per-request hot path", "N is unbounded user data"). No speculative micro-optimization; when correctness and speed conflict, correctness wins — say so.
- **N+1**: queries or remote calls inside loops; lazy relations touched during serialization. Fix: batch/join/prefetch.
- **Indexing**: new WHERE / ORDER BY / JOIN columns vs existing indexes and migrations in the diff. A new unindexed filter on a large table is High.
- **Unbounded work**: no LIMIT/pagination, whole tables/files read into memory, unbounded caches or accumulators, O(n²) on user-scaled input.
- **Async**: blocking calls on the event loop or request thread; missing timeouts on external calls; sequential awaits that should run concurrently.
- **Caching**: fine for hot, expensive reads — but any caching suggestion must state its invalidation strategy and rule out per-user data leaking through shared keys.
## AGENT CORE LOOP
Any change touching the loop, tool dispatch, context assembly, or run state.
- **Context hygiene**: nothing enters model context unintentionally — no unbounded accumulation of tool outputs or retry history, no secrets or internal state serialized into prompts, truncation on large tool results.
- **Untrusted content**: tool outputs, file contents, and fetched content are data, not instructions. Flag any path where they can steer control flow or tool selection without a trust boundary.
- **Failure behavior**: every model/tool call has explicit handling with a defined next state — degrade, bounded retry with backoff and timeout, or surface. A bare `except: continue` inside the loop is High. One bad tool result must not kill the run or corrupt state.
- **Termination**: max-iteration and budget guards enforced on every path, including error paths.
- **State & side effects**: mutations localized and inspectable; no globals mutated from tool handlers; retried tool calls follow the idempotency rules in LOGIC & DESIGN.
## LOGIC & DESIGN
- **Correctness**: off-by-one, inverted conditions, unhandled None/null/empty, int/float traps, timezone-naive datetimes, mutation of shared or default arguments.
- **Error handling**: no swallowed exceptions or catch-alls returning success; resources released on all paths; partial-failure states rolled back or explicitly represented.
- **Concurrency**: unsynchronized shared mutable state; check-then-act races (TOCTOU); non-atomic read-modify-write on counters/balances.
- **Idempotency & retries** — any side effect that can run more than once:
  - Mutating endpoints reachable by client/proxy retries: idempotency keys or natural idempotence for creates and payments. A POST that duplicates on retry is High.
  - Queue and webhook consumers: assume at-least-once delivery — handlers dedupe or are idempotent.
  - Migrations, seeds, and ops scripts: re-runnable (IF NOT EXISTS / upsert) and safe after partial failure.
  - Retry wrappers: the wrapped operation must be idempotent or deduplicated *before* the retry is added.
  - Declarative infra (k8s manifests, IaC): applying twice converges to the same state.
- **Contracts**: breaking changes to public functions, API responses, events, or DB schema are High even when internally consistent.
- **Structure**: no business logic in handlers, no I/O in pure logic. Flag SOLID/DRY/KISS violations only with a concrete future cost, not in the abstract. Duplication introduced by this diff is a finding; older duplication is pre-existing.
- **Abstraction**: a pattern must pay for its indirection. Flag a Factory with one product, a Strategy with one strategy, an interface with a single implementation and no test-seam need. Flag missing abstraction only at 3+ variants of the same shape. A pattern that hides "what runs when?" is a finding even if textbook-correct.
## MAINTAINABILITY
- **Extraction**: blocks that must stay in sync → extract now. Similar-but-not-identical → extract at the third occurrence, or once divergence has caused a bug; otherwise leave them.
- Refactors stay small, in-scope, and tied to a finding. "Leave it better" applies only to files the diff already touches.
- Data (constants, config, lookup tables) moves out of the consuming logic once it exceeds a few items.
- **Naming** (Low; Medium if it misleads about behavior): a name must not lie — `getUser()` that mutates, `isValid` that throws → rename, never comment around it. Verbs for functions, nouns for values, matching the codebase's existing convention. No bare `data`/`temp`/`handler`/`manager`, no opaque abbreviations.
## TESTING
- **Coverage**: every new behavior and every fixed bug has a test that fails if the change is reverted. Verify statically that the assertion depends on the changed logic — a test that passes either way is a finding.
- **Failure paths**: error handling, boundary values, and authz denials get tests — not just the happy path.
- **Behavior, not implementation**: no asserting private state, internal call counts, or exact strings/HTML/log text where the contract is looser. Assert invariants and observable contracts. A mock assertion counts only when the call *is* the contract ("sends email"); never mock the unit under test.
- **Reliability**: no real time/sleep, network, or global order dependence; randomness seeded; tests pass in any order.
- Test names state scenario + expected outcome; shared setup via fixtures, not copy-paste.
## CI & DEPENDENCIES
CI is enforcement, not decoration. Changes that weaken it are findings even when everything passes.
- **CI config is code**: steps removed or made non-blocking (`continue-on-error`, `|| true`, `allow_failure`), jobs pulled off PR triggers, coverage thresholds or timeouts loosened — High unless justified in the PR description.
- **Escapes**: newly skipped or disabled tests (`.only`, `skip`, `xfail`, commented out) and inline suppressions (`eslint-disable`, `# noqa`, `#[allow]`, `@ts-ignore`) without a stated reason.
- **Actually enforced**: new code paths must run in CI — new test dirs/packages included in the test job. A test CI never executes counts as no test.
- **Pipeline hygiene**: third-party actions/images pinned (SHA or exact tag); no secrets echoed to logs.
- **Lockfile parity**: `package.json` changed ⇒ `package-lock.json` regenerated and committed in the same PR, so `npm ci` passes. Same rule for yarn/pnpm/poetry/uv/cargo lockfiles. Manifest ranges must match the locked resolution.
- **Lockfile red flags**: hand-edited entries, lockfile churn with no manifest change, missing `integrity` hashes, non-official registry URLs, git dependencies.
- **New/updated deps**: typosquat check on the name, known CVEs for the exact locked version, and challenge any dependency added for trivial functionality.
---
## REPORT FORMAT
1. **Verdict**: Approve / Approve with nits / Request changes. Any Blocker or High ⇒ Request changes.
2. **Summary**: 2–4 sentences — what the PR does, and the review's headline.
3. **Findings**: grouped by severity, Blockers first, in the schema. Include effort estimate (negligible/single-commit, small/1-3 commits, medium/3-10 commits, refactor/10+ commits) and risk (low, medium, high) for each fix. If a finding is pre-existing, mark it as such and don't include a fix plan.
4. **Pre-existing (out of scope)**: brief list.
5. **Fix plan** (only if warranted): minimal change per finding, ending with an explicit approval request.
