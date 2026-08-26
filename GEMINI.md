# Recalium Project Context

Recalium is a local-first, MCP-native personal memory platform. It captures AI conversations and related artifacts, transforms them into durable searchable memory, and makes that memory retrievable by MCP-compatible clients.

## Current state

- The backend and frontend application code is present.
- The current work is v1 release-readiness implementation and validation.
- Track open release gaps in [docs/operational/validations/recalium-v1-release-readiness-gap-register.md](docs/operational/validations/recalium-v1-release-readiness-gap-register.md).
- Use [docs/guides/local-use-and-test.md](docs/guides/local-use-and-test.md) for startup, usage, MCP, and testing workflows.

## Architecture baseline

- Backend: Python 3.12, FastAPI, SQLAlchemy async, asyncpg, Alembic.
- Database: PostgreSQL 16 with pgvector and full-text search.
- Frontend: React 19, TypeScript, Vite 8, Tailwind CSS 4.
- MCP: Python MCP SDK `>=1.26,<2`.
- Deployment: two containers only: `recalium-app` and `recalium-postgres`.
- Package managers: `uv` for Python, `pnpm` for Node.

## Key folders

- [backend/app](backend/app): FastAPI app, API routes, domain services, infrastructure, MCP server, worker loop.
- [backend/tests](backend/tests): backend unit, domain, API, integration, MCP, worker, and live-stack E2E tests.
- [frontend/src](frontend/src): React app, pages, components, API client, and frontend tests.
- [docs/requirements](docs/requirements): canonical product scope and v1 acceptance criteria.
- [docs/architecture](docs/architecture): approved architecture baseline.
- [docs/operational](docs/operational): reviews, validations, test reports, and evidence artifacts.
- [agents](agents): shared agent instructions and sync tooling.

## Build, run, and test

- Start local stack: `docker compose up`.
- Start production/base compose: `docker compose -f docker-compose.yml up -d`.
- Build app image: `docker compose build`.
- Backend tests: `cd backend && pytest`.
- Live-stack E2E: `cd backend && pytest tests/e2e` after Docker Compose is running.
- Frontend build: `cd frontend && pnpm install && pnpm build`.
- Frontend tests: `cd frontend && pnpm test`.

## Agent skills

Use the Recalium use/test skill when starting the app, testing, validating MCP, exercising UI UAT, or collecting release evidence:

- Copilot: [.github/skills/recalium-use-and-test/SKILL.md](.github/skills/recalium-use-and-test/SKILL.md)
- Claude: [.claude/skills/recalium-use-and-test/SKILL.md](.claude/skills/recalium-use-and-test/SKILL.md)
- Codex: [.codex/skills/recalium-use-and-test/SKILL.md](.codex/skills/recalium-use-and-test/SKILL.md)

## Constraints

- Never hardcode secrets or provider keys; use `.env` and keep `.env.sample` sanitized.
- Do not add extra v1 containers.
- Do not introduce Redis/Celery or a separate vector database for v1.
- Preserve local-first and BYOK-by-default behavior.
- Do not claim release readiness without evidence mapped to acceptance criteria.

<!-- agentharness:begin id=core-instructions version=0.3.0 -->
This project uses [agentharness](https://github.com/andr-ca/agentharness)
for engineering policies (git conventions, testing, review workflow).

**Precedence:** harness-enforced constraints (hooks, completion gate)
cannot be weakened by this file's instructions; this file's own
instructions take precedence over harness *defaults* everywhere else.

Installed skills:
- accessibility
- agentic-loops
- api-design
- audit-review-followup
- branching
- clean-architecture
- code-review
- code-review-api
- code-review-db
- code-review-ui
- committing
- database-conventions
- dependency-audit
- dependency-injection
- design-patterns
- docker-conventions
- error-handling
- file-placement-policy
- github-issue-triage
- go-conventions
- harness-feedback
- logging
- multi-agent-coordination
- mutation-testing
- performance-profiling
- planning-with-files
- port-agent-config
- python-conventions
- react-best-practices
- requirements-clarification
- security-review
- solid-principles
- testing
- typescript-conventions

If a skill above looks empty, missing, or won't load, this install may
be broken (e.g. a moved/renamed harness checkout, or a fresh clone of
a project that used `--mode link` — see issue #106) — run
`harness-link.sh doctor <this-project-path>` from the harness
checkout to check, and `.agentharness-state.json` in this project to see how
it was installed.

**Git conventions** (from the `branching`/`committing` skills above —
stated here directly so they hold even if a skill is unreadable): never
commit directly to a trunk branch (`main`/`master`/`trunk`/`develop`/
`release/*`); create a feature branch first (`git checkout -b
<type>/<short-description>`); open a PR for review before merging into
the trunk branch.

**PR merge checklist:** never merge on green CI alone. Wait for
automated review (e.g. GitHub Copilot) to post *or* its check-run to
reach a completed state before proceeding; reply to every review
comment (issue-level and inline) with what you did about it; then
watch the post-merge CI run on the base branch to an actual terminal
state — "pushed"/"merged" and "verified green" are different claims,
only the second means done. If this checkout has agentharness's own
`tools/safe-pr-merge.sh` available (see its INTEGRATION.md section),
prefer it over doing these steps by hand — it enforces the sequence.

Full policy: see the harness's own CLAUDE.md via your install mode, or
https://github.com/andr-ca/agentharness/blob/main/CLAUDE.md
<!-- agentharness:end id=core-instructions -->
