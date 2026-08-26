# External Ingest Contract

Status: implementation guide  
Created: 2026-08-25  
Audience: external clients, local-first agent daemons, MCP skill authors  
Tracks: [issue #41](https://github.com/andr-ca/recalium/issues/41)

## Purpose

Document the supported ways to ingest content into Recalium from outside the
web UI, including the canonical `source_metadata` shape, idempotency replay
rules, and a client-side outbox recipe for when the server is down.

## Supported ingest paths

| Path | When to use | Transport |
|------|-------------|-----------|
| **MCP `ingest_memory`** | Interactive agents / MCP-capable clients | SSE `http://localhost:8000/mcp/sse` (or LAN URL when exposed) |
| **REST `POST /api/ingest`** | UI paste, scripts, long-running daemons, outbox flushers | HTTP JSON |
| **REST `POST /api/ingest/file`** | One-shot file upload (`.json` / `.txt` / `.md`) | `multipart/form-data` |
| **Watched import folder** | Drop-file workflow | Host-mounted `import/` (see product docs) |

MCP remains the richest agent surface. REST text ingest now accepts the same
metadata fields as MCP so daemons do not need to speak MCP SSE just to flush
an outbox.

## Auth

- Bound to localhost (`APP_BIND_HOST=127.0.0.1`): no bearer required.
- Exposed beyond localhost: send `Authorization: Bearer <APP_AUTH_BEARER>` from
  `.env` on every `/api/*` and `/mcp/*` call (PRIV-06). Never hardcode the token.
- Health probe for outbox flushers: `GET /api/health` (also under auth when
  exposed — use the same bearer).

## REST: `POST /api/ingest`

### Minimal (UI / paste)

```http
POST /api/ingest
Content-Type: application/json

{
  "content": "User: hello\nAssistant: hi there, durable note for later.",
  "source_name": "optional-label"
}
```

Success: `202` with:

```json
{
  "status": "accepted",
  "item_count": 1,
  "archive_ids": ["<uuid>"],
  "idempotent_replay": false,
  "idempotency_key": null
}
```

`content` must be non-empty after strip and ≥ 10 characters (domain rule).

### Full (daemon / outbox — MCP-aligned)

```http
POST /api/ingest
Content-Type: application/json
Authorization: Bearer <APP_AUTH_BEARER>   # only when exposed

{
  "content": "Durable memory text, at least ten characters.",
  "source_metadata": {
    "source_type": "ntfy_pipeline",
    "source_name": "bobbonson-outbox",
    "conversation_id": "conv-123",
    "session_id": "sess-456"
  },
  "client_identity": "bobbonson-outbox-flusher",
  "import_method": "rest_api",
  "idempotency_key": "outbox-entry-uuid-or-hash",
  "sensitivity_hint": "normal",
  "project_hint": "bobbonson",
  "processing_mode": "deferred"
}
```

Field notes:

| Field | Required | Notes |
|-------|----------|-------|
| `content` | yes | ≥ 10 chars after strip |
| `source_name` | no | Top-level UI label; overridden by `source_metadata.source_name` when present |
| `source_metadata` | recommended for agents | Dict; see schema below |
| `client_identity` | recommended | Audit actor; defaults to `user_ui` |
| `import_method` | no | Defaults to `paste` (minimal) or `rest_api` (when metadata/idempotency present) |
| `idempotency_key` | recommended for outbox | Stable per queued entry |
| `sensitivity_hint` | no | One of: `general`, `normal`, `public`, `low`, `sensitive`, `personal`, `private`, `confidential` |
| `project_hint` | no | Free-form workspace hint |
| `processing_mode` | no | `deferred` (default), `immediate`, or `local_only` |
| `mode` | no | Reserved; default `text` |

## MCP: `ingest_memory`

Same semantic contract as the full REST body, via the MCP tool. Required:

- `content` (≥ 10 chars)
- `source_metadata` (required on MCP; optional but recommended on REST)

Optional: `client_identity`, `import_method` (default `mcp_tool`),
`idempotency_key`, `sensitivity_hint`, `project_hint`, `processing_mode`
(default `deferred`).

Success shape includes `idempotent_replay` and echoes `idempotency_key` /
`processing_mode`. Errors use the stable envelope:

```json
{
  "status": "error",
  "error": {
    "code": "validation_error | idempotency_conflict | internal_error",
    "message": "...",
    "details": {"field": "..."},
    "retryable": false
  }
}
```

On REST, validation failures are HTTP `422`; idempotency conflict is HTTP
`409` with the same error envelope in `detail`.

## Canonical ingest `source_metadata`

Ingest-side keys (write these):

| Key | Role |
|-----|------|
| `source_type` | Origin system label (e.g. `copilot_chat`, `ntfy_pipeline`, `claude_code`) |
| `source_name` | Human-readable source / session label |
| `conversation_id` | Optional conversation id |
| `session_id` | Optional session id (used as name fallback if `source_name` absent) |
| URI / other keys | Allowed; stored under `raw_archive.metadata_json.source_metadata` |

Legacy alias: `system` is accepted as a fallback for `source_type`.

### Not ingest fields (retrieval projections)

Retrieval items expose `source_system`, `source_id`, and `captured_at`. Those
are **read-side provenance projections**, not the ingest request schema. Do
not invent them as required ingest keys.

Rough mapping:

- ingest `source_type` → retrieval `source_system` (via archive / processing)
- archive id → retrieval `source_id`
- archive / fact timestamps → retrieval `captured_at`

## Idempotency semantics

Implemented in `ingest_text_content` (shared by MCP and REST):

1. If `idempotency_key` is set, look up non-deleted `raw_archive` rows where
   `metadata_json->>'idempotency_key'` matches.
2. **Same key + same content hash** → return existing `archive_ids`, set
   `idempotent_replay: true`. No duplicate insert.
3. **Same key + different content** → conflict (`idempotency_conflict` /
   HTTP 409). Not retryable; fix the client or use a new key.
4. **No key** → always insert a new archive row.

Outbox rule: assign a **stable key per queued entry** at enqueue time; on
flush, POST the **exact** payload again. Treat `accepted` (whether or not
`idempotent_replay`) as success and delete/mark the outbox row done. Treat
conflict as poison (surface for human review; do not spin forever).

## Client outbox recipe

Pattern for local-first agents (e.g. ntfy → proposed-changes → Recalium):

1. **Enqueue locally** (SQLite/file): store the full `POST /api/ingest` JSON
   body, including a UUID `idempotency_key`, while Recalium may be down.
2. **Health gate**: poll `GET /api/health` until `200`.
3. **Flush FIFO**: POST each pending body to `/api/ingest` with the same
   bearer (if required).
4. **Ack**:
   - `202` + `status=accepted` → mark entry flushed (including
     `idempotent_replay: true`).
   - `409` / `idempotency_conflict` → mark failed/poison; do not auto-retry.
   - `5xx` / connection error → leave pending; retry with backoff.
   - `422` validation → fix payload or quarantine; not a transient outage.
5. **Never** change `content` for an already-used `idempotency_key`.

Prefer REST for long-running flushers. Prefer MCP when the caller is already
an MCP session (interactive agent).

## curl examples

Minimal:

```bash
curl -sS -X POST http://localhost:8000/api/ingest \
  -H 'Content-Type: application/json' \
  -d '{"content":"User: remember the deploy window is Fridays.","source_name":"ops-note"}'
```

Idempotent outbox flush:

```bash
curl -sS -X POST http://localhost:8000/api/ingest \
  -H 'Content-Type: application/json' \
  -d '{
    "content":"User: remember the deploy window is Fridays.",
    "source_metadata":{"source_type":"ntfy_pipeline","source_name":"bobbonson"},
    "client_identity":"bobbonson-outbox",
    "idempotency_key":"outbox-001",
    "processing_mode":"deferred"
  }'
```

Replaying the same request returns the same `archive_ids` with
`idempotent_replay: true`.

## Related

- [Local use and test guide](local-use-and-test.md) — start stack, MCP setup
- MCP skill: `.claude/skills/recalium-memory/SKILL.md`
- Implementation: `backend/app/api/routes/ingest.py`,
  `backend/app/mcp_server/server.py`,
  `backend/app/domain/ingest/service.py`
