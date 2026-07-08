#!/usr/bin/env bash
# Recalium SessionStart hook (Claude Code).
# Checks the local memory service and injects a usage reminder as session context.
# Exits 0 even when Recalium is down so it never blocks a session.
set -uo pipefail

URL="${RECALIUM_URL:-http://localhost:8000}"

if curl -sf -m 3 -o /dev/null "$URL/api/health" 2>/dev/null; then
  # SessionStart hooks can inject context via JSON on stdout.
  cat <<JSON
{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"Recalium memory is available at ${URL} (MCP: ${URL}/mcp/sse). Before starting, call retrieve_memory to recall relevant prior context. After finishing, call ingest_memory to store durable, source-backed memory. Always check item provenance before trusting a result."}}
JSON
else
  echo "Recalium memory service not reachable at ${URL} — start it to enable cross-session memory." >&2
fi

exit 0
