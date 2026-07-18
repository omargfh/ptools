# Remove the duplicate command aliases in `ptools projects`

**Goal**: Make `ptools projects --help` list six commands instead of nine by removing the redundant `cli.add_command(...)` calls that re-register commands already registered by their `@cli.command()` decorator.

**In scope**: `src/ptools/projects.py:462-467` (the six `add_command` calls) and the six decorators at `projects.py:261,331,346,362,377,431`.

**Out of scope**: The behavior of any `projects` subcommand; `src/ptools/rsync.py`, `src/ptools/flow.py`, `src/ptools/json.py`, `src/ptools/secrets.py`, `src/ptools/shell.py`, and `src/ptools/fs.py`, which use `add_command` correctly and are unaffected.

**Description**: Six functions in `src/ptools/projects.py` are decorated with `@cli.command()` — `chdir` (`projects.py:261`), `list_projects` (`projects.py:331`), `add_project` (`projects.py:346`), `delete_project` (`projects.py:362`), `install` (`projects.py:377`), and `prune` (`projects.py:431`). `@cli.command()` both builds the Click command and attaches it to the group under the function's name, with underscores converted to dashes. `projects.py:462-467` then calls `cli.add_command(...)` on all six again with explicit short names.

For the three functions whose names already match their intended CLI name (`chdir`, `install`, `prune`) the second registration is a harmless no-op overwrite. For the other three it creates a second, unintended alias, because the decorator already registered the dashed long form:

```
Commands:
  add             Add a new project with NAME at PATH.
  add-project     Add a new project with NAME at PATH.
  chdir           Change directory to the project with NAME.
  delete          Delete the project with NAME.
  delete-project  Delete the project with NAME.
  install         Install the @cd shell function from SHELLCONFIG.
  list            List all projects.
  list-projects   List all projects.
  prune           Remove projects whose directory no longer exists on disk.
```

Nine entries where six are intended. Every alias pair is a duplicated docstring in `docs/cli.rst`, since `sphinx_click` renders the live tree.

The correct pattern is already used elsewhere in the repo: `src/ptools/secrets.py:246-252` and `src/ptools/shell.py:298-303` decorate with bare `@click.command()` (which builds a command without attaching it) and then attach it once via `add_command` with the intended name. `projects.py` is the only module that mixes `@cli.command()` with `add_command`; `grep -c '@cli.command'` returns 0 for `flow`, `json`, `rsync`, `secrets`, and `shell`, and the two hits in `fs.py` (lines 138, 177) are commands that are *not* re-registered at `fs.py:478-481`.

**Canonical names: the short forms — `add`, `list`, `delete`.** They are what the explicit `add_command` calls chose, they read better as verbs on an implied object (`ptools projects add`), and they match the naming used across the rest of the CLI (`secrets.py:246-248` registers exactly `set`/`get`/`list`, `json.py:214-217` uses short verb names). The `-project` suffix is redundant inside a group already named `projects`.

The fix is therefore to change the three mismatched decorators to `@click.command(name=...)` — or rename the functions — so the decorator registers the short name directly, and drop the whole `projects.py:462-467` block. Either way the end state is one registration per command.

**Acceptance criteria**:
- `.venv/bin/ptools projects --help` lists exactly six commands: `add`, `chdir`, `delete`, `install`, `list`, `prune`.
- `ptools projects add-project`, `ptools projects list-projects`, and `ptools projects delete-project` all exit non-zero with Click's "No such command" error.
- `ptools projects add NAME PATH`, `ptools projects list`, and `ptools projects delete NAME` behave exactly as before.
- `.venv/bin/python3 -m pytest tests/test_projects.py` passes; if it invokes any long-form name, update the test to the canonical short form in the same PR.
- No `cli.add_command` call in `src/ptools/projects.py` targets a function that is also decorated with `@cli.command()`.

**Depends on**: none

**Notes**: Verified 2026-07-18 by running `.venv/bin/ptools projects --help`, which printed the nine-entry list reproduced above. Registration sites confirmed with `grep -n "@cli.command\|^def \|add_command" src/ptools/projects.py` → decorators at 261, 331, 346, 362, 377, 431 and `add_command` calls at 462-467. Uniqueness of the defect confirmed with `grep -rn "add_command" src/ptools/` plus a per-module count of `@cli.command` vs `@click.command`: `projects.py` is the only file with both a `@cli.command`-decorated function and a matching `add_command` re-registration.

`tests/test_projects.py` exists and must be read before touching the decorators — it is the only test file covering this module, and a hardcoded long-form invocation there would otherwise turn into a red suite.

This is a user-facing rename for anyone with the long forms in a shell script or alias. For a personal toolbox that is acceptable, but it is a real break, so confirm with the owner rather than assuming.

**Status**: proposed — not approved
