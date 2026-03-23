# Requirements: Recalium

**Defined:** 2026-03-22
**Core Value:** A user's future AI session — on any tool, with any model — can retrieve relevant, source-backed context from prior conversations that happened anywhere, without re-explaining anything.

## v1 Requirements

Requirements for initial release. Each maps to exactly one roadmap phase.

### Ingestion

- [x] **INGT-01**: User can import conversations via text paste (plain text / Markdown)
- [x] **INGT-02**: User can import conversations via file upload (ChatGPT JSON, Claude JSON, generic JSON)
- [x] **INGT-03**: System stores raw archive with source metadata and shows item in Archive UI within P95 ≤ 1s
- [ ] **INGT-04**: Watched import folder provides low-friction local ingestion without UI interaction
- [ ] **INGT-05**: MCP-accessible ingestion endpoint accepts raw content with source metadata, client identity, and sensitivity hints

### Processing Pipeline

- [x] **PIPE-01**: Async pipeline produces summaries, extracted facts, embeddings, and FTS index entries without blocking ingest response
- [x] **PIPE-02**: Every extracted fact carries source span, confidence tier (high/medium/low), derivation method, and model version
- [x] **PIPE-03**: Sensitivity gate runs before any external provider call; personal/relationship/unclassified content blocked from external processing by default
- [x] **PIPE-04**: Failed jobs retry automatically with bounded attempts; terminal failures surface for manual retry
- [ ] **PIPE-05**: Reprocessing supported after logic changes or failures

### Search and Retrieval

- [ ] **SRCH-01**: Keyword search available via PostgreSQL FTS
- [ ] **SRCH-02**: Semantic search available via pgvector (when embeddings exist)
- [ ] **SRCH-03**: Hybrid retrieval via Reciprocal Rank Fusion (RRF, k=60, top-50 candidates per mode, top-20 merged)
- [ ] **SRCH-04**: Retrieval with context budgeting: strict priority trimming (canonical → facts → summaries → raw excerpts)
- [ ] **SRCH-05**: Search and retrieval meet P95 ≤ 2s on datasets up to 100k stored items
- [ ] **SRCH-06**: Degraded mode: keyword search + cached semantic results available when embeddings or provider unavailable

### MCP Interface

- [ ] **MCP-01**: MCP `retrieve` tool returns items with source links, type, rank score, provenance metadata, conflict labels, budget/trimming reason, and retrieval-mode metadata
- [ ] **MCP-02**: MCP ingest endpoint accepts well-formed requests; rejects missing required fields with descriptive error
- [ ] **MCP-03**: Every MCP access event is recorded with client identity, timestamp, and operation metadata
- [ ] **MCP-04**: Access-event history retained for at least 90 days

### Canonical Memory and Review

- [ ] **CANM-01**: User can inspect provenance, edit, delete, mark disputed/stale, and promote facts to canonical memory
- [ ] **CANM-02**: Canonical memory is prioritized over extracted memory in retrieval; conflicting extracted memory returned as lower-ranked evidence with explicit conflict labeling
- [ ] **CANM-03**: Canonical memory requires explicit user action (no auto-promotion)
- [ ] **CANM-04**: Facts with no attributable source span cannot be promoted without explicit user confirmation
- [ ] **CANM-05**: Review queue groups duplicate/overlapping facts for manageable cleanup
- [x] **CANM-06**: Conflict detection flags contradictory facts across sources

### Deletion and Privacy

- [ ] **PRIV-01**: Raw source deletion/redaction immediately cascade-suppresses derived summaries, facts, embeddings, and search entries (marked source-removed)
- [ ] **PRIV-02**: Canonical memory from deleted source retains source-removed marker and required-review state
- [ ] **PRIV-03**: Future backups/exports exclude deleted/redacted data; UI flags older backups that may contain it
- [x] **PRIV-04**: Personal profile and relationship content blocked from external processing by default
- [x] **PRIV-05**: Unknown/unclassified content blocked from external processing by default until user explicitly allows
- [ ] **PRIV-06**: Broader-than-localhost exposure requires authentication, session handling, and transport protection

### BYOK Provider Configuration

- [ ] **BYOK-01**: First-run wizard explains BYOK model, supported providers, estimated cost per 100 conversations, and links to key creation pages
- [x] **BYOK-02**: User can configure OpenAI, Anthropic, and Ollama endpoint API keys through settings
- [x] **BYOK-03**: Key validation runs at configuration time with a lightweight test call (success, failure, or insufficient permissions)
- [x] **BYOK-04**: Provider-backed processing uses only user's configured keys; no calls to any Recalium-operated service
- [x] **BYOK-05**: System remains usable for ingestion, local storage, browsing, and keyword search without any configured keys
- [ ] **BYOK-06**: Processing cost estimated and displayed before bulk import confirmation (token count heuristics, order-of-magnitude correctness)
- [ ] **BYOK-07**: Invalid/rate-limited keys cause affected jobs to enter retryable failed state with clear error; no silent drops
- [ ] **BYOK-08**: User can switch providers per function without reprocessing already-completed items

### Backup and Restore

- [ ] **BKUP-01**: Scheduled daily backups with 30-day retention
- [ ] **BKUP-02**: Any successful backup restorable within 15 minutes
- [ ] **BKUP-03**: Restore recovers raw archive, summaries, facts, canonical memory, provenance metadata, retained audit events, and required configuration
- [x] **BKUP-04**: No acknowledged raw archive item lost after container restart or host reboot (persisted via bind-mount volumes)

### Web UI

- [x] **WEBUI-01**: Left-nav layout: Ingest, Archive, Facts, Canonical, Search, Review Queue, Audit, Settings
- [ ] **WEBUI-02**: Core workflows operable by keyboard only (ingest, search, fact review, canonical edit, review queue, restore)
- [ ] **WEBUI-03**: No critical accessibility failures (missing labels, keyboard traps, unannounced state changes)
- [x] **WEBUI-04**: Chrome/Chromium only in v1
- [ ] **WEBUI-05**: Provenance navigable from any summary, fact, or canonical item
- [ ] **WEBUI-06**: Audit view: basic event list with per-event detail drawer; more detailed logging configurable

### Portability

- [ ] **PORT-01**: JSON export/import via open memory bundle format (v1 spec); re-importable without bespoke conversion
- [ ] **PORT-02**: Local usage telemetry (searches/day, retrievals/day, facts reviewed, canonical items created, MCP vs UI retrievals) visible in Settings; never leaves local system

## v2 Requirements

Deferred to future releases. Tracked but not in current roadmap.

### Browser Extension

- **BEXT-01**: Browser extension ("Recalium Capture") for passive conversation capture
- **BEXT-02**: Automatic capture without manual export/import steps

### Intelligence and Automation

- **INTL-01**: Temporal decay and relevance weighting for older memories
- **INTL-02**: Confidence-based auto-curation for high-confidence extracted facts
- **INTL-03**: Advanced automatic conflict resolution

### Multi-User and Sync

- **MUSR-01**: Multi-user support with tenant-aware data model
- **MUSR-02**: Cloud sync (post-v1 hosted sync tier)
- **MUSR-03**: Per-agent permission controls beyond single-user scope

### Visualization

- **VIZ-01**: Knowledge graph visualization of memory relationships

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Browser extension | v2; separate release lifecycle and Chrome CSP complexity |
| Temporal decay / relevance weighting | v2; requires real usage data to tune |
| Confidence-based auto-curation | v2; depends on extraction quality data from real use |
| Multi-user support | v2; add when a second tenant exists |
| Cloud sync | post-v1 hosted sync tier; requires encryption design, auth, billing |
| Tenant-aware data model seams | premature for v1; add when a second tenant exists |
| Advanced per-agent permissions | beyond v1 scope |
| Knowledge graph visualization | beyond v1; not on critical path to value |
| Advanced automatic conflict resolution | beyond v1 |
| Markdown-plus-assets export | could have; lower priority than core pipeline |
| Managed processing tier backend | add shortly after v1 |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| INGT-01 | Phase 1 — Foundation | Complete |
| INGT-02 | Phase 1 — Foundation | Complete |
| INGT-03 | Phase 1 — Foundation | Complete |
| INGT-04 | Phase 5 — Service Hardening | Pending |
| INGT-05 | Phase 5 — Service Hardening | Pending |
| PIPE-01 | Phase 2 — Processing Pipeline | Complete |
| PIPE-02 | Phase 2 — Processing Pipeline | Complete |
| PIPE-03 | Phase 2 — Processing Pipeline | Complete |
| PIPE-04 | Phase 2 — Processing Pipeline | Complete |
| PIPE-05 | Phase 2 — Processing Pipeline | Pending |
| SRCH-01 | Phase 3 — Retrieval + Review | Pending |
| SRCH-02 | Phase 3 — Retrieval + Review | Pending |
| SRCH-03 | Phase 3 — Retrieval + Review | Pending |
| SRCH-04 | Phase 3 — Retrieval + Review | Pending |
| SRCH-05 | Phase 3 — Retrieval + Review | Pending |
| SRCH-06 | Phase 3 — Retrieval + Review | Pending |
| MCP-01 | Phase 3 — Retrieval + Review | Pending |
| MCP-02 | Phase 5 — Service Hardening | Pending |
| MCP-03 | Phase 3 — Retrieval + Review | Pending |
| MCP-04 | Phase 3 — Retrieval + Review | Pending |
| CANM-01 | Phase 3 — Retrieval + Review | Pending |
| CANM-02 | Phase 3 — Retrieval + Review | Pending |
| CANM-03 | Phase 3 — Retrieval + Review | Pending |
| CANM-04 | Phase 3 — Retrieval + Review | Pending |
| CANM-05 | Phase 3 — Retrieval + Review | Pending |
| CANM-06 | Phase 2 — Processing Pipeline | Complete |
| PRIV-01 | Phase 4 — Privacy + Operations | Pending |
| PRIV-02 | Phase 4 — Privacy + Operations | Pending |
| PRIV-03 | Phase 4 — Privacy + Operations | Pending |
| PRIV-04 | Phase 2 — Processing Pipeline | Complete |
| PRIV-05 | Phase 2 — Processing Pipeline | Complete |
| PRIV-06 | Phase 4 — Privacy + Operations | Pending |
| BYOK-01 | Phase 4 — Privacy + Operations | Pending |
| BYOK-02 | Phase 1 — Foundation | Complete |
| BYOK-03 | Phase 1 — Foundation | Complete |
| BYOK-04 | Phase 1 — Foundation | Complete |
| BYOK-05 | Phase 1 — Foundation | Complete |
| BYOK-06 | Phase 4 — Privacy + Operations | Pending |
| BYOK-07 | Phase 2 — Processing Pipeline | Pending |
| BYOK-08 | Phase 2 — Processing Pipeline | Pending |
| BKUP-01 | Phase 4 — Privacy + Operations | Pending |
| BKUP-02 | Phase 4 — Privacy + Operations | Pending |
| BKUP-03 | Phase 4 — Privacy + Operations | Pending |
| BKUP-04 | Phase 1 — Foundation | Complete |
| WEBUI-01 | Phase 1 — Foundation | Complete |
| WEBUI-02 | Phase 4 — Privacy + Operations | Pending |
| WEBUI-03 | Phase 4 — Privacy + Operations | Pending |
| WEBUI-04 | Phase 1 — Foundation | Complete |
| WEBUI-05 | Phase 3 — Retrieval + Review | Pending |
| WEBUI-06 | Phase 4 — Privacy + Operations | Pending |
| PORT-01 | Phase 5 — Service Hardening | Pending |
| PORT-02 | Phase 4 — Privacy + Operations | Pending |

**Coverage:**
- v1 requirements: 52 total
- Mapped to phases: 52
- Unmapped: 0 ✓

### Changes from Initial Draft

| Requirement | Initial Draft | Final Assignment | Reason |
|-------------|--------------|-----------------|--------|
| CANM-06 | Phase 3 | Phase 2 | Conflict detection is a pipeline output (dedup/overlap groupings materialized by worker); canonical memory workflows that *consume* conflict data remain in Phase 3 |

---
*Requirements defined: 2026-03-22*
*Last updated: 2026-03-22 after roadmap finalization (CANM-06 moved Phase 3 → Phase 2)*
