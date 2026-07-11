# Recalium

Recalium is a local-first, MCP-native personal memory platform. Your conversation history and derived memory live in your own PostgreSQL, and processing runs locally by default — enabling an optional BYOK provider (OpenAI or Anthropic) sends only the content being processed to that provider, and nothing else leaves your machine. It captures conversations and artifacts from AI tools, turns them into durable searchable memory, and exposes that memory to local UI workflows and MCP-compatible agents.

> **Privacy model — local custody, optional remote processing.** Storage, retrieval, and the default embedding/extraction path are fully local (no API key required). "Local-first" refers to data custody and the no-key default; it does **not** mean processing is always on-device. If you configure a BYOK key, the specific content you process is sent to that third-party provider under their terms. The built-in sensitivity gate runs before any external call.

## Current implementation status

The repository contains a working FastAPI/PostgreSQL/React foundation with backend tests and MCP tools. It is now in v1 release-readiness implementation: startup, usage, UI completion, MCP contract hardening, automated testing, and agent skill documentation are being closed against the v1 acceptance criteria.

Track release gaps in [docs/operational/validations/recalium-v1-release-readiness-gap-register.md](docs/operational/validations/recalium-v1-release-readiness-gap-register.md).

## Architecture baseline

- Backend: Python 3.12, FastAPI, SQLAlchemy async, asyncpg, Alembic.
- Frontend: React 19, TypeScript, Vite 8, Tailwind CSS 4.
- Database: PostgreSQL 16 with pgvector and full-text search.
- MCP: Python MCP SDK `>=1.26,<2`.
- Deployment: two containers only: `recalium-app` and `recalium-postgres`.
- Secrets: `.env` only; never hardcode keys or commit real secrets.

## Quick start

1. Copy [.env.sample](.env.sample) to `.env` and keep real values local.
2. Start the stack from the repository root with Docker Compose.
3. Confirm the API is healthy at `http://localhost:8000/api/health`.
4. In development, run the Vite UI from [frontend](frontend) and open `http://localhost:5173`.
5. In production/static mode, build [frontend](frontend) first, rebuild the app image, then open `http://localhost:8000`.

See [docs/guides/local-use-and-test.md](docs/guides/local-use-and-test.md) for the detailed local setup, UI, MCP, and testing walkthrough.

### Run without Docker

Prefer a native setup? Provide PostgreSQL 16 with `pgvector`, then run the backend with `uv` and the UI with `pnpm` — no containers. See [Local installation without Docker (native)](docs/guides/local-use-and-test.md#local-installation-without-docker-native).

## First use

1. Open the local UI.
2. Complete Settings or first-run wizard.
3. Leave provider keys empty for no-key local mode, or configure keys in `.env` for BYOK provider-backed processing.
4. Ingest a small conversation by paste or file upload.
5. Confirm it appears in Archive.
6. Search for the ingested content.
7. Inspect provenance before promoting any fact to canonical memory.

## MCP endpoint

The local MCP SSE endpoint is:

- `http://localhost:8000/mcp/sse`

Current tools:

- `retrieve_memory`
- `ingest_memory`
- `get_fact_links`
- `list_tags`

The v1 MCP contract still needs the release-readiness hardening tracked in the gap register: full ingest metadata, idempotency, stable errors, expanded evidence, and concurrent-client validation.

## Testing

Backend tests live under [backend/tests](backend/tests). Frontend tests live under [frontend/src/tests](frontend/src/tests). Release evidence belongs under [docs/operational/tests](docs/operational/tests) and [docs/operational/tests/artifacts](docs/operational/tests/artifacts).

Start with the detailed testing guidance in [docs/operational/tests/README.md](docs/operational/tests/README.md) and [docs/guides/local-use-and-test.md](docs/guides/local-use-and-test.md).

## Agent resources

Project agents should load the Recalium use/test skill when starting the app, validating MCP, exercising the UI, or collecting release evidence:

- Copilot: [.github/skills/recalium-use-and-test/SKILL.md](.github/skills/recalium-use-and-test/SKILL.md)
- Claude: [.claude/skills/recalium-use-and-test/SKILL.md](.claude/skills/recalium-use-and-test/SKILL.md)
- Codex: [.codex/skills/recalium-use-and-test/SKILL.md](.codex/skills/recalium-use-and-test/SKILL.md)

Repository-specific agent context lives in [agents/project.instructions.md](agents/project.instructions.md).

## Key documentation

- Requirements: [docs/requirements/README.md](docs/requirements/README.md)
- v1 acceptance criteria: [docs/requirements/features/platform-v1/acceptance-criteria.md](docs/requirements/features/platform-v1/acceptance-criteria.md)
- Architecture: [docs/architecture/README.md](docs/architecture/README.md)
- API and MCP: [docs/architecture/api-and-mcp.md](docs/architecture/api-and-mcp.md)
- UI architecture: [docs/architecture/ui-architecture.md](docs/architecture/ui-architecture.md)
- Plans: [docs/plans/README.md](docs/plans/README.md)

## Safety notes

- Do not run destructive data commands unless explicitly requested.
- Do not commit `.env` or real provider keys.
- Do not add extra v1 containers.
- Do not claim release readiness without evidence mapped to acceptance criteria.
