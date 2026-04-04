# Phase 3: Retrieval + Review - Context

**Gathered:** 2026-03-23
**Status:** Ready for planning

<domain>
## Phase Boundary

Users and MCP clients can retrieve the most relevant, source-backed memory using keyword, semantic, or hybrid search — with context budgeting, provenance navigation, and the ability to promote trusted facts to canonical memory that takes priority in all future retrieval.

**In scope:** keyword search (PostgreSQL FTS), semantic search (pgvector), hybrid retrieval (RRF k=60), context budgeting with strict priority trimming (canonical→facts→summaries→raw), degraded-mode fallback, MCP `retrieve` tool, access-event audit (MCP-03, MCP-04), canonical memory CRUD (create, edit, delete, mark disputed/stale, promote from facts), canonical memory prioritized over extracted facts in results, conflict labeling in retrieval responses, review queue for duplicate/overlap groups, provenance navigation from any summary/fact/canonical item to raw archive, Search/Facts/Canonical/Review Queue/Audit web UI pages.

**Not in scope (deferred to Phase 4):** deletion cascade UI, backup/restore, first-run wizard, accessibility validation, per-source redaction. **Not in scope (deferred to Phase 5):** MCP ingest endpoint, watched folder.

</domain>

<decisions>
## Implementation Decisions

### Retrieval Architecture
- Retrieval service lives at `backend/app/domain/retrieval/service.py`
- Three modes: `keyword`, `semantic`, `hybrid`
- Keyword: PostgreSQL FTS `WHERE search_vector @@ plainto_tsquery('english', :q)`, ordered by `ts_rank_cd`
- Semantic: pgvector cosine similarity on `embeddings` table, filtered to `source_status='active'` and current model name. Only operates when embeddings exist.
- Hybrid: top-50 per mode, RRF merge k=60, top-20 final. Min threshold: `1/(60+25) ≈ 0.012`.
- Budget trimming strictly follows: canonical→facts→summaries→raw. Never truncate mid-item; skip if doesn't fit.
- Context budget: 2000 characters/tokens default (configurable). Response includes `budget_used`, `budget_limit`, `trimming_reason`.
- In-process LRU cache (256 entries, 60s TTL) keyed on `hash(query+filters+mode+budget)`. Invalidated on new index publications and policy changes (deletion events flush relevant entries). Using Python `functools.lru_cache` or `cachetools.TTLCache`.

### Degraded Mode (SRCH-06)
- If no embeddings exist: semantic search returns empty candidate pool; hybrid auto-falls-back to keyword-only with `degraded_mode: true` flag in response.
- If embeddings exist but provider unavailable for new content: serve cached embedded content; flag `degraded_mode: true`.
- Mode `hybrid` with no embeddings → effective `keyword` with status indicator.

### Canonical Memory (CANM-01 through CANM-05)
- New table: `canonical_memory` — id, raw_archive_id (nullable FK), fact_id (nullable FK), content, status (`active`|`disputed`|`stale`|`source_removed_review_required`), created_at, updated_at, promoted_from (`fact`|`manual`), promoted_by, provenance_note.
- Separate Alembic migration 0003.
- Service at `backend/app/domain/canonical_memory/service.py`.
- Promote fact to canonical: explicit user action only (CANM-03). Facts with empty source_span require explicit confirmation flag in request (CANM-04).
- Canonical items have `source_status` too (CANM-02 — they're never auto-suppressed; just flagged when source removed).
- In retrieval, canonical items are always ranked first above extracted facts.

### Review Queue (CANM-05)
- Review queue table: `review_queue_items` — id, conflict_group_id (FK), item_type (`duplicate`|`overlap`|`contradiction`), status (`pending`|`resolved`|`dismissed`), created_at, resolved_at, resolved_by, resolution_note.
- Separate migration in 0003 alongside canonical_memory.
- Service at `backend/app/domain/review_queue/service.py`.
- Items come from existing `conflict_groups` table (created in Phase 2). The review queue materializes them as actionable tasks.

### MCP Interface (MCP-01, MCP-03, MCP-04)
- MCP server setup already has the `mcp` SDK installed. Add MCP server module at `backend/app/mcp_server/server.py`.
- MCP transport: stdio for direct agent use; SSE endpoint for HTTP MCP clients.
- MCP `retrieve` tool takes: query, mode (`keyword`|`semantic`|`hybrid`), budget, filters (category, source_system, time_range).
- Response envelope matches the architecture spec (see retrieval-and-ranking.md).
- All MCP access events emit an `AuditEvent` with `event_type="mcp_retrieve"`, `actor` = MCP client identity from request context, operation_metadata includes: query_summary, result_count, retrieval_mode, policy_decision.
- Audit event retention: existing `audit_events` table is already 90-day capable (no TTL purge in v1 — all events retained).

### Audit View (WEBUI-06 partial — full WEBUI-06 in Phase 4)
- Phase 3 ships the Audit page with basic event list (paginated, newest first) and per-event detail drawer. More detailed logging configurable in Phase 4.

### Provenance Navigation (WEBUI-05)
- Every fact/summary/canonical item in the UI links to its source archive item.
- Provenance chain: fact → raw archive item (via raw_archive_id FK).
- Archive item detail view (modal or side panel) shows raw_content snippet, ingested_at, source_type.

### Agent Discretion
- Exact shadcn/ui components for search input, results cards, provenance drawers, review queue table.
- Exact polling vs. reactive strategy for search results (immediate on submit, no polling needed).
- SQL query structure for FTS (plainto_tsquery vs. websearch_to_tsquery — use `websearch_to_tsquery` for better multi-word handling).
- Exact LRU cache implementation (cachetools vs. stdlib).

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets (Post-Phase-2)
- `FtsEntry` ORM model at `backend/app/domain/derived_memory/models.py` — has `search_vector TSVECTOR`, `source_status` — ready for FTS queries.
- `Embedding` ORM model — has `Vector(384)`, `embedding_model`, `source_status` — ready for pgvector queries.
- `Fact` ORM model — has `source_span`, `confidence_tier`, `derivation_method`, `derivation_model`, `conflict_group_id` — ready for retrieval assembly.
- `Summary` ORM model — has `summary_text`, `model_used`, `raw_archive_id` — ready for retrieval assembly.
- `ConflictGroup` ORM model — has `group_type`, `source_status` — review queue materializes from this.
- `AuditEvent` ORM model at `backend/app/domain/audit/models.py` — `event_type`, `actor`, `operation_metadata`, `occurred_at` — ready for MCP access event emission.
- `backend/app/api/routes/archive.py` — existing route pattern; clone for search routes.
- `backend/app/domain/derived_memory/service.py` — `embed_text()` function for query embedding.
- `backend/app/main.py` — MCP server startup hook goes here.
- `backend/app/infrastructure/db.py` — `get_session` dependency pattern for all route handlers.

### Established Patterns
- Domain services: `backend/app/domain/<module>/service.py` — pure Python, no FastAPI imports.
- Route handlers: `backend/app/api/routes/<module>.py` — thin adapters.
- ORM queries: `session.execute(select(...).where(...))` async style.
- `source_status='active'` filter on every derived table query (CASCADE CONTRACT).
- `deleted_at IS NULL` filter on every `raw_archive` query.
- All datetime defaults: `lambda: datetime.now(timezone.utc)`.
- No `_key`, `_secret`, `_token`, `_password` column suffixes.
- `pytest.importorskip` for optional deps in test bodies.
- Test fixtures: `db_session`, `client` (from `conftest.py`); add `db_session_phase3` alias.

### Integration Points
- `backend/app/api/routes/__init__.py` — register new routers (search, canonical, review_queue, audit, mcp).
- `backend/app/main.py` — add MCP server startup in lifespan; add `canonical_memory.models` to `_assert_no_keys_in_schema` imports.
- `frontend/src/App.tsx` — replace `DisabledPage` routes for `/facts`, `/canonical`, `/search`, `/review-queue`, `/audit` with real page components.
- `frontend/src/lib/api.ts` — add search, canonical, review-queue, and audit API calls.
- Alembic migration chain: 0001 → 0002 → 0003 (new: canonical_memory + review_queue_items tables).

### Frontend Components to Build
- `SearchPage.tsx` — query input, mode toggle (keyword/semantic/hybrid), results list with provenance badges.
- `FactsPage.tsx` — list active facts with source spans, confidence tiers, promote/dispute/delete actions.
- `CanonicalPage.tsx` — list canonical items, edit/delete/mark-stale, provenance link to source.
- `ReviewQueuePage.tsx` — list pending review queue items (duplicates/overlaps), resolve/dismiss actions.
- `AuditPage.tsx` — paginated event list, detail drawer per event.
- `ProvenanceSidePanel.tsx` — reusable panel showing raw archive item detail, opened from any fact/canonical/summary card.

</code_context>

<specifics>
## Specific Ideas

- `retrieval/service.py` must assemble the exact JSON envelope from `retrieval-and-ranking.md` — `query`, `retrieval_mode`, `budget_used`, `budget_limit`, `trimming_reason`, `items[]`.
- Each item in `items[]` must carry: `id`, `type` (canonical|fact|summary|excerpt), `content`, `score`, `source_id`, `source_system`, `captured_at`, `conflict_label`, `provenance.derivation_method`, `provenance.derivation_model`, `provenance.source_excerpt`.
- MCP server must be bound to `127.0.0.1` only (DNS rebinding attack prevention — locked architectural decision).
- Canonical memory promotes require `confirmed: true` in the request when `source_span` is empty (CANM-04).
- Review queue items are created from conflict_groups when a group first becomes resolvable. Worker can materialize them after conflict detection runs. But in Phase 3 we also need a one-time backfill from existing conflict_groups.
- LRU cache must be invalidated on `write_fts_entry` and `write_embedding` calls (signal via an async pub/sub or simple version counter increment).
- Search API: `GET /api/search?q=...&mode=hybrid&limit=20&offset=0` — paginated, bounded.
- Retrieval API: `POST /api/retrieve` — takes structured request body matching MCP contract; returns full retrieval envelope.
- Provenance navigation: `GET /api/archive/{id}` — return archive item detail including raw_content truncated to first 2000 chars + metadata.

</specifics>

<deferred>
## Deferred Ideas

- Reranking via cross-encoder (optional per architecture; skip for Phase 3 — RRF ordering is sufficient for v1).
- Temporal decay and relevance weighting (v2 — requires real usage data).
- Confidence-based auto-curation (v2).
- Deep provenance chain (fact → chunk → summary → raw) — Phase 3 shows fact → raw only; full chain when chunking is added.
- Per-agent MCP permissions (v2).
- More detailed audit logging (Phase 4).
- WEBUI-02/03 keyboard + accessibility (Phase 4).

</deferred>

---

*Phase: 03-retrieval-review*
*Context gathered: 2026-03-23*
