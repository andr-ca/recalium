#!/usr/bin/env bash
# Recalium Stop hook (Claude Code).
# Reminds the agent to persist durable outcomes to Recalium. Never blocks.
set -uo pipefail

URL="${RECALIUM_URL:-http://localhost:8000}"

if curl -sf -m 3 -o /dev/null "$URL/api/health" 2>/dev/null; then
  echo "Reminder: persist durable outcomes to Recalium via ingest_memory (include source_metadata + a stable idempotency_key)." >&2
fi

exit 0
