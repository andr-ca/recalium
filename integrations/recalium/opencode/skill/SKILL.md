---
name: recalium-memory
description: "Use when: you want durable cross-session memory in any project. Retrieve relevant prior context before a task and store source-backed memory after. Keywords: Recalium, memory, MCP, retrieve_memory, ingest_memory, get_fact_links, list_tags, recall, remember, provenance."
---

# Recalium Memory

Use Recalium as durable, local-first long-term memory in any project. It captures
conversations and facts once and lets any MCP-compatible client retrieve
source-backed context later — without re-explaining.

## When to use

- Before a task: recall relevant prior decisions, facts, and context.
- After a task: store durable, source-backed memory for future sessions.
- When you need linked facts (`get_fact_links`) or the tag vocabulary (`list_tags`).
- Any time the user says "remember this", "what did we decide", or "recall".

## Prerequisites

- Recalium runs locally as two Docker containers and exposes MCP over SSE.
- Confirm reachable: `GET http://localhost:8000/api/health` returns `200`.
- Use the MCP server registered as `recalium` (SSE: `http://localhost:8000/mcp/sse`).
- If health fails, ask the user to start Recalium; do not fabricate a repo path.
- Auth: localhost needs no token. Exposed mode sends
  `Authorization: Bearer <APP_AUTH_BEARER>` from the user's `.env` — never hardcode it.

## Tools

- `retrieve_memory` — search memory; returns budgeted, provenance-rich items.
- `ingest_memory` — store raw content as source-backed memory.
- `get_fact_links` — traverse links for a specific fact.
- `list_tags` — inspect the tag vocabulary with usage counts.

## Core loop: retrieve before, ingest after

1. **Retrieve first**: call `retrieve_memory` with a focused query before acting.
2. **Check provenance**: inspect `provenance`, `source_id`, `source_system`,
   `captured_at`, and `conflict_label` before trusting an item. Prefer
   `canonical_only=true` for vetted memory over raw archive.
3. **Do the task** using the recalled context.
4. **Ingest after**: call `ingest_memory` to persist durable, source-backed context.
5. **Never** treat an item as fact without its source; surface conflicts
   (`conflict_label`) to the user instead of silently choosing a side.

## retrieve_memory

Params: `query` (required), `mode` (`keyword` | `semantic` | `hybrid`, default
`hybrid`), `budget` (chars, default 2000), `category`, `source_system`,
`time_range_start` / `time_range_end` (ISO 8601), `canonical_only` (bool),
`tags` (all must match), `actor` (client identity for audit).

Response: `retrieval_mode`, `budget_used` / `budget_limit`, `trimming_reason`,
`degraded_mode`, and `items[]` with `id`, `type`, `content`, `score`, `source_id`,
`source_system`, `captured_at`, `conflict_label`, `provenance`, and (for links)
`source_fact_id` + `link_type`.

If `degraded_mode` is true, semantic search is unavailable — tell the user and
retry `mode="keyword"`.

## ingest_memory

Required: `content` (>= 10 chars), `source_metadata` (include `source_type` and
`source_name`; add conversation/session ids or a source URI when available).

Optional: `client_identity`, `import_method` (default `mcp_tool`),
`idempotency_key` (repeat-safe; replays return the same `archive_ids` with
`idempotent_replay: true`), `sensitivity_hint`, `project_hint`, `processing_mode`
(default `deferred`).

Success: `{"status": "accepted", "item_count": N, "archive_ids": [...]}`.
Never ingest secrets, tokens, keys, or passwords — redact first.

## get_fact_links

Params: `fact_id` (uuid), `direction` (`outgoing` | `incoming` | `both`).
Returns `links[]` with `link_type`, `confidence`, `entity_name`, `other_fact_id`,
`other_fact_text`, `created_by`. Use an item's `source_fact_id` as `fact_id` to expand.

## list_tags

Params: `prefix` (optional, e.g. `entity:`), `min_count` (default 0).
Returns `tags[]` (`id`, `name`, `fact_count`, `created_at`) sorted by usage. Use it
to discover valid tag names before filtering `retrieve_memory` by `tags`.

## Error envelope

`{"status": "error", "error": {"code", "message", "details", "retryable"}}`

- `validation_error` — fix the input (e.g. missing `content` / `source_metadata`).
- `idempotency_conflict` — reuse the prior result; do not force a new write.
- `internal_error` — `retryable: true`; retry once, then report to the user.

Surface `error.message` verbatim.

## Safety

- Never hardcode provider keys, bearer tokens, DB passwords, or secrets.
- Redact sensitive values before `ingest_memory`.
- Respect `conflict_label` — present conflicts, do not resolve them silently.
- Keep the local-first, BYOK posture: no external calls beyond the user's config.
