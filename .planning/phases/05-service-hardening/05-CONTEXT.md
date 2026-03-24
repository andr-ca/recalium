# Phase 5: Service Hardening - Context

**Gathered:** 2026-03-24
**Status:** Ready for planning

<domain>
## Phase Boundary

The system is portable, contract-stable, and ready for future service extraction — users can export and re-import their full memory bundle, MCP clients can ingest via the server directly, the watched folder enables frictionless ongoing ingestion, and all module boundaries are reviewed for deploy-profile separation.

**In scope:**
- **Watched import folder (INGT-04):** A configured directory (`WATCH_DIR` env var) is polled every N seconds (default 10s). Any `.json`, `.txt`, or `.md` file that appears is ingested via `ingest_file_content()`, then moved to a `processed/` subdirectory (not deleted). The watcher runs as an asyncio background task in the lifespan alongside the pipeline worker and backup scheduler.
- **MCP ingest tool (MCP-02, INGT-05):** A new `ingest_memory` tool registered on `mcp_app` in `mcp_server/server.py`. Accepts `content: str`, `source_name: str | None`, `source_type: str = "mcp_ingest"`, `actor: str = "mcp_client"`. Missing `content` or `content` too short → returns descriptive error dict (not an exception). Calls `ingest_text_content()` → returns `{"status": "accepted", "item_count": ..., "archive_ids": [...]}`.
- **Portability bundle export/import (PORT-01):** Open memory bundle format v1 JSON. Export: `GET /api/export/bundle` streams a JSON file with `{"format": "recalium-memory-bundle", "version": "1", "exported_at": ..., "items": [...]}` where each item is a full snapshot of a raw archive entry plus its derived data. Import: `POST /api/import/bundle` accepts the same JSON, ingests each item via the ingest service (dedup by content_hash — skip if already present). New route file `backend/app/api/routes/portability.py`.
- **API/MCP contract versioning + module boundary review (PORT-01 part):** Add `X-API-Version: 1` response header via middleware in `main.py`. Document contract version in `GET /health`. Review all domain modules for deploy-profile separation seams (comment markers only — no code restructuring needed for v1). Mark each domain boundary that would be a service extraction point in v2.

**Not in scope (v2):** Per-field redaction, GDPR data-subject export, multi-user auth, backup encryption, remote backup destinations, markdown-plus-assets export.

</domain>

<decisions>
## Implementation Decisions

### Watched Import Folder (INGT-04)

**Poll interval:** 10 seconds (configurable via `WATCH_POLL_INTERVAL` env var, default 10).
**Directory:** Configured via `WATCH_DIR` env var (default empty string — watcher disabled when empty).
**File handling:** After successful ingest, move file to `{WATCH_DIR}/processed/` subdirectory (create if not exists). On ingest error, move to `{WATCH_DIR}/failed/` with error info preserved in filename.
**Dedup:** Content hash dedup happens naturally via the ingest service (same content_hash = new archive item with same hash — currently not deduplicated at service level; watcher dedup is by filename to avoid re-processing moved files).
**Implementation:** `backend/app/domain/ingest/watcher.py` — `async def file_watcher_loop(watch_dir: str, poll_interval: int) -> None`. Main loop: `asyncio.sleep(poll_interval)` between polls. Scans `watch_dir/*.{json,txt,md}` (not in `processed/` or `failed/`). Processes each file with its own DB session.
**Startup registration:** In `lifespan()` in `main.py`, create task `_watcher_task = asyncio.create_task(file_watcher_loop(...))` only if `settings.watch_dir` is non-empty.
**New settings fields:** `watch_dir: str = ""` and `watch_poll_interval: int = 10`.

### MCP Ingest Tool (MCP-02, INGT-05)

**Tool name:** `ingest_memory` (alongside existing `retrieve_memory`).
**Parameters:**
- `content: str` — required; the raw text to ingest
- `source_name: str | None = None` — optional label
- `source_type: str = "mcp_ingest"` — defaults to `"mcp_ingest"`
- `actor: str = "mcp_client"` — for audit trail

**Validation (MCP-02):** Return descriptive error dict (not Python exception) for:
- `content` missing or empty: `{"error": "content is required and must be non-empty"}`
- `content` < 10 chars: `{"error": "content too short (minimum 10 characters)"}`

**Success response:** `{"status": "accepted", "item_count": ..., "archive_ids": [...]}`.
**Audit:** The `ingest_text_content()` call writes `actor` field in audit event. Pass `actor` from the MCP tool parameter.

### Portability Bundle (PORT-01)

**Export format (v1):**
```json
{
  "format": "recalium-memory-bundle",
  "version": "1",
  "exported_at": "<ISO 8601>",
  "items": [
    {
      "id": "<uuid>",
      "source_type": "<str>",
      "source_name": "<str|null>",
      "ingested_at": "<ISO 8601>",
      "raw_content": "<str>",
      "content_hash": "<str>",
      "conversation_count": <int>,
      "metadata": <dict|null>
    }
  ]
}
```
Deleted items (`deleted_at IS NOT NULL`) are excluded from export (PRIV-03 compliant).

**Import:** `POST /api/import/bundle` — reads JSON body, validates `format == "recalium-memory-bundle"` and `version == "1"`. For each item, calls `ingest_text_content()` with `content=item["raw_content"]` and `source_name=item.get("source_name")`. Dedup: if a `RawArchiveItem` with the same `content_hash` already exists (including deleted), skip it. Returns `{"imported": N, "skipped": N, "errors": [...]}`.

**Route file:** `backend/app/api/routes/portability.py` — registers `GET /api/export/bundle` and `POST /api/import/bundle`.
**Registration:** Add `portability_router` to `main.py`.

### API Contract Versioning

**`X-API-Version: 1` header:** Added via a simple middleware in `main.py` on all `/api/*` responses.
**`GET /health` response update:** Add `"api_version": "1"` field to the existing health response.
**Module boundary comments:** Add `# SERVICE-BOUNDARY: <module> — v2 extraction point` comments to `__init__.py` files of domain modules that would become separate microservices. Modules: `ingest`, `retrieval`, `backup`, `mcp_server`.

### New Settings Fields

```python
watch_dir: str = ""  # Empty = watcher disabled
watch_poll_interval: int = 10  # Seconds between polls
```

No `_key`, `_secret`, `_token`, `_password` suffixes.

### New Migration

No migration needed for Phase 5 — no new tables or columns. The portability bundle is a pure data export/import over existing tables.

### Agent Discretion

- Exact file move naming convention for failed files
- Whether to use `asyncio.gather` for parallel file processing in watcher
- Whether export uses `StreamingResponse` or builds full response in memory (memory OK for v1 — personal scale)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets (Post-Phase-4)

- `ingest_text_content(session, content, source_name)` at `backend/app/domain/ingest/service.py` — reuse directly for watcher and MCP ingest
- `ingest_file_content(session, filename, content, source_name)` — use for watcher (preserves filename)
- `RawArchiveItem` at `backend/app/domain/archive/models.py` — has `content_hash`, `raw_content`, `source_type`, `source_name`, `ingested_at`, `deleted_at`, `conversation_count`, `metadata_json`
- `worker_loop` at `backend/app/worker/loop.py` — copy asyncio task pattern for watcher
- `_backup_scheduler()` in `main.py` — pattern for background task registration
- `mcp_app` at `backend/app/mcp_server/server.py` — add new tool alongside `retrieve_memory`
- `get_session_factory()` at `backend/app/infrastructure/db.py` — use in MCP tool for DB session
- Health route at `backend/app/api/routes/health.py` (or wherever — check `backend/app/api/routes/__init__.py`) — update to add `api_version`

### Established Patterns

- Domain services: `backend/app/domain/<module>/service.py`
- Route handlers: `backend/app/api/routes/<module>.py`
- Background tasks: `asyncio.create_task(loop_fn())` in lifespan
- ORM queries: `session.execute(select(...).where(...))` async style
- `deleted_at IS NULL` filter on every `raw_archive` query
- Router registration: `app.include_router(router_var)` in `create_app()` in `main.py`
- All datetime defaults: `lambda: datetime.now(timezone.utc)`
- `pytest.importorskip` for optional deps in tests

### Integration Points

- `backend/app/main.py` — add watcher task + API version header middleware + portability router
- `backend/app/infrastructure/settings.py` — add `watch_dir` and `watch_poll_interval`
- `backend/app/mcp_server/server.py` — add `ingest_memory` tool
- `backend/app/api/routes/portability.py` — new file for export/import routes
- `backend/app/domain/ingest/watcher.py` — new file for file watcher loop
- `frontend/src/pages/SettingsPage.tsx` — optionally show `WATCH_DIR` status (non-blocking)

### Test Patterns

- Phase 5 tests use `db_session_phase5` fixture (alias for `db_session_phase4` with Phase 5 model imports — but no new models, so same fixture is fine)
- MCP ingest tests: call `ingest_memory()` directly (not via HTTP), assert DB state
- Watcher tests: create temp dir, write files, run watcher loop with poll_interval=0.01, assert files moved and DB items created
- Export tests: create archive items, call `GET /api/export/bundle`, parse JSON, assert all items present
- Import tests: call `POST /api/import/bundle` with valid bundle, assert items ingested; call with duplicate, assert skipped

</code_context>

<specifics>
## Specific Ideas

- Watcher loop: use `pathlib.Path(watch_dir).glob("*.json") | glob("*.txt") | glob("*.md")` (or `itertools.chain`) to collect files. Filter out files in `processed/` or `failed/` subdirs.
- Watcher file move: `shutil.move(str(file_path), str(processed_dir / file_path.name))` — if name conflict, append timestamp.
- MCP ingest tool: import `ingest_text_content` inside the tool function to avoid circular import at module load time.
- Export bundle: use `select(RawArchiveItem).where(RawArchiveItem.deleted_at.is_(None)).order_by(RawArchiveItem.ingested_at)`.
- Import dedup check: `select(RawArchiveItem).where(RawArchiveItem.content_hash == item["content_hash"])` — include deleted items in dedup check (don't re-import deleted content).
- `X-API-Version` header: add via `@app.middleware("http")` in `main.py` — simpler than a full middleware class for a single header.
- Health route: find existing `GET /health` and add `"api_version": "1"` to the response dict.
- `# SERVICE-BOUNDARY` comments in domain `__init__.py` files: single-line comment, non-invasive.

</specifics>

<deferred>
## Deferred Ideas

- Markdown-plus-assets export — v2 / explicitly out of scope
- Watched folder with inotify (Linux) or FSEvents (Mac) instead of polling — v2
- Import progress streaming — v2
- Export filtering (by date range, source type) — v2
- MCP ingest with file attachment support — v2
- Service extraction (actual microservices) — post-v1

</deferred>

---

*Phase: 05-service-hardening*
*Context gathered: 2026-03-24*
