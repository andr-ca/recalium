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
