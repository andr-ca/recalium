# Local Use and Test Guide

Status: implementation guide  
Created: 2026-04-27  
Audience: local users, developers, Copilot, Claude, Codex, and QA agents

## Purpose

This guide explains how to start Recalium locally, verify the app, use the UI, exercise MCP, and collect release-readiness evidence.

## Prerequisites

- Linux, macOS, or WSL2.
- Docker Compose v2 for the container path, **or** a native PostgreSQL 16 with the `pgvector` extension for the no-Docker path (see [Local installation without Docker (native)](#local-installation-without-docker-native)).
- Python 3.12+ for host-side backend tooling.
- `uv` for Python dependency management.
- Node.js compatible with Vite 8 and `pnpm` 10 for frontend work.
- Local ports available:
  - `8000` for Recalium API/UI.
  - `5435` for development PostgreSQL exposed by `docker-compose.override.yml`.
  - `5173` for Vite dev server.

## Environment setup

1. Copy the root sample environment file to `.env`.
2. Keep real provider keys only in `.env`.
3. Do not commit `.env`.
4. Leave provider keys empty for local/no-key mode.
5. Set `EMBED_BACKEND=none` for a smaller development image or `EMBED_BACKEND=cpu` for local sentence-transformers embeddings.

Required local defaults are documented in [.env.sample](../../.env.sample).

## Start the backend and database

From the repository root:

1. Start the stack with Docker Compose.
2. Wait for PostgreSQL health check, migrations, worker startup, backup scheduler startup, and Uvicorn readiness.
3. Open the API health endpoint at `http://localhost:8000/api/health`.
4. In development, open API docs at `http://localhost:8000/api/docs`.

Expected result:

- `recalium-postgres` is healthy.
- `recalium-app` is running.
- migrations complete without errors.
- API health returns success.
- logs do not contain provider keys or bearer tokens.

## Start the frontend during development

The production image serves the built React app from FastAPI. During development, run the Vite dev server separately from [frontend](../../frontend):

1. Install frontend dependencies with `pnpm install`.
2. Start Vite with `pnpm dev`.
3. Open `http://localhost:5173`.

Vite proxies `/api` requests to `http://localhost:8000` through [frontend/vite.config.ts](../../frontend/vite.config.ts).

## Build production UI assets

Before building the production app image:

1. Run `pnpm build` in [frontend](../../frontend).
2. Confirm the `frontend/dist` build output exists.
3. Build the Docker image.

The Dockerfile copies `frontend/dist` into the FastAPI static directory in [backend/Dockerfile](../../backend/Dockerfile).

## Local installation without Docker (native)

Run Recalium directly on the host with no containers. You provide PostgreSQL; the
FastAPI app, background worker, backup scheduler, and file watcher all run inside
the single Uvicorn process. This is an alternative to the Docker Compose path
above — use one or the other, not both on the same ports.

### Native prerequisites

- PostgreSQL 16 with the `pgvector` extension available on the server:
  - Debian/Ubuntu: `sudo apt install postgresql-16 postgresql-16-pgvector`
  - macOS (Homebrew): `brew install postgresql@16 pgvector`
- Python 3.12+ and `uv`.
- Node.js >= 20.19 and `pnpm` 10 (only if you want the UI).

### 1. Create the database and extension

Create the role, database, and `pgvector` extension. The extension must be
created once by a superuser — migration `0001` runs `CREATE EXTENSION IF NOT
EXISTS vector`, which is then a no-op:

```bash
sudo -u postgres psql -c "CREATE ROLE recalium LOGIN PASSWORD 'recalium';"
sudo -u postgres psql -c "CREATE DATABASE recalium OWNER recalium;"
sudo -u postgres psql -d recalium -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

Use a strong password for anything beyond local use and mirror it in `DATABASE_URL`.

### 2. Configure the backend environment

```bash
cd backend
cp .env.sample .env
```

[backend/.env.sample](../../backend/.env.sample) already targets a local database:
`DATABASE_URL=postgresql+asyncpg://recalium:recalium@localhost:5432/recalium`.
Keep `APP_BIND_HOST=127.0.0.1` for localhost mode (no auth). Put provider keys
only in `.env`.

### 3. Install backend dependencies

```bash
uv sync                       # runtime + dev dependencies
# For local sentence-transformers embeddings, also install the CPU ML extra:
uv sync --extra local-ml-cpu  # then set EMBED_BACKEND=cpu in .env
```

Leave `EMBED_BACKEND=none` to run with keyword search or a BYOK provider — no
local ML is required.

### 4. Run migrations

Run Alembic as a module (`python -m`) so `backend/` is on `sys.path` and the `app`
package resolves — the Docker image sets `PYTHONPATH=/app/backend` for the same
reason. `--env-file` loads `DATABASE_URL` for Alembic:

```bash
uv run --env-file .env python -m alembic upgrade head
```

### 5. Start the backend

```bash
# production-style
uv run --env-file .env python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
# development (live reload)
uv run --env-file .env python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Confirm health at `http://localhost:8000/api/health`. The worker, daily backup,
and (if `WATCH_DIR` is set) file watcher start automatically inside this process.
MCP is served at `http://localhost:8000/mcp/sse`, exactly as in the Docker path.

### 6. Run the frontend (optional)

Development (hot reload, proxies `/api` to the backend via
[frontend/vite.config.ts](../../frontend/vite.config.ts)):

```bash
cd frontend
pnpm install
pnpm dev            # http://localhost:5173
```

Production-style (served by the backend at `http://localhost:8000`):

```bash
pnpm build
mkdir -p ../backend/app/static
cp -r dist/* ../backend/app/static/
```

The backend serves `backend/app/static` when that directory exists; otherwise it
assumes the Vite dev server is in use.

### Native ports

- `8000` API/UI, `5173` Vite dev, `5432` native PostgreSQL (the Docker dev
  override uses `5435` instead to avoid clashing).

### Native troubleshooting

- `CREATE EXTENSION "vector"` fails or migrations error on `vector`: install the
  `pgvector` package for your PostgreSQL 16 server, then create the extension as a
  superuser (step 1).
- Alembic cannot find the database: ensure `DATABASE_URL` is loaded
  (`uv run --env-file .env …`) and PostgreSQL is listening on `localhost:5432`.
- `ModuleNotFoundError: No module named 'app'` from Alembic or Uvicorn: run them
  as modules (`python -m alembic …`, `python -m uvicorn …`) from `backend/`, or
  export `PYTHONPATH="$PWD"` first (this mirrors the Docker image's
  `PYTHONPATH=/app/backend`).
- UI missing at `:8000`: build the frontend and copy `dist` into
  `backend/app/static`, or use the Vite dev server at `:5173`.
- Port already in use: a running Docker stack also binds `8000` — stop it with
  `docker compose down` before starting the native app on the same port.

## First local usage path

### 1. Open the app

- Production/static mode: `http://localhost:8000`.
- Vite dev mode: `http://localhost:5173`.

### 2. Configure providers or skip keys

- Use Settings or the first-run wizard.
- Leave keys empty to use local storage, browsing, and keyword search.
- Provider keys are read from `.env` and must not be stored in the database.

### 3. Ingest content

Use the Ingest page to paste conversation text or upload `.json`, `.txt`, or `.md` files.

Expected result:

- The response is accepted only after raw archive persistence and required records commit.
- The item appears in Archive.
- Processing status is visible.

### 4. Browse archive

Use Archive to confirm raw item visibility, processing status, failed jobs, retry actions, and deletion behavior.

### 5. Search and retrieve

Use Search for keyword, semantic, or hybrid retrieval.

Expected result:

- Keyword search works without provider keys.
- Degraded mode is visible when embeddings/providers are unavailable.
- Results include source-backed provenance and budget/trimming metadata.

### 6. Review facts

Use Facts to inspect extracted facts, source spans, confidence, conflicts, tags, and promotion actions.

Expected result:

- The page supports editing fact text, marking facts disputed or stale, archiving/deleting noisy facts, showing archived/deleted facts, and promoting active facts to canonical memory.
- Archived and deleted facts are hidden from the default list.

### 7. Manage canonical memory

Use Canonical to edit trusted memory, mark items stale/disputed, and inspect source provenance.

### 8. Resolve review queue items

Use Review Queue to resolve duplicate, overlapping, or conflicting facts.

Expected result:

- Each queue item shows conflict-group metadata, active candidate facts, source snippets, confidence labels, a resolution note, and Resolve/Dismiss actions.

### 9. Audit access

Use Audit to inspect access events, actors, operation metadata, result counts, and policy decisions where available.

### 10. Backup and restore

Use Settings → Backup and Restore to:

- list backups
- see deleted-data warnings
- trigger a backup
- restore from a backup with confirmation

Restore testing still needs saved timing evidence before the 15-minute restore SLA can be closed.

## MCP usage path

Recalium mounts MCP SSE at `http://localhost:8000/mcp/sse`.

### Connect Claude Code

Register Recalium as a user-scoped MCP server so every Claude Code session
(in any project) can ingest and retrieve memory:

```bash
claude mcp add --scope user --transport sse recalium http://localhost:8000/mcp/sse
claude mcp list   # expect: recalium ... ✔ Connected
```

Requirements and notes:

- The docker compose stack must be running (`docker compose up -d`); if it is
  down, Claude Code shows the server as failed and reconnects when it is back.
- New sessions pick up the server automatically; sessions already open when
  you register it must be restarted to see the tools.
- Verified end-to-end 2026-07-08: `ingest_memory` → async pipeline (gate →
  FTS → embeddings) → `retrieve_memory` returns the item via hybrid search
  with provenance metadata.

Minimum agent workflow:

1. Connect to the SSE endpoint.
2. List available tools.
3. Ingest source-backed session content through `ingest_memory`.
4. Retrieve relevant context through `retrieve_memory` before starting a task.
5. Follow provenance links before trusting important facts.
6. Record any generated durable insight through MCP ingest after the task.

Current MCP tools:

- `retrieve_memory`
- `ingest_memory`
- `get_fact_links`
- `list_tags`

When calling `ingest_memory`, include:

- `content`
- `source_metadata` with at least a `source_type` and a useful `source_name`, `conversation_id`, or `session_id` when available
- `client_identity`
- `import_method`
- `idempotency_key` when available
- `sensitivity_hint`
- `project_hint`
- `processing_mode`

MCP validation failures return a stable error envelope with `status`, `error.code`, `error.message`, `error.details`, and `error.retryable`.

Release-ready MCP still requires broader live-client tests, richer audit metadata evidence, and concurrent SSE validation.

## Backend test layers

Run backend tests from [backend](../../backend) with the backend virtual environment active.

Recommended layers:

- Unit/domain tests under [backend/tests/domain](../../backend/tests/domain).
- API tests under [backend/tests/api](../../backend/tests/api).
- MCP tests under [backend/tests/mcp](../../backend/tests/mcp).
- Worker tests under [backend/tests/worker](../../backend/tests/worker).
- Live-stack E2E tests under [backend/tests/e2e](../../backend/tests/e2e) after Docker Compose is running.

The default test database URL is defined in [backend/tests/conftest.py](../../backend/tests/conftest.py).

## Frontend test layers

Run frontend tests from [frontend](../../frontend):

- `pnpm build` for TypeScript and production build validation.
- `pnpm test` for Vitest component/page tests.
- Playwright E2E once the config is added.

Release-ready UI requires tests for every core page plus keyboard-only workflows.

## Manual UAT checklist

Use keyboard only for each workflow:

- Ingest paste and file upload.
- Archive search, retry, and delete confirmation.
- Search mode selection, filters, and result provenance.
- Facts edit/status/promote/provenance.
- Canonical edit/status/provenance.
- Review Queue comparison and resolution.
- Audit detail inspection.
- Backup trigger and restore confirmation.

Failure conditions:

- Hidden focus.
- Mouse-only action.
- Hover-only details.
- Unlabeled input/button.
- State change not announced or visibly confirmed.

## Evidence locations

- Test reports: [docs/operational/tests](../operational/tests).
- Test artifacts: [docs/operational/tests/artifacts](../operational/tests/artifacts).
- Validation reports: [docs/operational/validations](../operational/validations).

## Troubleshooting

### App starts but UI is missing

- In development, use the Vite dev server.
- In production, build `frontend/dist` before rebuilding the app image.

### Tests cannot connect to PostgreSQL

- Confirm Docker Compose is running.
- Confirm dev PostgreSQL is exposed on localhost port `5435`.
- Confirm `recalium_test` exists or create it before running integration tests.

### MCP client cannot connect

- Use `/mcp/sse`, not only `/mcp`.
- Confirm the app is bound to localhost.
- In exposed mode, include the configured bearer token.

### Search returns no semantic results

- Confirm embeddings exist.
- Confirm provider keys or local embeddings are configured.
- Keyword search should still work in degraded mode.
