# Phase 4: Privacy + Operations - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Users have full, auditable control over their data — they can delete or redact any source conversation and watch derived data disappear from search immediately; they can restore from backup in under 15 minutes; and the system is keyboard-accessible and has a first-run wizard that takes a new user from empty system to first meaningful search result within 30 minutes.

**In scope:**
- Deletion cascade service: `DELETE /api/archive/{id}` sets `raw_archive.deleted_at`, propagates `source_status='source_removed'` to all derived tables (summaries, facts, embeddings, fts_entries, conflict_groups, review_queue_items, canonical_memory). Cascade is synchronous and immediate.
- Canonical memory from a deleted source retains `source_status='source_removed'` and `status='required_review'` (PRIV-02: NOT auto-deleted).
- Backup/restore service: `pg_dump`/`pg_restore` wrapper, scheduled daily asyncio task, 30-day retention, `POST /api/backup/restore` endpoint, UI warns when selected backup predates a deletion event (BKUP-01, BKUP-02, BKUP-03, PRIV-03).
- Archive deletion UI: Delete button on archive items, visual strikethrough/badge for deleted state, soft-deleted items optionally visible with "show deleted" toggle (PRIV-01 UI side).
- First-run wizard: shown when archive is empty and no keys configured; explains BYOK model, supported providers, estimated cost per 100 conversations (~$0.02 OpenAI / ~$0.03 Anthropic), links to key-creation pages, shows token cost estimate before bulk import confirmation (BYOK-01, BYOK-06).
- Audit improvements: per-event detail drawer in AuditPage (click row to expand), configurable verbosity (INFO/DEBUG toggle in Settings), `raw_archive_id` shown for archive-related events (WEBUI-06 full).
- Local telemetry counters: `telemetry` table stores daily counts (searches, retrievals, facts_reviewed, canonical_created, mcp_retrievals, ui_retrievals); visible in Settings; never exported (PORT-02).
- Authentication middleware: when `APP_BIND_HOST != 127.0.0.1`, a bearer token (`APP_AUTH_TOKEN` from `.env`) is required on all API requests; 401 if missing/wrong (PRIV-06).
- Accessibility: all core pages audited for missing ARIA labels, keyboard traps, unannounced state changes; Tab order verified; all interactive elements have `aria-label` (WEBUI-02, WEBUI-03).
- New Alembic migration 0004: `telemetry` table. No schema changes needed for deletion cascade (already has `deleted_at` on `raw_archive` and `source_status` on all derived tables).

**Not in scope (deferred to Phase 5):** MCP ingest, watched folder, portability bundle. **Not in scope (v2):** per-field redaction, GDPR data-subject export, multi-user auth.

</domain>

<decisions>
## Implementation Decisions

### Deletion Cascade (PRIV-01, PRIV-02)

**Mechanism:** Synchronous Python cascade inside the deletion service — no database triggers or ON DELETE CASCADE for `source_status`. The service:
1. Sets `raw_archive.deleted_at = now()` on the raw archive item.
2. Issues `UPDATE summaries SET source_status='source_removed' WHERE raw_archive_id = :id`.
3. Issues `UPDATE facts SET source_status='source_removed' WHERE raw_archive_id = :id`.
4. Issues `UPDATE embeddings SET source_status='source_removed' WHERE raw_archive_id = :id`.
5. Issues `UPDATE fts_entries SET source_status='source_removed' WHERE raw_archive_id = :id`.
6. Issues `UPDATE conflict_groups SET source_status='source_removed' WHERE id IN (SELECT conflict_group_id FROM facts WHERE raw_archive_id = :id)`.
7. Issues `UPDATE review_queue_items SET source_status='source_removed' WHERE conflict_group_id IN (SELECT id FROM conflict_groups WHERE source_status='source_removed')`.
8. Issues `UPDATE canonical_memory SET source_status='source_removed', status='required_review' WHERE raw_archive_id = :id` (PRIV-02: mark, not delete).
9. Writes audit event `event_type='archive_delete'`.
10. Invalidates retrieval cache.

All in a single `async with session:` block for atomicity. The cascade is idempotent (can be called twice safely).

**No new migration needed for the cascade:** `deleted_at` already exists on `raw_archive` (migration 0001), and `source_status` already exists on all derived tables.

**Route:** `DELETE /api/archive/{id}` → returns 204. Added to `archive.py`.

### Archive Listing with Deleted Items (PRIV-01)

The existing `GET /api/archive` already filters `deleted_at IS NULL`. Add optional query param `include_deleted=true` so the UI can show a "show deleted" toggle. Deleted items return with `status_badge="Deleted"` and `deleted_at` timestamp.

### Backup / Restore (BKUP-01, BKUP-02, BKUP-03, PRIV-03)

**Tool:** `pg_dump` / `pg_restore` (PostgreSQL custom format `-Fc`). The app container has `pg_dump` available via the `postgres` client tools installed alongside `psycopg2`.

**Backup service:** `backend/app/domain/backup/service.py`
- `create_backup()`: runs `pg_dump` via `asyncio.create_subprocess_exec`, saves to `/backups/recalium_{timestamp}.dump`; returns backup metadata dict.
- `list_backups()`: scans `/backups/*.dump`, returns sorted list with timestamps and sizes.
- `restore_backup(filename)`: runs `pg_restore` with `--clean --if-exists`, then reconnects app. Runs in subprocess so it doesn't deadlock on live sessions.
- `delete_old_backups()`: removes backups older than 30 days.
- `backup_predates_deletion(filename)`: checks if any `audit_events` with `event_type='archive_delete'` occurred after the backup timestamp.

**Scheduled task:** Added to `main.py` lifespan alongside the pipeline worker — daily asyncio task at midnight UTC. Uses `asyncio.create_task(backup_scheduler())`.

**Routes:** `backend/app/api/routes/backup.py`
- `GET /api/backup/list` → list of backups with timestamps, sizes, `has_post_deletion_events` flag.
- `POST /api/backup/trigger` → manual trigger, returns job status.
- `POST /api/backup/restore` → body `{"filename": "..."}`, streams progress or returns 200 when done.

**Backups directory:** `/backups` — mounted as `./backups` on host (already specified in architecture).

**15-minute SLA:** `pg_restore` on a personal-scale DB (< 1GB) completes in < 2 minutes typically. The 15-minute SLA is achieved. The restore endpoint is synchronous (waits for completion) with a 900s timeout.

**PRIV-03:** Future backups always exclude already-deleted data (because `pg_dump` snapshots current state where `deleted_at IS NOT NULL` rows are present but searches exclude them — wait, actually `pg_dump` dumps the full physical table including soft-deleted rows). Correction: `pg_dump` of the physical table includes soft-deleted rows. The PRIV-03 requirement says "future backups/exports exclude deleted/redacted data." This means the backup route should use a `--exclude-table-data raw_archive` approach plus a selective dump, OR simply note that `pg_dump` includes all rows and rely on the "UI flags older backups" mechanism. **Decision:** Use standard `pg_dump` (includes all rows, which is actually good for restore completeness), and the UI flags older backups that may contain data deleted since then (satisfying PRIV-03's "UI flags" clause). True exclusion of deleted rows from dumps is v2 (requires logical replication or custom ETL export).

### Authentication Middleware (PRIV-06)

A FastAPI middleware checks: if `settings.app_bind_host != "127.0.0.1"`, require `Authorization: Bearer {APP_AUTH_TOKEN}` header on all `GET/POST/PUT/PATCH/DELETE` requests to `/api/*` and `/mcp/*`. Returns 401 with `{"detail": "Authentication required"}` if missing or wrong. Passthrough for `/health`, `/api/docs`, `/api/redoc`, and static files.

New settings fields: `app_bind_host: str = "127.0.0.1"` and `app_auth_token: str = ""`. If `app_bind_host != "127.0.0.1"` and `app_auth_token == ""`, the app refuses to start with a clear error.

The middleware is added in `create_app()` in `main.py`. It's a plain Starlette `BaseHTTPMiddleware`.

### First-Run Wizard (BYOK-01, BYOK-06)

**Trigger:** React component checks on app load: if archive count == 0 AND no provider key is configured → show wizard.

**Wizard steps (3 steps):**
1. **Welcome + BYOK explanation:** "Recalium uses your own API keys (BYOK). Your data never goes to Recalium servers." Shows estimated cost: OpenAI ~$0.02/100 conversations (gpt-4o-mini), Anthropic ~$0.03/100 conversations (claude-3-haiku). Links to key-creation pages.
2. **Key setup:** Inline key entry + validate button (reuses existing Settings page logic). Shows "skip for now" option.
3. **First import:** Drag-drop or paste first conversation. On submit, shows estimated token count before confirm. **Cost estimation heuristic:** `estimated_tokens = len(text) / 4` (order-of-magnitude correct). Show `~{N} tokens ≈ ${cost:.4f}` where `cost = tokens * 0.00000015` (gpt-4o-mini input).

**State persistence:** Wizard dismissed status stored in `localStorage('wizard_dismissed')`. Re-shown on fresh install (localStorage cleared).

**Route:** A new `WizardPage.tsx` component; shown when `useWizardState()` hook returns `should_show: true`. Added to `App.tsx` as a conditional overlay or route `/wizard`.

### Audit View (WEBUI-06 full)

Existing `AuditPage.tsx` shows basic event list. Phase 4 adds:
- Click on any event row to expand a detail drawer (inline expand, not a modal — no shadcn Dialog).
- Detail shows: `id`, `event_type`, `actor`, `occurred_at`, full `operation_metadata` rendered as formatted JSON.
- Filter by event_type using a `<select>` dropdown (server-side filtering already supported by `list_audit_events`).
- "Verbose logging" toggle in Settings: adds `verbose_audit: bool` column to `settings` table (migration 0004). When enabled, the pipeline logs additional events (e.g., embedding model loaded, sensitivity gate results). The toggle is a simple checkbox in `SettingsPage.tsx`.

### Local Telemetry (PORT-02)

**Storage:** New `telemetry` table (migration 0004):
```sql
CREATE TABLE telemetry (
  id SERIAL PRIMARY KEY,
  date DATE NOT NULL UNIQUE,
  searches INT NOT NULL DEFAULT 0,
  retrievals INT NOT NULL DEFAULT 0,
  facts_reviewed INT NOT NULL DEFAULT 0,
  canonical_created INT NOT NULL DEFAULT 0,
  mcp_retrievals INT NOT NULL DEFAULT 0,
  ui_retrievals INT NOT NULL DEFAULT 0
);
```

**Increment mechanism:** `increment_telemetry(event_type, session)` function in `backend/app/domain/telemetry/service.py`. Called from:
- `search.py` route on every `GET /api/search` → `searches += 1`
- `retrieval.py` / `mcp_server.py` on every retrieve → `retrievals += 1`, `mcp_retrievals += 1` or `ui_retrievals += 1`
- `review_queue.py` route on resolve → `facts_reviewed += 1`
- `canonical.py` route on promote/create → `canonical_created += 1`

Uses PostgreSQL `INSERT ... ON CONFLICT (date) DO UPDATE SET searches = telemetry.searches + 1` (upsert). Never a SELECT first.

**API:** `GET /api/telemetry/summary` → last 30 days of daily counts. Added to `settings.py` route or new `telemetry.py` route.

**UI:** Section added to `SettingsPage.tsx` showing a simple table of last 7 days. Local only — never exported.

### Accessibility (WEBUI-02, WEBUI-03)

All interactive elements must have:
- `aria-label` on icon buttons, icon-only controls
- `role="status"` on loading states
- `role="alert"` on error messages
- No keyboard traps (modals/drawers must have Escape key handler)
- All form inputs have associated `<label>` (via `htmlFor` + `id`)
- Tab order follows visual order (no negative tabindex tricks)

Pages to audit: `IngestPage`, `SearchPage`, `ArchivePage`, `FactsPage`, `CanonicalPage`, `ReviewQueuePage`, `AuditPage`, `SettingsPage`.

### New Migration 0004

Migration 0004 adds:
1. `telemetry` table (see above)
2. `verbose_audit` column on `settings` table: `ALTER TABLE settings ADD COLUMN verbose_audit BOOLEAN NOT NULL DEFAULT false`

No changes to existing derived tables (source_status cascade already in place).

### Agent Discretion

- Exact backup file naming convention (timestamp format)
- Whether to show backup list as a new page or section in Settings
- Exact wizard UI layout and animation
- Whether to use a full-screen wizard overlay or a step-by-step modal (no shadcn Dialog — use plain HTML)
- Telemetry chart type (table vs. sparkline — table is simpler and avoids adding recharts)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets (Post-Phase-3)

- `RawArchiveItem` at `backend/app/domain/archive/models.py` — has `deleted_at`, `id` (UUID). Cascade service sets `deleted_at` here.
- `Summary`, `Fact`, `Embedding`, `FtsEntry`, `ConflictGroup` at `backend/app/domain/derived_memory/models.py` — all have `source_status` ENUM. Cascade updates these.
- `CanonicalMemoryItem` at `backend/app/domain/canonical_memory/models.py` — has `source_status` + `status`. Cascade sets `source_status='source_removed'` + `status='required_review'`.
- `ReviewQueueItem` — already has `source_status`.
- `AuditEvent` at `backend/app/domain/audit/models.py` — write `event_type='archive_delete'` after cascade.
- `audit_service.list_audit_events()` — already supports `event_type` filter; used to detect post-deletion events for backup warnings.
- `backend/app/worker/loop.py` — pattern for asyncio background tasks. Copy for backup scheduler.
- `backend/app/main.py` — lifespan creates `_worker_task`; add `_backup_task` same way.
- `backend/app/infrastructure/settings.py` — add `app_bind_host` and `app_auth_token` fields here.
- `backend/app/domain/retrieval/service.py` — has `invalidate_cache()` function; call from deletion cascade service.
- `frontend/src/lib/api.ts` — `request<T>()` helper; `DELETE` returning 204 must use raw `fetch()` (not `request()`).
- `frontend/src/pages/SettingsPage.tsx` — extend with telemetry section and verbose audit toggle.
- `frontend/src/pages/ArchivePage.tsx` — add Delete button and deleted item styling.
- `frontend/src/pages/AuditPage.tsx` — add per-event detail expansion and event_type filter.

### Established Patterns

- Domain services: `backend/app/domain/<module>/service.py` — pure Python, no FastAPI imports.
- Route handlers: `backend/app/api/routes/<module>.py` — thin adapters.
- ORM queries: `session.execute(select(...).where(...))` async style.
- `source_status='active'` filter on every derived table query (CASCADE CONTRACT).
- `deleted_at IS NULL` filter on every `raw_archive` query.
- All datetime defaults: `lambda: datetime.now(timezone.utc)`.
- No `_key`, `_secret`, `_token`, `_password` column suffixes.
- SQLAlchemy ENUM: always `postgresql.ENUM(name="source_status", create_type=False)` in migrations.
- `pytest.importorskip` for optional deps.
- `db_session_phase3` fixture in `conftest.py`; add `db_session_phase4` alias.
- Phase 4 adds telemetry module imports to `conftest.py` safe-import block.

### Integration Points

- `backend/app/api/routes/__init__.py` — register `backup_router`, `telemetry_router`.
- `backend/app/main.py` — add `backup_task` in lifespan; add auth middleware in `create_app()`.
- `frontend/src/App.tsx` — add `/wizard` route; conditional show on first visit.
- `frontend/src/lib/api.ts` — add `deleteArchiveItem()`, `listBackups()`, `triggerBackup()`, `restoreBackup()`, `getTelemetrySummary()`, `updateSettings()` (for verbose audit toggle).
- Alembic migration chain: 0001 → 0002 → 0003 → 0004 (new: telemetry table + verbose_audit column).

### Test Patterns

- Phase 4 tests use `db_session_phase4` fixture (alias for `db_session_phase3` with Phase 4 model imports).
- Deletion cascade tests: create raw item + derived data, call cascade service, assert all derived rows have `source_status='source_removed'`, assert retrieval returns empty.
- Backup tests: skip if `pg_dump` not available (mark with `pytest.importorskip` or `pytest.mark.skipif`).
- Telemetry tests: upsert idempotency, daily rollup.
- Auth middleware tests: call API without token when `app_bind_host=0.0.0.0`, expect 401.

</code_context>

<specifics>
## Specific Ideas

- The deletion cascade in `backend/app/domain/archive/service.py` must use a single `async with session:` block and run all UPDATEs before the final `session.commit()` to ensure atomicity.
- `DELETE /api/archive/{id}` should return `404` if the item doesn't exist or is already deleted.
- Backup filenames: `recalium_{YYYYMMDD_HHMMSS}.dump` — `datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")`.
- Backup restore: use `--clean --if-exists --no-owner --no-privileges` flags with `pg_restore` to avoid permission errors.
- Auth middleware: exempt paths `/health`, `/api/docs`, `/api/redoc`, `/openapi.json`, and all static files (anything not starting with `/api` or `/mcp`).
- First-run wizard: the "show wizard" check should be a separate `GET /api/status/onboarding` endpoint that returns `{"should_show_wizard": bool, "has_archive_items": bool, "has_configured_key": bool}`. This avoids the frontend needing to call multiple endpoints.
- Telemetry upsert SQL: `INSERT INTO telemetry (date, {col}) VALUES (:date, 1) ON CONFLICT (date) DO UPDATE SET {col} = telemetry.{col} + 1`.
- The `verbose_audit` column in `settings` table must NOT end in `_key`, `_secret`, `_token`, or `_password` (startup assertion passes).
- Wizard cost estimate: show as plain text: "~{N} tokens ≈ ${cost:.4f} (OpenAI gpt-4o-mini estimate)". Do not block import on cost estimate.
- Keyboard accessibility: all `<button>` elements already get keyboard focus by default in HTML. The main issues are: icon buttons without `aria-label`, and `<div onClick>` handlers that should be `<button>`.

</specifics>

<deferred>
## Deferred Ideas

- Per-field redaction (redact specific messages within a conversation rather than whole archive item) — v2.
- GDPR data-subject export bundle — v2 / Phase 5.
- Multi-user authentication with session cookies — v2 managed tier.
- `pg_dump` with selective row exclusion (dump only non-deleted rows) — v2.
- Telemetry charts / sparklines (recharts) — v2.
- Backup encryption — v2.
- Remote backup destination (S3, etc.) — v2.
- More granular audit verbosity levels (per-event-type toggle) — v2.
- Accessibility automated CI checks (axe-core integration) — post-v1.

</deferred>

---

*Phase: 04-privacy-operations*
*Context gathered: 2026-03-23*
