# Commit Guidelines

## Commit Sanity
- Commits should be small, meaningful and atomic. Each commit should represent a single logical change to the codebase.
- Commits should be self-contained and should not depend on other commits. If a change requires multiple commits, each commit should be able to stand on its own.
- Commits should be tested and verified before being pushed. Ensure that the code compiles, passes tests, and does not introduce any new issues.

## Commit Attribution
- Commits should not attribute Claude in the author/committer fields or the body.
- Commits should not include any personal notes or unrelated information. The commit message should focus on the change being made and its impact on the codebase.

## Commit Message Format
- Commit messages should be clear, concise, and descriptive. Use the imperative mood (e.g., "Fix bug" instead of "Fixed bug" or "Fixes bug").
- Commit messages should be short.
- Commit messages follow the following format:
  - `<type>(<scope>): <subject>`
  - `<type>`: one of `feat`, `fix`, `docs`, `ci`, `style`, `refactor`, `test`, `chore`, `perf`, `build`, `revert`.
  - `<scope>`: optional, a noun describing the section of the codebase affected (e.g., `api`, `ui`, `auth`, `core`, `docs`, `tests`, etc.)
  - `<subject>`: a brief description of the change

## Commit Body Guidelines
- Commit body should include only relevant information about the change in bullet points, if necessary.
- Commit body should avoid including any personal notes or unrelated information.
- Commit body should avoid including any sensitive information, such as passwords, API keys, or personal data.
