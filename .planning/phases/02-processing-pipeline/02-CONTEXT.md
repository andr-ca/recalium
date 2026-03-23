# Phase 2: Processing Pipeline - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Every ingested conversation is asynchronously transformed into summaries, extracted facts (with source spans, confidence tiers, model provenance), local embeddings, and FTS index entries — without blocking ingest — and no content ever reaches an external provider before the sensitivity gate approves it. The worker loop, sensitivity classifier, job status UI, and conflict detection are all in scope for this phase.

**In scope:** In-process async worker loop (asyncio.create_task in lifespan), PostgreSQL job queue (SKIP LOCKED), sensitivity gate (heuristics + local ML classifier), summarization/extraction via configured LLM provider, local embeddings via sentence-transformers, FTS indexing, derived-memory ORM models, conflict/duplicate detection (CANM-06), job status badges in Archive UI (auto-refresh while processing), BYOK-07 (invalid key → retryable failed state), BYOK-08 (per-function provider routing without reprocessing completed items), Alembic migration for derived-memory tables.

**Not in scope:** Keyword search, semantic search, hybrid retrieval (Phase 3), canonical memory workflows (Phase 3), deletion/redaction cascade (Phase 4), backup/restore (Phase 4), MCP server (Phase 5), watched folder (Phase 5), first-run wizard (Phase 4).

</domain>

<decisions>
## Implementation Decisions

### Worker Architecture
- Single `asyncio.create_task()` loop started in FastAPI lifespan (`lifespan` in `main.py`)
- Worker polls jobs table with `SELECT ... FOR UPDATE SKIP LOCKED`; processes one job at a time with bounded concurrency via `asyncio.Semaphore`
- CPU-heavy work (sentence-transformers inference) dispatched via `asyncio.to_thread()` to avoid blocking the event loop
- All external HTTP (OpenAI/Anthropic/Ollama API calls) via `httpx.AsyncClient`
- Worker loop is a single `asyncio.Task`; concurrency controlled by semaphore, not multiple tasks
- Pending/available jobs survive container restart because queue state is durable in PostgreSQL
- In-progress jobs older than a recovery threshold are re-queued on worker startup

### Sensitivity Classification
- Two-pass gate: keyword heuristics first (fast path), then a small local ML intent classifier as second pass
- Heuristics use keyword lists for `personal_profile` (name, birthday, address, age, etc.) and `relationship` (wife, husband, kids, friend X, etc.)
- ML classifier: use sentence-transformers zero-shot classification or a small fine-tuned intent model via `asyncio.to_thread()`
- Default sensitivity: `unclassified` — blocked from external processing unless user explicitly overrides
- Gate fires before any external provider call; policy decision recorded in job metadata
- Categories: `personal_profile`, `relationship`, `unclassified` (blocked by default), `general` (allowed)

### LLM Provider Strategy
- Provider-agnostic routing per function: embedding provider and summarization/extraction provider are independently configurable (satisfies BYOK-08)
- Route to whichever provider key is configured; user can set different providers for embedding vs. extraction
- If no LLM provider configured: skip summarization and LLM extraction; still run local embeddings (sentence-transformers all-MiniLM-L6-v2) and FTS indexing
- If no provider configured for embeddings: skip embedding job (not failed — marked `pending_provider`)
- Job status `pending_provider` when blocked on missing provider key; NOT counted as failed
- Invalid/rate-limited key → job enters `retryable_failed` state with error captured (satisfies BYOK-07)
- Provider keys read from settings at job dispatch time (not cached in job record)

### Job Status UI
- Archive card badge upgrades from Phase 1 `Ingested` to full pipeline state:
  - `Processing` — spinner icon, amber/neutral color
  - `Done` — green badge
  - `Failed` — red badge with inline retry button
  - `Pending Provider` — amber badge with tooltip "Configure an API key in Settings"
- Auto-refresh: page polls `/api/archive` every 5 seconds while any item has `Processing` status
- Clicking `Failed` expands the card to show last error message inline
- No WebSocket or SSE in Phase 2 — polling is sufficient for personal scale

### the agent's Discretion
- Exact polling interval granularity (5s default is a starting point; agent may tune)
- Specific shadcn/ui component choices for status badges and retry button
- SQL query structure for SKIP LOCKED job claims (exact CTE vs. subquery form)
- Chunk size for summarization (default to whole-conversation for v1 given personal-scale data volumes)
- Exact ML model used for intent classification second pass (zero-shot via sentence-transformers or lightweight HuggingFace model)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Job` ORM model already exists at `backend/app/domain/jobs/models.py` — has `job_type`, `raw_archive_id`, `status`, `attempts`, `max_attempts`, `error_message`, `claimed_at`, `completed_at`
- `RawArchiveItem` ORM model at `backend/app/domain/archive/models.py` — has `source_status` column (from Phase 1 schema)
- `backend/app/main.py` lifespan — `asynccontextmanager` already wired; worker task should be `asyncio.create_task()`'d here
- `backend/app/domain/settings/service.py` — existing BYOK key validation; `validate_openai_key`, `validate_anthropic_key`, `validate_ollama_key` functions to reuse for provider routing
- `frontend/src/components/ui/badge.tsx` — has `success`, `warning`, `destructive` variants; reuse for status badges
- `frontend/src/components/ArchiveItemCard.tsx` — existing card component to extend with status badge
- `frontend/src/pages/ArchivePage.tsx` — existing archive page; add polling logic here
- `frontend/src/lib/api.ts` — typed API client; add job status endpoint calls

### Established Patterns
- SQLAlchemy 2.x async ORM: `async with get_session() as session:` pattern (from Phase 1 routes)
- Domain services in `backend/app/domain/<module>/service.py` — pure Python, no FastAPI imports
- Route handlers in `backend/app/api/routes/<module>.py` — thin adapters calling domain services
- All datetime defaults use `lambda: datetime.now(timezone.utc)` (enforced from Phase 1 fixes)
- No column names with `_key`, `_secret`, `_token`, `_password` suffixes (startup assertion)
- `asyncio.to_thread()` for all CPU-bound work (established in Phase 1 architecture decisions)
- `httpx.AsyncClient` for all external HTTP calls

### Integration Points
- `backend/app/main.py` lifespan → start worker asyncio task on startup, cancel on shutdown
- `backend/app/api/routes/ingest.py` → already enqueues jobs after raw archive write (Phase 1 stub returns 501; Phase 2 wires this fully)
- `backend/app/domain/jobs/` → worker dispatcher, job claim, retry logic live here
- New modules needed: `backend/app/domain/derived_memory/` (summaries, facts, embeddings, FTS), `backend/app/domain/policy/` (sensitivity gate), `backend/app/worker/` (loop, dispatcher)
- Alembic migration: add derived_memory tables (summaries, facts, embeddings, fts_entries, conflict_groups) to existing 0001_initial or new 0002 migration

</code_context>

<specifics>
## Specific Ideas

- Worker task must be cancelled cleanly on lifespan shutdown (store the `asyncio.Task` handle and call `.cancel()` + `await` in the shutdown branch)
- Sensitivity gate must record its decision (category + confidence) in job metadata — not just block/allow; needed for audit trail and PRIV-04/PRIV-05 compliance
- `pending_provider` is a terminal-but-retryable state: when user later adds a provider key, these jobs should become eligible again (not require manual re-queue)
- Facts table MUST include `source_span`, `confidence_tier`, `derivation_method`, `derivation_model` — these are required fields per PIPE-02 and processing-pipeline.md; a fact without source_span is `low` confidence
- Conflict detection (CANM-06): duplicate/overlap grouping materializes a `conflict_groups` table linking fact IDs; flagged at derivation time, surfaced in Phase 3 review queue UI

</specifics>

<deferred>
## Deferred Ideas

- Real-time WebSocket/SSE push for job status — polling is sufficient for personal scale in v1
- Chunk-level granular processing (splitting conversations into chunks for long content) — whole-conversation as default unit for v1; chunking can be added in Phase 3 or as a refinement
- Per-provider cost estimation before bulk import (BYOK-06) — deferred to Phase 4 where the first-run wizard and settings UX ships

</deferred>

---

*Phase: 02-processing-pipeline*
*Context gathered: 2026-03-23*
