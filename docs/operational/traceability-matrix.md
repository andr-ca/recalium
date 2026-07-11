# Requirements Traceability Matrix

> **Generated** by `scripts/traceability.py` — do not edit by hand. This is the
> single status authority mapping each requirement to the tests that verify it.
> Run `python scripts/traceability.py --check` in CI to fail on untested
> claimed-done requirements.

- Requirements: **52**
- With ≥ 1 referencing test: **50** (96%)
- Verified manually (infra/scope): **2**
- Claimed done (`[x]`) but **no test / no manual note**: **0**

## Manually verified (excluded from the --check gate)

- **BKUP-04** — Durability via Docker bind-mount volumes — verified by a restart/reboot drill, not unit tests.
- **WEBUI-04** — Browser-support scope (Chromium only in v1) — verified manually, not via automated tests.

## Matrix

### BKUP

| ID | Status | Tests | Requirement |
| --- | --- | --- | --- |
| BKUP-01 | ✅ done | `backend/tests/domain/test_backup_service.py`<br>`backend/tests/integration/test_phase4_integration.py` | Scheduled daily backups with 30-day retention |
| BKUP-02 | ✅ done | `backend/tests/domain/test_backup_service.py`<br>`backend/tests/integration/test_phase4_integration.py` | Any successful backup restorable within 15 minutes |
| BKUP-03 | ✅ done | `backend/tests/domain/test_backup_service.py`<br>`backend/tests/integration/test_phase4_integration.py` | Restore recovers raw archive, summaries, facts, canonical memory, provenance metadata, retained audit events, and required configuration |
| BKUP-04 | ✅ done | _manual_ | No acknowledged raw archive item lost after container restart or host reboot (persisted via bind-mount volumes) |

### BYOK

| ID | Status | Tests | Requirement |
| --- | --- | --- | --- |
| BYOK-01 | ✅ done | `backend/tests/integration/test_phase4_integration.py`<br>`frontend/src/pages/WizardPage.tsx` | First-run wizard explains BYOK model, supported providers, estimated cost per 100 conversations, and links to key creation pages |
| BYOK-02 | ✅ done | `backend/tests/test_settings.py` | User can configure OpenAI, Anthropic, and Ollama endpoint API keys through settings |
| BYOK-03 | ✅ done | `backend/tests/test_settings.py` | Key validation runs at configuration time with a lightweight test call (success, failure, or insufficient permissions) |
| BYOK-04 | ✅ done | `backend/tests/test_settings.py` | Provider-backed processing uses only user's configured keys; no calls to any Recalium-operated service |
| BYOK-05 | ✅ done | `backend/tests/test_settings.py` | System remains usable for ingestion, local storage, browsing, and keyword search without any configured keys |
| BYOK-06 | ✅ done | `backend/tests/integration/test_phase4_integration.py`<br>`frontend/src/pages/WizardPage.tsx` | Processing cost estimated and displayed before bulk import confirmation (token count heuristics, order-of-magnitude correctness) |
| BYOK-07 | ✅ done | `backend/tests/domain/test_jobs_service.py`<br>`backend/tests/worker/test_dispatcher.py` | Invalid/rate-limited keys cause affected jobs to enter retryable failed state with clear error; no silent drops |
| BYOK-08 | ✅ done | `backend/tests/domain/test_derived_memory.py`<br>`backend/tests/worker/test_dispatcher.py` | User can switch providers per function without reprocessing already-completed items |

### CANM

| ID | Status | Tests | Requirement |
| --- | --- | --- | --- |
| CANM-01 | ✅ done | `backend/tests/api/test_canonical_api.py`<br>`backend/tests/domain/test_canonical_memory.py`<br>`backend/tests/integration/test_phase3_integration.py` | User can inspect provenance, edit, delete, mark disputed/stale, and promote facts to canonical memory |
| CANM-02 | ✅ done | `backend/tests/domain/test_canonical_memory.py`<br>`backend/tests/integration/test_phase3_integration.py` | Canonical memory is prioritized over extracted memory in retrieval; conflicting extracted memory returned as lower-ranked evidence with explicit conflict labeling |
| CANM-03 | ✅ done | `backend/tests/api/test_canonical_api.py`<br>`backend/tests/domain/test_canonical_memory.py`<br>`backend/tests/integration/test_phase3_integration.py` | Canonical memory requires explicit user action (no auto-promotion) |
| CANM-04 | ✅ done | `backend/tests/api/test_canonical_api.py`<br>`backend/tests/domain/test_canonical_memory.py`<br>`backend/tests/integration/test_phase3_integration.py` | Facts with no attributable source span cannot be promoted without explicit user confirmation |
| CANM-05 | ✅ done | `backend/tests/domain/test_review_queue.py`<br>`backend/tests/integration/test_phase3_integration.py` | Review queue groups duplicate/overlapping facts for manageable cleanup |
| CANM-06 | ✅ done | `backend/tests/domain/test_conflict_detection.py` | Conflict detection flags contradictory facts across sources |

### INGT

| ID | Status | Tests | Requirement |
| --- | --- | --- | --- |
| INGT-01 | ✅ done | `backend/tests/test_ingest.py` | User can import conversations via text paste (plain text / Markdown) |
| INGT-02 | ✅ done | `backend/tests/test_ingest.py` | User can import conversations via file upload (ChatGPT JSON, Claude JSON, generic JSON) |
| INGT-03 | ✅ done | `backend/tests/test_archive.py`<br>`backend/tests/test_ingest.py` | System stores raw archive with source metadata and shows item in Archive UI within P95 ≤ 1s |
| INGT-04 | ✅ done | `backend/tests/integration/test_phase5_integration.py` | Watched import folder provides low-friction local ingestion without UI interaction |
| INGT-05 | ✅ done | `backend/tests/integration/test_phase5_integration.py` | MCP-accessible ingestion endpoint accepts raw content with source metadata, client identity, and sensitivity hints |

### MCP

| ID | Status | Tests | Requirement |
| --- | --- | --- | --- |
| MCP-01 | ✅ done | `backend/tests/api/test_search_api.py`<br>`backend/tests/domain/test_retrieval.py`<br>`backend/tests/integration/test_phase3_integration.py`<br>`backend/tests/mcp/test_mcp_server.py` | MCP `retrieve` tool returns items with source links, type, rank score, provenance metadata, conflict labels, budget/trimming reason, and retrieval-mode metadata |
| MCP-02 | ✅ done | `backend/tests/integration/test_phase5_integration.py`<br>`backend/tests/mcp/test_mcp_server.py` | MCP ingest endpoint accepts well-formed requests; rejects missing required fields with descriptive error |
| MCP-03 | ✅ done | `backend/tests/api/test_search_api.py`<br>`backend/tests/domain/test_retrieval.py`<br>`backend/tests/integration/test_phase3_integration.py`<br>`backend/tests/mcp/test_mcp_server.py` | Every MCP access event is recorded with client identity, timestamp, and operation metadata |
| MCP-04 | ✅ done | `backend/tests/api/test_search_api.py`<br>`backend/tests/integration/test_phase3_integration.py`<br>`backend/tests/mcp/test_mcp_server.py` | Access-event history retained for at least 90 days |

### PIPE

| ID | Status | Tests | Requirement |
| --- | --- | --- | --- |
| PIPE-01 | ✅ done | `backend/tests/domain/test_derived_memory.py`<br>`backend/tests/worker/test_loop.py` | Async pipeline produces summaries, extracted facts, embeddings, and FTS index entries without blocking ingest response |
| PIPE-02 | ✅ done | `backend/tests/domain/test_derived_memory.py`<br>`evals/checks/eval_extraction.py` | Every extracted fact carries source span, confidence tier (high/medium/low), derivation method, and model version |
| PIPE-03 | ✅ done | `backend/tests/domain/test_policy_gate.py` | Sensitivity gate runs before any external provider call; personal/relationship/unclassified content blocked from external processing by default |
| PIPE-04 | ✅ done | `backend/tests/domain/test_jobs_service.py`<br>`backend/tests/worker/test_loop.py` | Failed jobs retry automatically with bounded attempts; terminal failures surface for manual retry |
| PIPE-05 | ✅ done | `backend/tests/api/test_reprocess.py`<br>`backend/tests/domain/test_jobs_service.py` | Reprocessing supported after logic changes or failures |

### PORT

| ID | Status | Tests | Requirement |
| --- | --- | --- | --- |
| PORT-01 | ✅ done | `backend/tests/integration/test_phase5_integration.py` | JSON export/import via open memory bundle format (v1 spec); re-importable without bespoke conversion |
| PORT-02 | ✅ done | `backend/tests/domain/test_telemetry_service.py`<br>`backend/tests/integration/test_phase4_integration.py` | Local usage telemetry (searches/day, retrievals/day, facts reviewed, canonical items created, MCP vs UI retrievals) visible in Settings; never leaves local system |

### PRIV

| ID | Status | Tests | Requirement |
| --- | --- | --- | --- |
| PRIV-01 | ✅ done | `backend/tests/api/test_archive_delete.py`<br>`backend/tests/domain/test_deletion_cascade.py`<br>`backend/tests/integration/test_phase4_integration.py` | Raw source deletion/redaction immediately cascade-suppresses derived summaries, facts, embeddings, and search entries (marked source-removed) |
| PRIV-02 | ✅ done | `backend/tests/domain/test_deletion_cascade.py`<br>`backend/tests/integration/test_phase4_integration.py` | Canonical memory from deleted source retains source-removed marker and required-review state |
| PRIV-03 | ✅ done | `backend/tests/domain/test_backup_service.py`<br>`backend/tests/integration/test_phase4_integration.py`<br>`backend/tests/integration/test_phase5_integration.py` | Future backups/exports exclude deleted/redacted data; UI flags older backups that may contain it |
| PRIV-04 | ✅ done | `backend/tests/domain/test_policy_gate.py` | Personal profile and relationship content blocked from external processing by default |
| PRIV-05 | ✅ done | `backend/tests/domain/test_policy_gate.py` | Unknown/unclassified content blocked from external processing by default until user explicitly allows |
| PRIV-06 | ✅ done | `backend/tests/api/test_auth_middleware.py`<br>`backend/tests/integration/test_phase4_integration.py` | Broader-than-localhost exposure requires authentication, session handling, and transport protection |

### SRCH

| ID | Status | Tests | Requirement |
| --- | --- | --- | --- |
| SRCH-01 | ✅ done | `backend/tests/api/test_search_api.py`<br>`backend/tests/domain/test_retrieval.py`<br>`backend/tests/integration/test_phase3_integration.py` | Keyword search available via PostgreSQL FTS |
| SRCH-02 | ✅ done | `backend/tests/domain/test_retrieval.py`<br>`backend/tests/integration/test_phase3_integration.py` | Semantic search available via pgvector (when embeddings exist) |
| SRCH-03 | ✅ done | `backend/tests/api/test_search_api.py`<br>`backend/tests/domain/test_retrieval.py`<br>`backend/tests/integration/test_phase3_integration.py` | Hybrid retrieval via Reciprocal Rank Fusion (RRF, k=60, top-50 candidates per mode, top-20 merged) |
| SRCH-04 | ✅ done | `backend/tests/domain/test_retrieval.py`<br>`backend/tests/integration/test_phase3_integration.py` | Retrieval with context budgeting: strict priority trimming (canonical → facts → summaries → raw excerpts) |
| SRCH-05 | ✅ done | `backend/tests/api/test_search_api.py`<br>`backend/tests/integration/test_phase3_integration.py` | Search and retrieval meet P95 ≤ 2s on datasets up to 100k stored items |
| SRCH-06 | ✅ done | `backend/tests/domain/test_retrieval.py`<br>`backend/tests/integration/test_phase3_integration.py` | Degraded mode: keyword search + cached semantic results available when embeddings or provider unavailable |

### WEBUI

| ID | Status | Tests | Requirement |
| --- | --- | --- | --- |
| WEBUI-01 | ✅ done | `backend/tests/test_archive.py`<br>`frontend/src/tests/LeftNav.test.tsx` | Left-nav layout: Ingest, Archive, Facts, Canonical, Search, Review Queue, Audit, Settings |
| WEBUI-02 | ✅ done | `backend/tests/integration/test_phase4_integration.py` | Core workflows operable by keyboard only (ingest, search, fact review, canonical edit, review queue, restore) |
| WEBUI-03 | ✅ done | `backend/tests/integration/test_phase4_integration.py` | No critical accessibility failures (missing labels, keyboard traps, unannounced state changes) |
| WEBUI-04 | ✅ done | _manual_ | Chrome/Chromium only in v1 |
| WEBUI-05 | ✅ done | `backend/tests/domain/test_canonical_memory.py`<br>`backend/tests/integration/test_phase3_integration.py` | Provenance navigable from any summary, fact, or canonical item |
| WEBUI-06 | ✅ done | `backend/tests/integration/test_phase4_integration.py` | Audit view: basic event list with per-event detail drawer; more detailed logging configurable |
