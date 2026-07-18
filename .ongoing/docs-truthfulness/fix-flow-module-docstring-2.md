# Correct flow.py's command list and the `flow map` example

**Goal**: Make `src/ptools/flow.py`'s module docstring and `collect`'s example name commands that actually exist.

**In scope**: The module docstring at `src/ptools/flow.py:1-13` and the example inside `collect`'s docstring at `src/ptools/flow.py:131-139`.

**Out of scope**: Renaming or aliasing any command; the behaviour of `collect`; other modules' docstrings.

**Description**: `src/ptools/flow.py:8-11` says the module defines the subcommands "map, filter, reduce, group, unique, foreach, while, exec, range, json, and dict".

There is no `map` command. The function is named `collect` (`flow.py:130`) and is registered as `collect` (`flow.py:577`). Verified 2026-07-18 against `.venv/bin/ptools flow --help`, whose command list is: `collect`, `dict`, `exec`, `filter`, `foreach`, `group`, `json`, `patch`, `range`, `read`, `reduce`, `sort`, `unique`, `while`.

So the docstring is wrong in both directions: it advertises one command that does not exist (`map`), and omits four that do — `collect`, `read`, `sort`, `patch` (registered at `flow.py:576`, `:577`, `:582`, `:589`).

The same error is repeated in runnable form at `flow.py:135`:

```
$ printf '1\n2\n3\n' | ptools flow map 'x * 2'
```

That is `collect`'s own docstring example, and it fails — `map` is not a valid subcommand.

`docs/cli.rst` renders the live Click tree through `sphinx_click` (`docs/conf.py:34` loads the extension), so both the module docstring and the broken example are published to the docs site verbatim.

**Acceptance criteria**:
- The module docstring's command list matches the keys registered on `cli` in `flow.py:576-589` exactly — no missing entries, no invented ones.
- `printf '1\n2\n3\n' | ptools flow <cmd> 'x * 2'` succeeds for the command named in `collect`'s example and emits `2`, `4`, `6`.
- `ptools flow --help` and the docstring agree on the set of command names.

**Depends on**: none

**Notes**: The docstring list will need re-checking whenever a command is added to `flow.py`; consider phrasing it so it does not enumerate every command, or adding a test that asserts the docstring's names are a subset of `cli.commands`. `flow.py:399` defines `while_loop` but registers it as `while` (`:586`) and `flow.py:102` defines `_dict` registered as `dict` (`:588`) — the docstring should use the registered names, not the Python identifiers.

**Status**: proposed — not approved
