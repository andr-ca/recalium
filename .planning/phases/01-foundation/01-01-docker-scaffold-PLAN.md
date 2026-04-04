---
wave: 1
depends_on: []
requirements_addressed: [BKUP-04, WEBUI-04]
files_modified:
  - docker-compose.yml
  - docker-compose.override.yml
  - .env.sample
  - .gitignore
  - backend/entrypoint.sh
  - backend/Dockerfile
  - frontend/Dockerfile
  - Makefile
autonomous: true
---

<objective>
Bootstrap the two-container Docker topology with bind-mount volumes, entrypoint retry logic, and the .env/.env.sample skeleton. After this plan, `docker compose up` starts both containers, the app container waits for PostgreSQL to be ready, and host-visible data directories exist at ./data/postgres and ./backups.

Purpose: Establishes the durable-storage contract (BKUP-04) and the two-container layout that all other plans depend on.
Output: docker-compose.yml, docker-compose.override.yml, .env.sample, .gitignore, backend/entrypoint.sh, backend/Dockerfile, frontend/Dockerfile, Makefile
</objective>

<tasks>

<task id="1" name="Write docker-compose.yml (production base)">
  <read_first>
    - docs/architecture/container-topology.md
    - .planning/research/PITFALLS.md (Pitfall 7 — bind mounts)
    - .planning/phases/01-foundation/01-CONTEXT.md (D-05, D-06, D-07)
  </read_first>
  <action>
Create `docker-compose.yml` at repo root with the following exact content:

```yaml
# Recalium — production base compose file.
# WARNING: Data lives at ./data/postgres and ./backups on the HOST.
# NEVER run `docker compose down -v` — it will NOT destroy bind-mount data,
# but that flag is dangerous in general. Use `docker compose down` only.

services:
  recalium-postgres:
    image: pgvector/pgvector:pg16
    container_name: recalium-postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      # Bind mount — data on host filesystem, safe from `docker compose down -v`
      - ./data/postgres:/var/lib/postgresql/data
    networks:
      - recalium-net
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 10
      start_period: 10s

  recalium-app:
    build:
      context: .
      dockerfile: backend/Dockerfile
    container_name: recalium-app
    restart: unless-stopped
    depends_on:
      recalium-postgres:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@recalium-postgres:5432/${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_HOST: recalium-postgres
      POSTGRES_PORT: "5432"
      APP_ENV: ${APP_ENV:-production}
      LOG_LEVEL: ${LOG_LEVEL:-info}
      OPENAI_API_KEY: ${OPENAI_API_KEY:-}
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:-}
      OLLAMA_BASE_URL: ${OLLAMA_BASE_URL:-}
      OLLAMA_API_KEY: ${OLLAMA_API_KEY:-}
    ports:
      # Bind to localhost only — prevents accidental LAN exposure
      - "127.0.0.1:${APP_PORT:-8000}:8000"
    volumes:
      - ./backups:/app/backups
      - ./import:/app/import
    networks:
      - recalium-net
    entrypoint: ["/app/entrypoint.sh"]

networks:
  recalium-net:
    driver: bridge
```

Key constraints:
- Use `pgvector/pgvector:pg16` image (includes pgvector 0.8.x pre-installed).
- Port binding is `127.0.0.1:${APP_PORT:-8000}:8000` — NEVER `0.0.0.0`.
- Bind mounts for `./data/postgres`, `./backups`, `./import` — NOT named volumes.
- `depends_on` with `condition: service_healthy` so the entrypoint gets a live PG.
- API keys are injected via environment from `.env` — empty strings if not set.

Create `docker-compose.override.yml` (development overrides — hot-reload, exposed PG port):

```yaml
# Development overrides — applied automatically by `docker compose up` in dev.
# In production, use: `docker compose -f docker-compose.yml up`

services:
  recalium-postgres:
    ports:
      # Expose PG directly for local DB tools (dev only)
      - "127.0.0.1:5432:5432"

  recalium-app:
    build:
      context: .
      dockerfile: backend/Dockerfile
      target: development
    environment:
      APP_ENV: development
      LOG_LEVEL: debug
    volumes:
      - ./backend:/app/backend
      - ./backups:/app/backups
      - ./import:/app/import
    command: ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "/app/backend"]
```

Note: `--host 0.0.0.0` in the override is intentional for container-internal binding only — the host-side port mapping in `docker-compose.yml` remains `127.0.0.1:${APP_PORT:-8000}:8000`.
  </action>
  <acceptance_criteria>
    - `grep -n "127.0.0.1" docker-compose.yml` returns the APP_PORT line
    - `grep -n "named_volumes\|^volumes:" docker-compose.yml` returns 0 lines (no top-level volumes section)
    - `grep -n "./data/postgres" docker-compose.yml` returns 1 line
    - `grep -n "./backups" docker-compose.yml` returns 1 line
    - `grep -n "./import" docker-compose.yml` returns 1 line
    - `grep -n "pgvector/pgvector:pg16" docker-compose.yml` returns 1 line
    - `grep -n "service_healthy" docker-compose.yml` returns 1 line
    - `grep -n "0.0.0.0" docker-compose.yml` returns 0 lines
  </acceptance_criteria>
</task>

<task id="2" name="Write .env.sample and .gitignore">
  <read_first>
    - .planning/phases/01-foundation/01-CONTEXT.md (D-12 — keys never in DB)
    - AGENTS.md (global .env/.env.sample rule)
  </read_first>
  <action>
Create `.env.sample` at repo root:

```bash
# Recalium Environment Variables
# Copy this file to .env and fill in real values.
# SECURITY: .env is gitignored. Never commit .env.
# SECURITY: API keys live ONLY here — never in the database. The DB stores
#           only a 4-character fingerprint and a boolean (key_configured).

# ── PostgreSQL ──────────────────────────────────────────────────────────────
POSTGRES_USER=recalium
POSTGRES_PASSWORD=change_me_in_production
POSTGRES_DB=recalium

# ── Application ─────────────────────────────────────────────────────────────
# APP_ENV: "production" or "development"
APP_ENV=development
# LOG_LEVEL: "debug", "info", "warning", "error"
LOG_LEVEL=info
# APP_PORT: host port that maps to container port 8000
APP_PORT=8000

# ── BYOK Provider Keys (optional — system works without them) ────────────────
# OpenAI: https://platform.openai.com/api-keys
# Leave empty to operate in degraded mode (keyword search only, no embeddings via OpenAI).
OPENAI_API_KEY=

# Anthropic: https://console.anthropic.com/settings/keys
# Leave empty to skip Anthropic-backed processing.
ANTHROPIC_API_KEY=

# Ollama: set URL if you run a local Ollama instance.
# Example: http://host.docker.internal:11434
OLLAMA_BASE_URL=
# Ollama API key (only needed if your Ollama deployment requires auth)
OLLAMA_API_KEY=
```

Create `.gitignore` at repo root (merge with any existing content):

```
# Environment secrets — NEVER commit .env
.env
.env.local
.env.*.local

# Bind-mount data directories — live on host, not in git
data/
backups/
import/

# Python
__pycache__/
*.py[cod]
*.egg-info/
.venv/
.uv/
dist/
build/
*.so
.pytest_cache/
.ruff_cache/
.mypy_cache/
htmlcov/
.coverage

# Node / Frontend
frontend/node_modules/
frontend/dist/
frontend/.pnpm-store/
frontend/.vite/
frontend/coverage/

# Editor / OS
.DS_Store
.idea/
.vscode/settings.json
*.swp
*.swo

# Docker
docker-compose.override.yml.local
```
  </action>
  <acceptance_criteria>
    - `grep -n "OPENAI_API_KEY=" .env.sample` returns 1 line with empty value
    - `grep -n "ANTHROPIC_API_KEY=" .env.sample` returns 1 line with empty value
    - `grep -n "POSTGRES_PASSWORD=" .env.sample` returns 1 line
    - `grep -n "never in the database" .env.sample` returns 1 line (security comment)
    - `grep -n "^\.env$" .gitignore` returns 1 line
    - `grep -n "^data/$" .gitignore` returns 1 line
    - `grep -n "^backups/$" .gitignore` returns 1 line
  </acceptance_criteria>
</task>

<task id="3" name="Write backend/entrypoint.sh and Dockerfiles">
  <read_first>
    - .planning/phases/01-foundation/01-CONTEXT.md (D-08 — entrypoint retry loop)
    - .planning/research/STACK.md (Python 3.12, uv 0.10.12)
  </read_first>
  <action>
Create `backend/entrypoint.sh`:

```bash
#!/usr/bin/env bash
# Recalium app container entrypoint.
# 1. Waits for PostgreSQL to be ready (retry loop, max 60s).
# 2. Runs `alembic upgrade head` to apply pending migrations.
# 3. Starts Uvicorn.

set -euo pipefail

PGHOST="${POSTGRES_HOST:-recalium-postgres}"
PGPORT="${POSTGRES_PORT:-5432}"
PGUSER="${POSTGRES_USER:-recalium}"
PGDB="${POSTGRES_DB:-recalium}"

MAX_WAIT=60
ELAPSED=0
INTERVAL=2

echo "[entrypoint] Waiting for PostgreSQL at ${PGHOST}:${PGPORT}..."
until pg_isready -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${PGDB}" -q; do
  if [ "${ELAPSED}" -ge "${MAX_WAIT}" ]; then
    echo "[entrypoint] ERROR: PostgreSQL did not become ready within ${MAX_WAIT}s. Exiting."
    exit 1
  fi
  echo "[entrypoint] PostgreSQL not ready yet. Waiting ${INTERVAL}s... (${ELAPSED}/${MAX_WAIT}s elapsed)"
  sleep "${INTERVAL}"
  ELAPSED=$((ELAPSED + INTERVAL))
done

echo "[entrypoint] PostgreSQL is ready. Running migrations..."
cd /app
alembic -c backend/alembic.ini upgrade head

echo "[entrypoint] Migrations complete. Starting Uvicorn..."
exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --log-level "${LOG_LEVEL:-info}"
```

Create `backend/Dockerfile` (multi-stage: base → production; development target for override):

```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base

# Install system dependencies (pg_isready for entrypoint health check)
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv (Python package manager)
RUN pip install uv==0.10.12

WORKDIR /app

# Copy dependency files first (layer cache)
COPY backend/pyproject.toml backend/uv.lock* ./backend/

# Install Python dependencies
RUN cd backend && uv sync --frozen --no-dev

COPY backend/ ./backend/
COPY backend/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Production: pre-built frontend static files
FROM base AS production
COPY frontend/dist/ ./backend/app/static/

FROM base AS development
# No static copy in dev — Vite dev server handles frontend separately

# Default to production target
FROM production
```

Create `frontend/Dockerfile` (for future use; not wired into docker-compose.yml yet since frontend is served as static):

```dockerfile
# syntax=docker/dockerfile:1
# Frontend build container — produces ./dist for copy into backend image.
FROM node:22-alpine AS builder

RUN npm install -g pnpm@10.32.1

WORKDIR /app/frontend
COPY frontend/package.json frontend/pnpm-lock.yaml* ./
RUN pnpm install --frozen-lockfile

COPY frontend/ ./
RUN pnpm build

FROM scratch AS export
COPY --from=builder /app/frontend/dist /dist
```

Create `Makefile` at repo root:

```makefile
.PHONY: up down logs build shell-app shell-db migrate reset-dev

## Start all services (development mode with hot-reload)
up:
	docker compose up

## Start in production mode (no override file)
up-prod:
	docker compose -f docker-compose.yml up -d

## Stop services (data is preserved — bind mounts on host)
down:
	docker compose down
	@echo "Data preserved at ./data/postgres and ./backups"

## View logs
logs:
	docker compose logs -f

## Build images
build:
	docker compose build

## Open shell in app container
shell-app:
	docker compose exec recalium-app bash

## Open psql in postgres container
shell-db:
	docker compose exec recalium-postgres psql -U $${POSTGRES_USER:-recalium} -d $${POSTGRES_DB:-recalium}

## Run alembic migrations manually
migrate:
	docker compose exec recalium-app alembic -c backend/alembic.ini upgrade head

## Reset dev environment (PRESERVES DATA — only removes containers)
## If you want to also wipe the DB: manually delete ./data/postgres/
reset-dev:
	@echo "Stopping containers (data preserved at ./data/postgres)..."
	docker compose down
	docker compose build --no-cache
	docker compose up
```
  </action>
  <acceptance_criteria>
    - `grep -n "pg_isready" backend/entrypoint.sh` returns 2 lines (wait loop + command)
    - `grep -n "alembic.*upgrade head" backend/entrypoint.sh` returns 1 line
    - `grep -n "MAX_WAIT=60" backend/entrypoint.sh` returns 1 line
    - `grep -n "set -euo pipefail" backend/entrypoint.sh` returns 1 line
    - `grep -n "python:3.12-slim" backend/Dockerfile` returns 1 line
    - `grep -n "uv==0.10.12" backend/Dockerfile` returns 1 line
    - `grep -n "postgresql-client" backend/Dockerfile` returns 1 line
    - `grep -n "down -v" Makefile` returns 0 lines (never use -v)
    - `bash -n backend/entrypoint.sh` exits 0 (valid shell syntax)
  </acceptance_criteria>
</task>

</tasks>

<verification>
Run from repo root after all tasks complete:

1. `docker compose config --quiet` — validates compose YAML parses without errors
2. `grep -c "127.0.0.1" docker-compose.yml` — must be ≥ 1 (port binding)
3. `grep "0.0.0.0" docker-compose.yml` — must return 0 lines
4. `grep "^data/$" .gitignore && grep "^backups/$" .gitignore && grep "^\.env$" .gitignore` — all three must match
5. `bash -n backend/entrypoint.sh` — must exit 0
6. Copy `.env.sample` to `.env`, then run `docker compose up --dry-run` (Docker Compose 2.x) or `docker compose config` to confirm variable substitution resolves without errors
</verification>

<must_haves>
1. Bind mounts `./data/postgres`, `./backups`, `./import` are in `docker-compose.yml` — NOT named volumes. Verified: `grep "named_volumes\|^volumes:" docker-compose.yml` returns 0 lines.
2. App container port is mapped as `127.0.0.1:${APP_PORT:-8000}:8000` — never `0.0.0.0`. Verified: `grep "0.0.0.0" docker-compose.yml` returns 0 lines.
3. `backend/entrypoint.sh` has a retry loop (max 60s) before `alembic upgrade head` — entrypoint never fails silently if PG is slow. Verified: `grep "MAX_WAIT=60" backend/entrypoint.sh` returns 1 line.
</must_haves>
