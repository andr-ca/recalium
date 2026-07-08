---
name: recalium-use-and-test
description: "Use when: starting Recalium locally, testing the app, validating MCP tools, exercising the UI, collecting release evidence, or helping an agent use Recalium memory. Keywords: Recalium, MCP, ingest_memory, retrieve_memory, local setup, Docker Compose, pytest, Playwright, UI UAT, backup restore."
---

# Recalium Use and Test Skill

## Purpose

Use this skill when an agent needs to start, use, test, or validate Recalium locally.

This skill applies to Copilot agents working in this repository.

## Required context

Read these files before acting:

1. `AGENTS.md`
2. `CLAUDE.md`
3. `docs/guides/local-use-and-test.md`
4. `docs/operational/validations/recalium-v1-release-readiness-gap-register.md`
5. `docs/requirements/features/platform-v1/acceptance-criteria.md`
6. `docs/architecture/api-and-mcp.md`
7. `docs/architecture/ui-architecture.md`

## Safety rules

- Never hardcode provider keys, bearer tokens, database passwords, or secrets.
- Use `.env`; update sanitized `.env.sample` when configuration changes.
- Keep v1 to two containers: `recalium-app` and `recalium-postgres`.
- Do not add Redis, Celery, a separate worker container, or a separate vector database for v1.
- Prefer `uv` for Python and `pnpm` for frontend work.
- Preserve the local-first and BYOK-by-default model.

## Start workflow

1. Inspect repository state and current branch.
2. Confirm `.env` exists from `.env.sample`.
3. Start Docker Compose from the repository root.
4. Wait for migrations and app readiness.
5. Confirm `http://localhost:8000/api/health` responds successfully.
6. In development, start the Vite UI from `frontend` and open `http://localhost:5173`.
7. In production/static mode, build `frontend/dist`, rebuild the app image, and open `http://localhost:8000`.

## First-use workflow

1. Open Settings or the first-run wizard.
2. Choose no-key local mode or validate provider keys from `.env`.
3. Ingest a small conversation through the Ingest page.
4. Confirm the archive item appears in Archive.
5. Search for content from the ingested item.
6. Inspect provenance before treating a result as durable memory.
7. Promote only explicitly selected facts to canonical memory.

## MCP workflow

The local MCP SSE endpoint is:

- `http://localhost:8000/mcp/sse`

Use this sequence:

1. Connect with an MCP client.
2. List tools.
3. Call `retrieve_memory` before starting a task to collect relevant context.
4. Call `ingest_memory` after a task to store source-backed durable context.
5. Call `get_fact_links` for linked facts.
6. Call `list_tags` to inspect the tag vocabulary.
7. Check audit events after machine access.

When calling `ingest_memory`, include `content`, `source_metadata`, `client_identity`, `import_method`, `idempotency_key` when available, `sensitivity_hint`, `project_hint`, and `processing_mode`. Missing `content` or `source_metadata` returns a stable validation error envelope.

Expected MCP tools today:

- `retrieve_memory`
- `ingest_memory`
- `get_fact_links`
- `list_tags`

Before claiming MCP is complete, verify the v1 gaps in the release readiness gap register are closed: audit metadata, invalid-input behavior, broader live-client evidence, and concurrent SSE clients.

## Backend test workflow

Run targeted tests first, then broaden:

1. Domain tests for changed services.
2. API tests for changed routes.
3. MCP tests for tool/resource changes.
4. Worker tests for queue/dispatcher changes.
5. Live-stack E2E tests after Docker Compose is running.

Save notable evidence under `docs/operational/tests/` and `docs/operational/tests/artifacts/`.

## Frontend test workflow

Use this order:

1. Type/build check with the frontend build script.
2. Vitest page/component tests.
3. Playwright E2E when configured.
4. Keyboard-only manual UAT for every core workflow.
5. Axe/accessibility smoke tests when configured.

Core UI workflows that must be keyboard-operable:

- ingest
- archive
- search
- fact review
- canonical edit
- review queue
- audit detail
- backup and restore

## Release evidence workflow

For each completed gap:

1. Link the changed files.
2. Link passing tests.
3. Add manual UAT notes when automation is not sufficient.
4. Store screenshots, traces, logs, or benchmark output under `docs/operational/tests/artifacts/`.
5. Update the release readiness gap register.

Do not claim release readiness until acceptance criteria 1-28 have direct automated or manual evidence.

## Common blockers

- UI missing in production: build `frontend/dist` before building the app image.
- Backend tests cannot connect: ensure dev Postgres is running and the test database exists.
- MCP client fails: use `/mcp/sse` and check exposed-mode bearer auth.
- Search degrades: confirm embeddings/providers are configured or use keyword mode.
- Provider key leaks: stop and remove the leak immediately; keys belong only in `.env`.
