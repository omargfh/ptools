# Interactive filter builder for `ptools proc`

**Goal**: Add a picker-driven way to build a `ptools proc` query-DSL expression without knowing its syntax.

**In scope**: a wizard entry point (new subcommand, e.g. `ptools proc filter`, or a `--wizard` flag on the existing `list_processes`/`cli` commands) that picks a field from `lib/proc/model.FIELDS`, an operator valid for that field's `kind`, and a value; chains clauses with `&`/`|`; compiles the result through `lib/proc/query.compile_query` and feeds it into the same `--where`/`query_arg` code path the CLI already uses (`proc.py:51`, `proc.py:81-90`).

**Out of scope**: changing the query DSL grammar (`lib/proc/query.py`) or the live Textual TUI's own filter bar (`lib/proc/app.py`) beyond feeding the wizard's output into the existing `--where` mechanism.

**Description**: The `cpu>50 & mem>500MB`-style filter language (`lib/proc/query.py`) requires memorizing field names, kind-specific operators (`Field.kind` in `model.py`: `STR` gets `=`/`!=`/`~`/`!~`; `NUM`/`SIZE`/`DURATION` get comparisons; `NUM_LIST`/`STR_LIST` get membership/any-match), and humanized value formats (`500MB`, `30s`). A picker-driven builder — field via `SelectApp` using `Field.title`/`Field.help` as labels, operator choices derived from `Field.kind`, value via `ask_text` — lowers that barrier the way `touch wizard` already did for template selection.

**Acceptance criteria**:
- The field picker lists every entry in `lib/proc/model.FIELDS` by `title`, with `help` shown as the picker description.
- Offered operators depend on the picked field's `kind` (e.g. a `STR` field never offers `>`/`<`).
- Multiple clauses can be chained with `&`/`|` before the wizard compiles and runs the final expression through `compile_query`.
- The resulting filter reaches `ptools proc` through the existing `--where`/positional-query path (`proc.py:108`'s `" & ".join(...)` combination) — no parallel filtering implementation.
- Fields with a `join` requirement need no special handling in the wizard itself: `required_joins()` (`model.py:91-98`) is already applied downstream (`proc.py:110`) to auto-enable whatever join a chosen field needs, mirroring how a typed `--where` behaves today.

**Depends on**: none

**Notes**: `--where`/`-w` and the bare `query_arg` positional are the two existing ways to supply a filter (`proc.py:51`, `proc.py:81-83`) — the wizard should produce the same expression string either would accept, not a separate internal representation.

**Status**: proposed — not approved
