# Recalium Project Instructions

Use this file as the repository-specific companion to `core.instructions.md`, `python.instructions.md`, and `tdd.instructions.md`.

## Project summary

- Project name: Recalium.
- Purpose: local-first, MCP-native personal memory infrastructure that captures AI conversations, turns them into durable searchable memory, and exposes that memory to MCP-compatible clients.
- Primary users: local AI power users, developers, and MCP agent builders.
- Current phase: v1 release-readiness implementation and validation.
- Deployment model: two containers only for v1: `recalium-app` and `recalium-postgres`.

## In scope for v1

- Local Docker Compose runtime.
- FastAPI backend serving API, MCP, static UI, in-process worker loop, backup scheduler, and optional file watcher.
- PostgreSQL 16 with pgvector and full-text search.
- React/Vite/TypeScript local UI.
- BYOK provider configuration via `.env`.
- Raw archive, derived summaries/facts/embeddings/FTS, canonical memory, review queue, audit events, backup/restore, import/export, and MCP tools.
- Keyboard-operable core UI workflows.
- Release evidence for v1 acceptance criteria.

## Out of scope for v1

- Multi-user authentication or tenant policy engines.
- Recalium-hosted processing services.
- Separate worker, backup, watcher, Redis, queue, or vector database containers.
- Browser extension ingestion.
- Graph visualization.
- Automated memory decay beyond manual statuses.
- Hardcoded secrets or checked-in `.env` values.

## Key folders

- `backend/app/`: FastAPI app, API routes, domain services, infrastructure, MCP server, worker loop.
- `backend/tests/`: backend unit, domain, API, integration, MCP, worker, and live-stack E2E tests.
- `backend/migrations/`: Alembic migrations.
- `frontend/src/`: React app, pages, components, API client, tests.
- `docs/requirements/`: canonical product scope and acceptance criteria.
- `docs/architecture/`: approved architecture baseline and technical constraints.
- `docs/plans/`: execution planning package.
- `docs/operational/`: reviews, validations, test reports, and evidence artifacts.
- `docs/guides/`: local usage and operator guides.
- `agents/`: shared instructions, sync tooling, and agent-maintenance docs.
- `.github/agents/`: Copilot project agent definitions.
- `.github/skills/`: Copilot project skills.
- `.claude/skills/`: Claude project skills.
- `.codex/skills/`: Codex-style project skills.
- `import/`: mounted local import folder for watched-folder ingestion.
- `backups/`: mounted backup output directory.
- `data/postgres/`: host-bound PostgreSQL data directory.

## Key files

- `README.md`: user-facing project overview and quick start.
- `AGENTS.md`: repository-level agent rules and commands.
- `CLAUDE.md`: Claude/GSD project context and constraints.
- `GEMINI.md`: Gemini project context.
- `.env.sample`: root Docker Compose environment sample; keep sanitized.
- `backend/.env.sample`: backend local development sample; keep sanitized.
- `docker-compose.yml`: production/base two-container topology.
- `docker-compose.override.yml`: development overrides and exposed local PostgreSQL port.
- `backend/Dockerfile`: backend image and static UI copy path.
- `backend/app/main.py`: app factory, lifespan tasks, auth middleware, route registration, MCP mount, static serving.
- `backend/app/mcp_server/server.py`: MCP tools and server factory.
- `frontend/src/lib/api.ts`: typed UI API client.
- `frontend/src/App.tsx`: SPA route map.
- `docs/guides/local-use-and-test.md`: local startup, usage, testing, and MCP guide.
- `docs/operational/validations/recalium-v1-release-readiness-gap-register.md`: active release-readiness gap register.

## Technology and runtime notes

- Backend: Python 3.12+, FastAPI, Uvicorn, SQLAlchemy async, asyncpg, Alembic, Pydantic v2.
- Database: PostgreSQL 16+ with pgvector and full-text search.
- MCP: Python MCP SDK `>=1.26,<2`; do not upgrade to v2 without explicit approval and docs update.
- Frontend: React 19, TypeScript 5, Vite 8, Tailwind CSS 4.
- Python package manager: `uv`.
- Node package manager: `pnpm`.
- Secrets/config: `.env` only; update sanitized `.env.sample` when adding config.

## Development commands

- Start stack: `docker compose up`.
- Start production compose: `docker compose -f docker-compose.yml up -d`.
- Build images: `docker compose build`.
- Backend tests: run `pytest` from `backend` with the backend environment active.
- Frontend install/build/test: run `pnpm install`, `pnpm build`, and `pnpm test` from `frontend`.
- Agent sync dry run: `python3 agents/sync-agents.py push --dry-run` or `python3 agents/sync-agents.py pull --dry-run`.

## Required implementation workflow

- Inspect `git status -sb` before editing.
- Do not overwrite existing user changes.
- Prefer small, localized changes.
- For code changes, follow TDD: failing test first, implementation second, refactor third.
- Update docs and evidence whenever behavior, setup, commands, or public contracts change.
- Validate with the narrowest relevant tests first, then broaden.
- Do not claim release readiness without evidence under `docs/operational/`.

## MCP rules

- Default endpoint: `http://localhost:8000/mcp/sse`.
- MCP must remain localhost-first.
- Exposed mode requires bearer auth and transport protection.
- MCP retrieve responses must include item type, score, source links, provenance, conflict labels, budget/trimming reason, retrieval mode, and degraded-mode metadata.
- MCP ingest must converge on the same canonical ingest contract as UI/API/file watcher.
- MCP ingest release readiness requires source metadata, client identity, import method, idempotency key, sensitivity hint, project hint, requested processing mode, stable errors, and audit events.

## UI rules

- The v1 left navigation is: Ingest, Archive, Facts, Canonical, Search, Review Queue, Audit, Settings.
- Core workflows must be keyboard-operable.
- Do not hide important details behind hover-only UI.
- Use accessible labels, visible focus state, predictable focus order, and explicit loading/error/empty states.
- Provenance should be reachable from summaries, facts, canonical items, search results, and review items.
- Backup/restore must be operator-visible and must warn about backups that may contain deleted data.

## Data and privacy rules

- Raw archive is the source of truth and must retain source metadata.
- Derived memory must remain linked to source provenance.
- Canonical memory requires explicit user action.
- Deleting or redacting raw source data must suppress linked derived data from search/retrieval.
- Canonical memory from deleted sources remains only with source-removed/review-required state.
- External provider processing must be gated by sensitivity classification.
- Provider keys must never be persisted to the database, backups, exports, logs, or committed files.

## Domain glossary

- Raw Archive: original ingested source material.
- Derived Memory: summaries, extracted facts, embeddings, and FTS entries produced from raw archive items.
- Canonical Memory: trusted user-curated memory promoted explicitly by the user.
- Review Queue: grouped duplicate, overlapping, or conflicting extracted facts requiring user cleanup.
- Provenance: source-backed trace linking memory to raw archive, derivation process, timestamp, actor/client, and source excerpt/hash.
- MCP: Model Context Protocol interface used by agents and tools to ingest and retrieve memory.
- Tombstone/source removal: durable deletion/redaction state used to suppress removed source data.

## Agent skill resources

- Copilot skill: `.github/skills/recalium-use-and-test/SKILL.md`.
- Claude skill: `.claude/skills/recalium-use-and-test/SKILL.md`.
- Codex skill: `.codex/skills/recalium-use-and-test/SKILL.md`.

Use the skill when starting the app, testing, validating MCP, exercising UI UAT, collecting release evidence, or helping another agent use Recalium memory.

## Maintenance guidance

- Keep this file aligned with actual commands and folder structure.
- Update it whenever setup, runtime, MCP, UI, testing, or release evidence workflows change.
- Prefer repo-relative links and concrete commands over vague guidance.
