# Roadmap: Recalium

**Project:** Recalium — Local-First MCP-Native Personal Memory Platform
**Core Value:** A user's future AI session can retrieve relevant, source-backed context from prior conversations, without re-explaining anything.
**Created:** 2026-03-22
**Granularity:** Fine (5 phases, 5–10 plans each)
**Coverage:** 52/52 v1 requirements mapped ✓

---

## Phases

- [x] **Phase 1: Foundation** — Durable local storage, raw ingest, BYOK key storage pattern, web UI shell (completed 2026-03-23)
- [x] **Phase 2: Processing Pipeline** — Async derived-memory worker, fact extraction, sensitivity gate, dedup materialization (completed 2026-03-23)
- [x] **Phase 3: Retrieval + Review** — Hybrid search, MCP retrieve, canonical memory workflows, review queue (completed 2026-03-23)
- [x] **Phase 4: Privacy + Operations** — Deletion cascade UI, backup/restore, first-run wizard, accessibility, audit view (completed 2026-03-23)
- [ ] **Phase 5: Service Hardening** — MCP ingest, watched folder, portability bundle, API/MCP contract hardening

---

## Phase Details

### Phase 1: Foundation

**Goal:** Users can ingest conversations from any supported source and find them in the archive immediately, with confidence that their data survives container restarts and that API keys are never written to the database.

**Depends on:** Nothing (first phase)

**Requirements:** INGT-01, INGT-02, INGT-03, BKUP-04, WEBUI-01, WEBUI-04, BYOK-02, BYOK-03, BYOK-04, BYOK-05

**Success Criteria** (what must be TRUE when this phase completes):
1. User pastes plain text or Markdown into the Ingest page and the item appears in Archive within 1 second (P95).
2. User uploads a ChatGPT JSON, Claude JSON, or generic JSON export and each conversation appears as a distinct archive entry within 1 second (P95).
3. User restarts or reboots the Docker host and every previously acknowledged archive item is still present (bind-mount volumes, not named volumes).
4. User opens Settings, enters an OpenAI/Anthropic/Ollama API key, and the system validates it with a lightweight test call — reporting success, failure, or insufficient permissions — without storing the key in the database.
5. System is fully usable for ingestion, archive browsing, and keyword search when no API keys are configured (degraded mode is transparent, not a blocker).

**Plans:** 1/8 plans complete

---

### Phase 2: Processing Pipeline

**Goal:** Every ingested conversation is asynchronously transformed into summaries, extracted facts (with source spans, confidence tiers, model provenance), embeddings, and FTS entries — without blocking ingest — and no content ever reaches an external provider before the sensitivity gate approves it.

**Depends on:** Phase 1

**Requirements:** PIPE-01, PIPE-02, PIPE-03, PIPE-04, PIPE-05, PRIV-04, PRIV-05, BYOK-07, BYOK-08, CANM-06

**Success Criteria** (what must be TRUE when this phase completes):
1. After a conversation is ingested, the Archive UI shows processing progress; within a reasonable window the item has a summary, extracted facts, and embedding — all without blocking the ingest HTTP response.
2. Every extracted fact displays its source span (the verbatim text it was derived from), a confidence tier (high/medium/low), the derivation method, and the model + version that produced it.
3. Personal profile, relationship, or unclassified content is blocked from any external provider call by default; the sensitivity gate fires before any BYOK key is used — verified by importing a conversation containing personal information with a BYOK key configured.
4. When an API key is invalid or rate-limited, affected jobs enter a retryable failed state with a clear per-job error message — no silent drops; the user can manually retry.
5. User can switch providers per function (e.g., change the summarization provider) without triggering reprocessing of already-completed items; items with stale embeddings fall back to FTS only.
6. Conflict detection flags contradictory facts across sources and exposes them in the Facts view for review.

**Plans:** 8/8 plans complete

---

### Phase 3: Retrieval + Review

**Goal:** Users and MCP clients can retrieve the most relevant, source-backed memory from the archive using keyword, semantic, or hybrid search — with context budgeting, provenance navigation, and the ability to promote trusted facts to canonical memory that takes priority in all future retrieval.

**Depends on:** Phase 2

**Requirements:** SRCH-01, SRCH-02, SRCH-03, SRCH-04, SRCH-05, SRCH-06, MCP-01, MCP-03, MCP-04, CANM-01, CANM-02, CANM-03, CANM-04, CANM-05, WEBUI-05

**Success Criteria** (what must be TRUE when this phase completes):
1. A keyword search returns relevant results from the PostgreSQL FTS index; a semantic search returns ranked results from pgvector; both complete within 2 seconds (P95) on a dataset of up to 100k stored items.
2. Hybrid search (RRF, k=60, top-50 candidates per mode, top-20 merged) returns a merged ranked list; when embeddings are unavailable, the system falls back to keyword search + cached semantic results transparently.
3. An MCP client calling the `retrieve` tool receives items with source links, type, rank score, provenance metadata, conflict labels, context-budget trimming reason, and retrieval-mode metadata.
4. Every MCP access event (retrieve operation) is recorded with client identity, timestamp, and operation metadata; records are retained for at least 90 days.
5. User can inspect any fact's provenance chain (fact → summary → raw archive → original conversation), promote it to canonical memory with explicit confirmation, mark it disputed/stale, edit it, or delete it.
6. Canonical memory items are ranked above extracted facts in retrieval results; conflicting extracted facts appear as lower-ranked evidence with explicit conflict labels.

**Plans:** 8/8 plans complete

Plans:
- [x] 03-01-PLAN.md — Migration 0003 + ORM models (canonical_memory, review_queue_items)
- [x] 03-02-PLAN.md — Test scaffold RED (5 test files: retrieval, canonical, review_queue, mcp, api_routes)
- [x] 03-03-PLAN.md — Core retrieval service (keyword/semantic/hybrid/RRF/budget/cache/audit)
- [x] 03-04-PLAN.md — Canonical memory service + review queue service (CANM-01–05)
- [x] 03-05-PLAN.md — MCP server (retrieve tool, AuditEvent emission, 127.0.0.1 binding)
- [x] 03-06-PLAN.md — API routes (search, retrieve, canonical CRUD, review queue, audit)
- [x] 03-07-PLAN.md — Frontend pages (Search, Facts, Canonical, ReviewQueue, Audit, ProvenanceSidePanel)
- [x] 03-08-PLAN.md — Integration test suite GREEN (all 15 requirement IDs covered)

---

### Phase 4: Privacy + Operations

**Goal:** Users have full, auditable control over their data — they can delete or redact any source conversation and watch derived data disappear from search immediately; they can restore from backup in under 15 minutes; and the system is keyboard-accessible and has a first-run wizard that takes a new user from empty system to first meaningful search result within 30 minutes.

**Depends on:** Phase 3

**Requirements:** PRIV-01, PRIV-02, PRIV-03, PRIV-06, BYOK-01, BYOK-06, BKUP-01, BKUP-02, BKUP-03, WEBUI-02, WEBUI-03, WEBUI-06, PORT-02

**Success Criteria** (what must be TRUE when this phase completes):
1. User deletes or redacts a raw archive entry; derived summaries, facts, embeddings, and search entries are immediately suppressed (marked `source-removed`); any promoted canonical memory retains a `source-removed` / `required-review` marker — verified by confirming those items no longer appear in semantic or keyword search.
2. User can restore the system from any retained daily backup within 15 minutes; the restored state includes raw archive, summaries, facts, canonical memory, provenance metadata, audit events, and required configuration; the restore UI warns when a selected backup predates a deletion event.
3. A new user completes the first-run wizard (BYOK setup + first conversation import + first search) within 30 minutes; the wizard explains the BYOK model, estimated cost per 100 conversations, and links to provider key creation pages; cost estimation is shown before bulk import.
4. All core workflows (ingest, search, fact review, canonical edit, review queue, restore) are operable by keyboard only with no critical accessibility failures (no missing labels, keyboard traps, or unannounced state changes).
5. Audit view shows a paginated access-event list with per-event detail drawer; more detailed logging is configurable; local telemetry (searches/day, retrievals/day, facts reviewed, canonical items created, MCP vs UI retrievals) is visible in Settings and never leaves the local system.

**Plans:** 8/8 plans complete

Plans:
- [x] 04-01-PLAN.md — Deletion cascade service + auth middleware (PRIV-01, PRIV-02, PRIV-06)
- [x] 04-02-PLAN.md — Test scaffold RED (6 test files: cascade, archive DELETE, auth, backup, telemetry, integration)
- [x] 04-03-PLAN.md — Backup/restore service + telemetry + migration 0004
- [x] 04-04-PLAN.md — Archive deletion UI (delete button + confirmation + show-deleted toggle)
- [x] 04-05-PLAN.md — First-run wizard + cost estimation (BYOK-01, BYOK-06)
- [x] 04-06-PLAN.md — Audit improvements (event_type filter, detail drawer) + telemetry UI in Settings
- [x] 04-07-PLAN.md — Accessibility audit + keyboard navigation fixes (WEBUI-02, WEBUI-03)
- [x] 04-08-PLAN.md — Phase 4 integration test suite GREEN

---

### Phase 5: Service Hardening

**Goal:** The system is portable, contract-stable, and ready for future service extraction — users can export and re-import their full memory bundle, MCP clients can ingest via the server directly, the watched folder enables frictionless ongoing ingestion, and all module boundaries are reviewed for deploy-profile separation.

**Depends on:** Phase 4

**Requirements:** INGT-04, INGT-05, MCP-02, PORT-01

**Success Criteria** (what must be TRUE when this phase completes):
1. User places a conversation file in the configured watched import folder; it is ingested automatically within a reasonable polling window without any UI interaction.
2. An MCP client calls the `ingest` tool with a well-formed request and the content is accepted and queued for processing; a request missing required fields receives a descriptive error response.
3. User exports their full memory archive as a JSON bundle (open memory bundle format v1) and successfully re-imports it into a fresh Recalium instance without bespoke conversion tools.
4. All module boundaries have been reviewed for deploy-profile separation (local vs. hosted seams); API and MCP contracts are versioned; the system can be described as ready for future service extraction.

**Plans:** TBD

---

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 0/TBD | Complete    | 2026-03-23 |
| 2. Processing Pipeline | 8/8 | Complete | 2026-03-23 |
| 3. Retrieval + Review | 8/8 | Complete | 2026-03-23 |
| 4. Privacy + Operations | 8/8 | Complete | 2026-03-23 |
| 5. Service Hardening | 0/TBD | Not started | — |

---

## Coverage Map

| Phase | Requirements |
|-------|-------------|
| 1 — Foundation | INGT-01, INGT-02, INGT-03, BKUP-04, WEBUI-01, WEBUI-04, BYOK-02, BYOK-03, BYOK-04, BYOK-05 |
| 2 — Processing Pipeline | PIPE-01, PIPE-02, PIPE-03, PIPE-04, PIPE-05, PRIV-04, PRIV-05, BYOK-07, BYOK-08, CANM-06 |
| 3 — Retrieval + Review | SRCH-01, SRCH-02, SRCH-03, SRCH-04, SRCH-05, SRCH-06, MCP-01, MCP-03, MCP-04, CANM-01, CANM-02, CANM-03, CANM-04, CANM-05, WEBUI-05 |
| 4 — Privacy + Operations | PRIV-01, PRIV-02, PRIV-03, PRIV-06, BYOK-01, BYOK-06, BKUP-01, BKUP-02, BKUP-03, WEBUI-02, WEBUI-03, WEBUI-06, PORT-02 |
| 5 — Service Hardening | INGT-04, INGT-05, MCP-02, PORT-01 |

**Total mapped:** 52/52 ✓

---

## Research Flags (carry forward to planning)

| Phase | Flag | Notes |
|-------|------|-------|
| Phase 2 | Sensitivity classification heuristics | Rules for personal/relationship/unclassified content not fully specified; needs domain validation against real ChatGPT/Claude export content before Phase 2 plan is finalized |
| Phase 3 | RRF recall empirical validation | k=60, ef_search=100 parameters specified but not empirically validated against real export data; flag for measurement pass |
| Phase 5 | Open memory bundle JSON schema versioning | Format described at high level; needs formal versioned schema spec before implementation |

---

*Roadmap created: 2026-03-22*
*Last updated: 2026-03-23 after completing Phase 4 (all 8 plans executed, 172 tests passing, 13 Phase 4 reqs verified)*
