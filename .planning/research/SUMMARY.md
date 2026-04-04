# Project Research Summary

**Project:** Recalium — Local-First MCP-Native Personal Memory Platform
**Domain:** AI conversation archive + personal memory retrieval
**Researched:** 2026-03-22
**Confidence:** HIGH

## Executive Summary

Recalium is a local-first personal memory platform that imports AI conversation history from multiple vendors (ChatGPT, Claude, etc.), processes it into layered memory (raw archive → summaries → extracted facts → canonical memory), and exposes that memory to AI agents via the MCP protocol with hybrid retrieval and strict context budgeting. The expert approach for this class of product is a modular monolith: one Python (FastAPI) container and one PostgreSQL container, with an in-process asyncio worker loop handling all derivation work. PostgreSQL serves as the primary store, FTS engine, vector search backend (via pgvector), and job queue — eliminating Redis, Celery, and dedicated vector database containers for personal scale.

The recommended approach is to build in strict dependency order: durable storage + raw ingest first, then the async processing pipeline, then retrieval and canonical memory workflows, then privacy enforcement and operational hardening. No competitor combines multi-vendor import, source-span provenance on every extracted fact, hybrid RRF retrieval with context budgeting, canonical curation, conflict detection, and a comprehensive audit trail in a local-first BYOK model — this is the unoccupied position in the market, and the feature set is well-defined and validated against competitors (Mem0/OpenMemory, basic-memory, MCP Reference Memory).

The two primary product risks are the **cold-start problem** (users must reach a successful search result within 30 minutes) and **extraction quality** (more than 50% trivial or wrong facts causes abandonment). The technical risks are all well-documented: event loop starvation from CPU-bound inference, orphaned derived data after deletion, and mixed-model embedding spaces after provider switches. All of these have clear mitigations. The critical path runs through: schema design with cascade-aware deletion semantics → in-process worker with proper `asyncio.to_thread()` usage → pgvector index setup after data load → sensitivity gate before any external provider call.

---

## Key Findings

### Recommended Stack

The backend is Python 3.12 + FastAPI 0.135.1 + PostgreSQL 16 + pgvector 0.8.2, managed by `uv`. SQLAlchemy 2.x async + asyncpg is the ORM/driver pair; Alembic handles migrations. The MCP server mounts to the same FastAPI process via the official `mcp` SDK (pin `>=1.26,<2` — v2 has breaking transport changes). Embeddings default to `sentence-transformers` 5.3.0 (all-MiniLM-L6-v2, local, no API key required) with OpenAI/Anthropic/Ollama as BYOK alternatives. The frontend is React 19 + TypeScript + Vite 8 + Tailwind CSS v4 + shadcn/ui 2.x, managed by `pnpm` 10.x (not v11 — still beta). All versions were live-verified from PyPI/npm/GitHub on 2026-03-22.

**Core technologies:**
- **FastAPI 0.135.1**: ASGI framework + static file serving + OpenAPI — native async, Pydantic v2 native
- **PostgreSQL 16 + pgvector 0.8.2**: Single container for FTS, vector search, AND job queue — eliminates Redis/RabbitMQ
- **SQLAlchemy 2.x + asyncpg 0.31.0**: Async-native ORM; type-safe; required for event-loop-safe DB access
- **mcp SDK 1.26.0** (pin `<2`): Official SDK; stdio + Streamable HTTP transport; FastMCP mounts cleanly to FastAPI
- **sentence-transformers 5.3.0**: Local embeddings, no API key — essential for "usable without keys" requirement
- **React 19 + Vite 8 + shadcn/ui 2.x**: Current stable; shadcn/ui 2.x requires React 19 + Tailwind v4 — do not start on React 18
- **uv 0.10.12 + pnpm 10.32.1**: uv replaces pip/virtualenv/pip-tools; pnpm for strict JS hoisting

**What NOT to use:** `mcp>=2`, pnpm v11 (beta), React 18 for new code, `requests` (use `httpx`), SQLite (no pgvector), `asyncio.run()` inside routes, hardcoded API keys.

See [STACK.md](./STACK.md) for full version compatibility matrix and alternatives considered.

### Expected Features

No competitor combines all of: multi-vendor import, source-span provenance, layered memory, hybrid retrieval, context budgeting, canonical curation, conflict detection, and a local-first BYOK model. This is Recalium's unoccupied position. The cold-start problem (empty system → no value) is the #1 product risk; extraction quality is #2.

**Must have — table stakes (v1 P1):**
- Multi-vendor import (ChatGPT JSON, Claude JSON, generic JSON, paste) — the value prop starts here
- Durable local storage (Docker bind mounts + PostgreSQL) — the trust promise
- Keyword search — users try this first; always available
- Basic web UI (Ingest, Archive, Facts, Search, Settings) — system is a black box without it
- Delete/redact with full cascade — privacy is non-negotiable for target audience
- BYOK configuration (OpenAI, Anthropic, Ollama) — target users have keys; must work day one
- First-run wizard with cold-start import — 30-minutes-to-first-result target
- Backup and restore — "local-first" means users own their data
- MCP `retrieve` tool with context budgeting — primary AI agent consumption surface
- Async processing pipeline (summarization, fact extraction, embeddings, FTS indexing)
- Source span + confidence tier on every extracted fact — the trust differentiator
- Degraded-mode operation (keyword search always available without API keys)

**Should have — differentiators (v1 P2, deferrable under pressure):**
- Canonical memory with explicit user promotion — adds ground truth layer
- Duplicate/overlap detection + review queue — keeps memory clean at scale
- Conflict detection and labeling — surfaces contradictions in retrieval
- MCP `ingest` tool — agent-driven ingestion for power users
- Watched folder import — low-friction ongoing ingestion
- Sensitivity-aware processing (block personal/relationship content from external providers)
- Audit view (90-day access log, client identity, operation metadata)
- Full provenance navigation UI (canonical → facts → raw)
- Processing cost estimation before bulk import

**Defer (v2+):**
- Browser extension ("Recalium Capture") — separate release lifecycle
- Cloud sync / hosted tier — needs encryption design, auth, billing
- Auto-promotion to canonical / temporal decay — needs usage data to tune safely
- Knowledge graph visualization — not on critical path to value
- Multi-user/team support — add when a second tenant exists

See [FEATURES.md](./FEATURES.md) for full competitor analysis and prioritization matrix.

### Architecture Approach

The approved architecture is a two-container modular monolith: `recalium-app` (Python FastAPI process hosting REST API + MCP server + static React SPA + in-process asyncio worker/backup/watcher) and `recalium-postgres` (PostgreSQL 16 with pgvector). All domain modules (`ingest`, `archive`, `derived-memory`, `canonical-memory`, `policy`, `retrieval`, `audit`, `jobs`, `operations`, `portability`) are clean Python sub-packages with explicit interfaces inside a single `backend/app/domain/` tree. Transport layers (`api/`, `mcp/`) are thin adapters that call domain services and contain no business logic. The in-process worker polls the PostgreSQL `jobs` table using `SELECT ... FOR UPDATE SKIP LOCKED`, claimed in a single transaction with the archive write at ingest time.

**Major components:**
1. **`ingest`** — Validate + normalize, persist raw archive, enqueue derivation jobs (atomic); return HTTP 202
2. **`worker/loop.py`** — asyncio task: poll job table → claim batch → dispatch to domain handlers → ack
3. **`derived-memory`** — Summaries, chunks, facts, embeddings, dedup groupings; produced by worker
4. **`retrieval`** — RRF hybrid search (FTS + pgvector, k=60, top-50/mode → top-20); conflict labeling; budget trimming (canonical → facts → summaries → raw)
5. **`canonical-memory`** — User-approved durable entries; source of truth in context budgeting
6. **`policy`** — Sensitivity gate called before every external provider call; allow/deny/review
7. **`audit`** — Append-only event log; provenance read models; 90-day retention

**Key patterns:** Ingest-Acknowledge-Then-Queue (always), SKIP LOCKED job queue (no Redis), RRF + budget trimming (canonical → facts → summaries → raw), modular monolith with deploy-profile seams for future service extraction.

See [ARCHITECTURE.md](./ARCHITECTURE.md) for full data flow diagrams, anti-patterns, and scaling path.

### Critical Pitfalls

1. **Deletion does not actually delete derived data** — Design `source_status` cascade flags into every derived table from day one; implement suppression as DB trigger or transactional stored procedure; add nightly integrity check; write test: delete raw item → assert zero semantic search results. Phase: core schema.

2. **In-process worker blocks the event loop** — Wrap all CPU-bound work (sentence-transformers inference) in `asyncio.to_thread()`; use `httpx.AsyncClient` for all external calls; use `asyncio.Semaphore` to bound worker concurrency; hold strong task references in lifespan context (no fire-and-forget). Phase: async pipeline foundation.

3. **Sensitive content sent to external provider before classification** — Pipeline gate ordering must be enforced architecturally: ingest raw → local sensitivity classification → user declaration check → ONLY THEN dispatch external job. Default to BLOCKED for unclassified content. Phase: processing pipeline.

4. **API keys stored in database or included in backups** — Keys live only in `.env`; DB stores fingerprint/display name only; `pg_dump` must exclude key values; startup assertion scans for key columns. Phase: BYOK configuration.

5. **Docker volume destroyed by `docker compose down -v`** — Use bind mounts (not named volumes) for PostgreSQL data directory; `./data/postgres` and `./backups` on host filesystem; never document or use `-v` flag. Phase: infrastructure setup.

6. **Mixed embedding models after provider switch** — Record `model_name` + `model_dim` per embedding row; surface warning on provider switch; filter semantic search to current model; items with stale embeddings fall back to FTS only until re-embedded. Phase: BYOK + retrieval.

7. **pgvector HNSW index built on empty table or misconfigured** — Build HNSW index after initial data load; set `hnsw.ef_search ≥ 100` for filtered RRF queries; enable `hnsw.iterative_scan = strict_order` (pgvector 0.8.0+); set `shared_buffers = 256MB–1GB` and `maintenance_work_mem = 512MB`. Phase: search/retrieval.

See [PITFALLS.md](./PITFALLS.md) for full pitfall registry, technical debt patterns, and recovery strategies.

---

## Implications for Roadmap

The architecture document already establishes a 5-phase delivery order, validated by feature dependencies and pitfall prevention mapping. The roadmap should follow this structure.

### Phase 1: Foundation
**Rationale:** Everything else depends on durable storage and a working ingest path. No pipeline, no retrieval, no UI completeness needed yet — but schema cascade semantics must be correct from the first migration (Pitfall 1 prevention).
**Delivers:** Docker topology (bind mounts, not named volumes), PostgreSQL + pgvector + FTS setup, Alembic migration baseline with `source_status` cascade flags on all tables, raw archive ingest API, FastAPI skeleton + lifespan + DB pool, React UI shell (left-nav layout + ingest form), audit event persistence for ingest.
**Features addressed:** Durable local storage, multi-vendor import (paste + file), basic web UI shell, BYOK configuration foundation.
**Pitfalls avoided:** Docker volume destruction (bind mounts from day one), deletion orphaning (cascade schema from day one), API keys in DB (pattern established at BYOK phase start).
**Research flag:** Standard patterns — well-documented; no additional research needed.

### Phase 2: Processing Pipeline
**Rationale:** Retrieval is useless without derived memory. The worker loop must be solid and event-loop-safe before retrieval can be meaningful. Sensitivity gate must be architecturally enforced here, not bolted on later (Pitfall 10).
**Delivers:** PostgreSQL LISTEN/NOTIFY + SKIP LOCKED job queue with bounded cleanup, asyncio worker loop with `asyncio.to_thread()` for all inference, per-step job types (summarize / extract-facts / embed / index-fts / dedup), sensitivity gate as pre-flight check before external dispatch, `model_name` + `model_dim` columns on embeddings table, processing pipeline status UI.
**Features addressed:** Async processing pipeline, source span + confidence tier on facts, sensitivity-aware processing (gate only; full UI in Phase 4), degraded-mode (FTS always available).
**Pitfalls avoided:** Event loop starvation (to_thread everywhere), sensitive content leakage (gate before external calls), mixed embedding models (model metadata from day one), unbounded job queue growth (LISTEN/NOTIFY + cleanup).
**Research flag:** Standard patterns — asyncio.to_thread, SKIP LOCKED, sentence-transformers are all well-documented. Sensitivity classification heuristics may need domain-specific tuning; flag for validation.

### Phase 3: Retrieval + Review
**Rationale:** Retrieval depends on Phase 2 derived artifacts. Canonical memory workflows require fact extraction to exist. MCP `retrieve` is the "aha moment" — it must ship complete (RRF + context budgeting + provenance) to validate the core bet.
**Delivers:** Keyword search (FTS), semantic search (pgvector HNSW built after initial data load), hybrid search with RRF (k=60, top-50/mode, top-20 merged), context budget trimming (canonical → facts → summaries → raw), MCP `retrieve` tool with Streamable HTTP transport bound to `127.0.0.1`, canonical memory with explicit user promotion, review queue for duplicate/overlap groupings, conflict detection + labeling in retrieval results, provenance navigation UI.
**Features addressed:** Keyword search, hybrid search (RRF), MCP retrieve with context budgeting, canonical memory + promotion, conflict detection + labeling, duplicate/overlap detection, full provenance navigation UI.
**Pitfalls avoided:** HNSW index on empty table (build post-data-load), MCP DNS rebinding (127.0.0.1 binding + Origin validation), mixed embedding models in retrieval (filter to current model), RRF score drift.
**Research flag:** RRF parameter tuning (k=60, ef_search=100) is specified in architecture; validate empirically with real import data before launch. MCP Streamable HTTP transport is well-documented — standard patterns.

### Phase 4: Privacy + Operations
**Rationale:** Privacy enforcement and operational hardening can be layered on top once core pipeline and retrieval are stable. Deletion cascade UI, backup/restore UI, and sensitivity UI require the underlying mechanisms built in Phases 1–3 to already exist.
**Delivers:** Full deletion cascade UI + verification (with post-deletion backup warning), backup/restore UI (daily schedule, 30-day retention, restore SLA), degraded-mode UI indicators (embedding coverage status, key validation), sensitivity classification UI (approve/block/review queue), first-run wizard (cold-start import + BYOK setup + 30-min-to-value flow), keyboard accessibility audit, audit view (access event list + detail drawer), processing cost estimation.
**Features addressed:** Delete/redact with cascade (UI layer), backup and restore, first-run wizard, degraded-mode indicators, audit view, sensitivity classification UI, BYOK key management UI, cost estimation.
**Pitfalls avoided:** Deletion UX gap (post-deletion backup warning), invalid key silent failure (surface retryable_failed with key re-validation prompt), first-run skip without BYOK clarity.
**Research flag:** Standard patterns — no additional research needed.

### Phase 5: Service Hardening
**Rationale:** Final cleanup for future hosted service extraction. Deploy-profile separation, API/MCP contract hardening, component boundary review, and open memory bundle export. Cannot be done meaningfully before the system is feature-complete.
**Delivers:** Deploy-profile configuration separation (local vs. hosted seams), API contract versioning, MCP protocol version negotiation, open memory bundle JSON export/import, `MCP ingest` tool, watched folder import, `pg_dump`/restore validation suite.
**Features addressed:** Open memory bundle portability, MCP ingest tool, watched folder import.
**Pitfalls avoided:** Provenance chain breaks on edit/promotion (append-only version table verified here), MCP protocol version negotiation.
**Research flag:** Open memory bundle format specification may need iteration based on real export/import cycles — flag for validation.

### Phase Ordering Rationale

- **Storage before pipeline before retrieval** is a hard dependency chain: vectors can't be queried before embeddings exist; embeddings can't exist before the worker runs; the worker can't run before the job queue schema exists; the job queue schema depends on the PostgreSQL container.
- **Cascade semantics in Phase 1** (not Phase 4 where deletion UI ships) prevents the most expensive data integrity pitfall — orphaned derived data is nearly impossible to retroactively fix correctly.
- **Sensitivity gate in Phase 2** (not Phase 4 where sensitivity UI ships) ensures no content ever leaks to an external provider during development or early testing — the gate must be architecturally enforced before any BYOK keys are exercised.
- **MCP binding security (Phase 3)** must be in the same phase as MCP transport is introduced — retrofitting `127.0.0.1` binding and `Origin` validation after deployment is operationally risky.
- **First-run wizard in Phase 4** (not Phase 1) is correct because the wizard requires a working import pipeline, processing queue, and search to demonstrate value — building the wizard before the pipeline is complete wastes the effort.

### Research Flags

Phases needing deeper research during planning:
- **Phase 2** (sensitivity classification): The heuristic rules for personal/relationship content classification are not fully specified in the architecture docs. Needs domain-specific validation against real ChatGPT/Claude export content before the sensitivity gate is finalized.
- **Phase 3** (RRF parameter validation): The k=60, ef_search=100 parameters are specified but not empirically validated. Flag for a recall measurement pass with real import data before launch sign-off.
- **Phase 5** (open memory bundle format): The JSON export/import format is described but not fully specified as a versioned schema. Needs a formal spec before implementation.

Phases with standard patterns (research not needed):
- **Phase 1**: Docker Compose bind mounts, FastAPI skeleton, Alembic, PostgreSQL setup — all well-documented.
- **Phase 4**: Backup/restore with `pg_dump`, first-run wizard UX, keyboard accessibility — standard patterns.

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All versions live-verified from PyPI/npm/GitHub on 2026-03-22; compatibility matrix documented with specific version ranges and breaking change callouts |
| Features | HIGH | Based on live competitor analysis (Mem0 50k stars, basic-memory 2.7k stars, MCP reference memory) plus deep project context (requirements, acceptance criteria, product overview); unoccupied market position clearly identified |
| Architecture | HIGH | Approved, reviewed baseline with extensive documentation across 8+ architecture docs; patterns are well-established (SKIP LOCKED, RRF, modular monolith); specific risks documented with mitigations |
| Pitfalls | HIGH | 10 critical pitfalls with specific detection queries, recovery costs, and prevention phase mapping; verified against official pgvector docs, MCP spec, Docker docs, and project NFRs |

**Overall confidence:** HIGH

### Gaps to Address

- **Sensitivity classification heuristics**: The policy gate exists architecturally but the specific rules for classifying "personal profile", "relationship", and "unknown" content are not defined. Needs a concrete rule set or lightweight classifier before Phase 2 implementation begins. Handle during Phase 2 planning.
- **RRF recall empirical validation**: The k=60, top-50/mode, top-20 parameters are specified but the actual recall quality against real ChatGPT/Claude export data is unvalidated. Flag for measurement during Phase 3 or beta testing.
- **Open memory bundle JSON schema versioning**: Format is described at a high level but needs a formal versioned schema spec (possibly JSON Schema) before Phase 5 export/import is implemented.
- **sentence-transformers model selection**: all-MiniLM-L6-v2 is the default, but dimension count (384) vs. quality trade-offs against larger models have not been benchmarked on the specific content type (AI conversation transcripts). Acceptable for v1 launch; revisit if retrieval quality is poor.

---

## Sources

### Primary (HIGH confidence)
- PyPI live fetch (2026-03-22): FastAPI, Uvicorn, SQLAlchemy, asyncpg, Alembic, Pydantic, httpx, mcp, sentence-transformers, pytest-asyncio — exact versions verified
- npm/GitHub live fetch (2026-03-22): React, Vite, pnpm, Tailwind CSS, shadcn/ui — exact versions verified
- pgvector GitHub changelog (2026-03-22): v0.8.2 confirmed; HNSW parallel build fix; iterative_scan feature in 0.8.0+
- MCP Python SDK GitHub releases (2026-03-22): v1.26.0 stable; v2 development with breaking transport changes on `main`
- MCP Specification — Transports (Streamable HTTP, security warnings): https://modelcontextprotocol.io/docs/concepts/transports
- pgvector README and HNSW docs: https://github.com/pgvector/pgvector
- Docker Volumes documentation: https://docs.docker.com/engine/storage/volumes/
- Mem0/OpenMemory GitHub: https://github.com/mem0ai/mem0 (50.7k stars, competitor analysis)
- basic-memory GitHub: https://github.com/basicmachines-co/basic-memory (2.7k stars, competitor analysis)
- MCP Reference Memory Server: https://github.com/modelcontextprotocol/servers/tree/main/src/memory
- Recalium project docs: `docs/architecture/` (8 docs, reviewed baseline), `docs/requirements/` (nfr.md, assumptions-and-risks.md, product-overview.md, acceptance-criteria.md), `.planning/PROJECT.md`

### Secondary (MEDIUM confidence)
- SQLAlchemy 2.x async patterns — official SQLAlchemy 2.x async docs; well-established patterns
- asyncio event loop blocking patterns — official Python 3.12+ asyncio docs; well-documented limitation
- FastAPI `BackgroundTasks` caveat — official FastAPI docs (2025); confirms in-process workers appropriate when bounded

---
*Research completed: 2026-03-22*
*Ready for roadmap: yes*
