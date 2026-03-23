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
