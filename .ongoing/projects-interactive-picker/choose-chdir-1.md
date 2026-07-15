# Interactive picker for `ptools projects chdir`

**Goal**: Let `ptools projects chdir` pick a project interactively when no name is typed.

**In scope**: `src/ptools/projects.py`'s `chdir` command — make the `name` argument optional; when omitted, open a `SelectApp` picker over `Projects.get_instance().get_projects()` (label = project name, description = path) and use the pick in place of the typed argument.

**Out of scope**: `switch()`'s sub-path join behavior (`name/subdir`) when a name is typed directly; the `install` command that wires `chdir` into the user's shell function.

**Description**: `chdir NAME` (`projects.py:119-136`) requires typing the project name exactly, with no way to browse. `lget` already has this exact shape: `--choose-collection` opens a `SelectApp` over collection names instead of requiring an exact match (`literals.py`'s `LiteralsApp`, itself now a thin `SelectApp` subclass). Bring `chdir` in line with the same shared component.

**Acceptance criteria**:
- `ptools projects chdir` with no argument opens an arrow-key picker over configured projects and prints the resolved path for the chosen one — identical output to typing that name explicitly.
- `ptools projects chdir demo` (name given) is unchanged; no picker shown.
- Existing `demo/subdir`-style sub-path handling is unaffected when a name is typed directly.
- Cancelling the picker (escape) prints nothing and exits non-zero, so a wrapping shell function does not `cd` anywhere.

**Depends on**: none

**Notes**: `chdir` prints the resolved path to stdout for a shell wrapper function to `cd` into (see the command's own docstring example). The picker must preserve that "print path, no side effects beyond `Projects.switch()`" contract exactly.

**Status**: proposed — not approved
