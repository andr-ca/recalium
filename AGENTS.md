# Repository Guidelines

## Project Structure & Module Organization
`docs/requirements/` is the canonical product scope package; feature details live under `docs/requirements/features/platform-v1/`. `docs/architecture/` captures the approved system design and handoff set, while `docs/plans/` turns that baseline into execution-ready work. Use `docs/operational/` for reviews, QA plans, and validation evidence; place generated test artifacts in `docs/operational/tests/artifacts/`. The `agents/` folder holds shared instruction templates plus `agents/sync-agents.py`, and `.github/agents/` stores the project-scoped agent definitions synced from those templates.

Application code now lives under `backend/` and `frontend/`. Runtime data is host-mounted under `data/postgres/`, `backups/`, and `import/`; do not treat those mounted data folders as source code.

## Build, Test, and Development Commands
The application stack is now present. Use these commands for local development and validation.

- `docker compose up` starts `recalium-app` and `recalium-postgres` in development mode.
- `docker compose -f docker-compose.yml up -d` starts the production/base compose profile.
- `docker compose build` rebuilds the app image.
- `cd backend && pytest` runs the backend test suite with the active backend environment.
- `cd backend && pytest tests/e2e` runs live-stack E2E tests after Docker Compose is running.
- `cd frontend && pnpm install && pnpm build` installs and builds the UI.
- `cd frontend && pnpm test` runs Vitest tests.
- `python3 agents/sync-agents.py push --dry-run` previews syncing local agent prompts into `.github/agents/`.
- `python3 agents/sync-agents.py pull --dry-run` previews syncing project agents back to your local profile.
- `python3 agents/sync-agents.py push` or `pull` performs the sync after you confirm paths.

## Coding Style & Naming Conventions
Match the existing documentation style: short sections, direct language, and repo-relative Markdown links. New atomic requirement IDs should follow `<feature-short-name>-NNN` as defined in `docs/requirements/README.md`. Prefer descriptive filenames such as `recalium-v1-plan-review-final.md` over generic names like `notes.md`.

For Python changes in `agents/`, follow the existing script style: 4-space indentation, type hints, `pathlib.Path`, `snake_case` functions, and `UPPER_CASE` constants.

## Testing Guidelines
For docs-only changes, manually verify headings, links, and cross-document references. For `agents/sync-agents.py`, validate both `push` and `pull` paths with `--dry-run` before making real sync changes. Backend changes require targeted `pytest` coverage. Frontend changes require `pnpm build` and relevant Vitest coverage. UI release-readiness work must add Playwright and keyboard-only evidence. MCP changes require both unit/schema tests and live-client E2E evidence.

## Agent Skills

Use the Recalium use/test skill when starting the app, testing, validating MCP, exercising UI UAT, or collecting release evidence:

- Copilot: `.github/skills/recalium-use-and-test/SKILL.md`
- Claude: `.claude/skills/recalium-use-and-test/SKILL.md`
- Codex: `.codex/skills/recalium-use-and-test/SKILL.md`

Read `agents/project.instructions.md` for current repository-specific implementation context.

## Commit & Pull Request Guidelines
Current history uses conventional-style subjects such as `chore: initial commit`; keep that format with a lowercase type and imperative summary (`docs: update architecture handoff links`). PRs should state which package changed (`requirements`, `architecture`, `plans`, `operational`, or `agents`), summarize cross-file impacts, and list validation performed. When a change updates the documented process, link the source document that remains canonical after the PR.
