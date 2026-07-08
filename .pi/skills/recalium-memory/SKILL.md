---
name: recalium-memory
description: "Use when: you want durable cross-session memory in pi. pi has no MCP, so reach Recalium via its local REST API — recall relevant context before a task and store source-backed memory after. Keywords: Recalium, memory, REST, ingest, search, recall, remember, provenance."
---

# Recalium Memory (pi — REST)

pi does not use MCP by design. Reach Recalium's local REST API directly (with
`curl`) to recall and store durable, source-backed memory across sessions.

## Prerequisites

- Recalium running: `curl -sf http://localhost:8000/api/health` returns `200`.
- If it's down, ask the user to start Recalium; do not fabricate a path.
- Localhost needs no auth. Exposed mode: add
  `-H "Authorization: Bearer $APP_AUTH_BEARER"` (read from `.env` — never hardcode).

## Retrieve before a task

```bash
curl -s "http://localhost:8000/api/search?q=<query>&mode=hybrid&budget=2000&limit=10"
```

Structured variant with filters:

```bash
curl -s -X POST http://localhost:8000/api/retrieve \
  -H 'Content-Type: application/json' \
  -d '{"query":"<query>","mode":"hybrid","budget":2000,"filters":{"canonical_only":false,"tags":[]}}'
```

The response envelope has `items[]` (`content`, `score`, `source_id`,
`source_system`, `captured_at`, `conflict_label`, `provenance`) plus
`degraded_mode`. Inspect provenance and `conflict_label` before trusting an item.
If `degraded_mode` is true, retry with `mode=keyword`.

## Ingest after a task

```bash
curl -s -X POST http://localhost:8000/api/ingest \
  -H 'Content-Type: application/json' \
  -d '{"content":"<durable, source-backed note>","source_name":"pi-cli"}'
```

Returns HTTP 202 `{"status":"accepted","item_count":N,"archive_ids":[...]}`.
`content` must be non-empty. Never ingest secrets, tokens, or passwords — redact first.

## Discipline

- Retrieve before acting; ingest durable outcomes after.
- Check provenance; surface conflicts to the user instead of resolving silently.
- Keep local-first, BYOK — no external calls beyond the user's config.

> Recalium also exposes MCP at `/mcp/sse` for MCP-native tools. pi uses REST here
> because it has no MCP client; an extension could add MCP support if desired.
