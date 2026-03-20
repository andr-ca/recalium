# Repository Guidelines

## Project Structure & Module Organization
`docs/requirements/` is the canonical product scope package; feature details live under `docs/requirements/features/platform-v1/`. `docs/architecture/` captures the approved system design and handoff set, while `docs/plans/` turns that baseline into execution-ready work. Use `docs/operational/` for reviews, QA plans, and validation evidence; place generated test artifacts in `docs/operational/tests/artifacts/`. The `agents/` folder holds shared instruction templates plus `agents/sync-agents.py`, and `.github/agents/` stores the project-scoped agent definitions synced from those templates.

## Build, Test, and Development Commands
There is no application build pipeline committed yet, so day-to-day work is mostly documentation and agent maintenance.

- `python3 agents/sync-agents.py push --dry-run` previews syncing local agent prompts into `.github/agents/`.
- `python3 agents/sync-agents.py pull --dry-run` previews syncing project agents back to your local profile.
- `python3 agents/sync-agents.py push` or `pull` performs the sync after you confirm paths.
- `pytest` is the planned backend test entry point documented in `docs/operational/tests/qa-automation-stack.md`, but no runnable test suite is checked in yet.

## Coding Style & Naming Conventions
Match the existing documentation style: short sections, direct language, and repo-relative Markdown links. New atomic requirement IDs should follow `<feature-short-name>-NNN` as defined in `docs/requirements/README.md`. Prefer descriptive filenames such as `recalium-v1-plan-review-final.md` over generic names like `notes.md`.

For Python changes in `agents/`, follow the existing script style: 4-space indentation, type hints, `pathlib.Path`, `snake_case` functions, and `UPPER_CASE` constants.

## Testing Guidelines
For docs-only changes, manually verify headings, links, and cross-document references. For `agents/sync-agents.py`, validate both `push` and `pull` paths with `--dry-run` before making real sync changes. Future automated checks should align with the planned QA stack: `pytest`, Playwright, Ruff, mypy, and `markdownlint-cli2`.

## Commit & Pull Request Guidelines
Current history uses conventional-style subjects such as `chore: initial commit`; keep that format with a lowercase type and imperative summary (`docs: update architecture handoff links`). PRs should state which package changed (`requirements`, `architecture`, `plans`, `operational`, or `agents`), summarize cross-file impacts, and list validation performed. When a change updates the documented process, link the source document that remains canonical after the PR.
