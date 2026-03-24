#!/usr/bin/env bash
# Recalium dev container entrypoint.
# Same as entrypoint.sh but starts uvicorn with --reload for live code reloading.
# Used only in the development Docker Compose override.

set -euo pipefail

PGHOST="${POSTGRES_HOST:-recalium-postgres}"
PGPORT="${POSTGRES_PORT:-5432}"
PGUSER="${POSTGRES_USER:-recalium}"
PGDB="${POSTGRES_DB:-recalium}"

MAX_WAIT=60
ELAPSED=0
INTERVAL=2

echo "[dev-entrypoint] Waiting for PostgreSQL at ${PGHOST}:${PGPORT}..."
until pg_isready -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${PGDB}" -q; do
  if [ "${ELAPSED}" -ge "${MAX_WAIT}" ]; then
    echo "[dev-entrypoint] ERROR: PostgreSQL did not become ready within ${MAX_WAIT}s. Exiting."
    exit 1
  fi
  echo "[dev-entrypoint] PostgreSQL not ready yet. Waiting ${INTERVAL}s... (${ELAPSED}/${MAX_WAIT}s elapsed)"
  sleep "${INTERVAL}"
  ELAPSED=$((ELAPSED + INTERVAL))
done

echo "[dev-entrypoint] PostgreSQL is ready. Running migrations..."
cd /app/backend
alembic upgrade head

echo "[dev-entrypoint] Migrations complete. Starting Uvicorn with --reload..."
exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --reload \
  --reload-dir /app/backend \
  --log-level "${LOG_LEVEL:-debug}"
