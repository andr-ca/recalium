# Non-Functional Requirements

## Status
This file captures the current NFR baseline for review.

## Privacy and data control
### Requirements
- Storage must default to local-first operation.
- The storage location must be user-visible.
- The system must not share data with third parties implicitly.
- UI, API, and MCP endpoints must bind to localhost by default unless the user explicitly opts into broader network exposure.
- If the user opts into broader network exposure, the exposed interface must require authentication, session handling, and transport protection appropriate to that interface.
- Export and deletion must be user-accessible.
- Redaction workflows must be supported.
- The system should support excluding selected categories or sources from indexing or embedding where configured.
- Any external provider usage for summarization, embedding, or related processing must be explicit and opt-in.
- v1 may depend on external providers for summarization, extraction, or embeddings, but that provider usage must remain visible and user-controlled.
- Personal profile and relationships are sensitive categories by default in v1.
- Sensitive categories must be blocked from external processing by default unless the user explicitly overrides that protection.
- Sensitive content must be identified before any external processing by combining user-declared sensitivity with local rule-based pre-classification using metadata and local detection rules.
- Content that is unknown or not confidently classified must be blocked from external processing by default until the user explicitly allows it.
- When a raw source item is deleted or redacted, derived summaries, facts, embeddings, and search visibility must be immediately cascade-suppressed and marked as source-removed.
- Future backups and exports must exclude deleted or redacted data, and the system must warn users that previously created backups or exports may still contain that data.

## Reliability
### Requirements
- Raw archive writes must succeed independently of downstream processing.
- Ingested content must not be silently lost.
- Pipeline failures must not destroy raw input.
- Failed items must remain visible with retry support.
- Reprocessing must be supported after logic improvements or failures.
- If external providers are unavailable, the system must continue to support local storage, keyword search, and any implemented basic local processing features.
- No acknowledged raw archive item may be lost after a container restart or host reboot, assuming persisted Docker volumes remain intact.
- Failed processing jobs must retry automatically with bounded attempts before entering a final failed state that supports manual retry.
- v1 must provide built-in scheduled local backups and a restore UI.
- Scheduled backups must run daily, retain 30 days of successful backups, and allow restoring any successful backup within 15 minutes.
- A successful restore must recover at least raw archive items, summaries, structured facts, canonical memory, provenance metadata, configuration needed for the restored dataset, and audit events retained within the backup.

## Performance
### Requirements
- Ingestion acknowledgement should feel immediate for personal-scale use.
- Search and retrieval should remain interactive on personal-scale datasets.
- Expensive indexing and reprocessing work may run asynchronously.
- v1 ingestion should synchronously complete only raw archive persistence and lightweight metadata extraction before acknowledging success.
- Ingestion acknowledgement must meet $P95 \le 1\text{ s}$ for paste import and file upload up to 5 MB under normal local conditions.
- Search and retrieval must meet $P95 \le 2\text{ s}$ on personal-scale datasets up to 100k stored items.

### Benchmark definition baseline
- “Normal local conditions” means the standard local Docker deployment profile running on a single-user workstation with persisted local storage and no concurrent multi-user traffic.
- “100k stored items” means the combined indexed workload across raw items, derived summaries, structured facts, and searchable chunks used by the active retrieval/search path.

## Extensibility
- The architecture must support swapping embedding providers.
- The architecture must support changing summarization logic.
- The architecture must support adding classifiers, extractors, and connectors later.
- Previously ingested data must be reprocessable when logic changes.
- The architecture should support both provider-backed and future local processing implementations without changing the core memory model.
- The architecture should treat PostgreSQL full-text search and `pgvector` as the v1 baseline while keeping retrieval composition logic modular.
- v1 architecture choices should preserve a credible path to a future sellable service, including later support for tenant boundaries, hosted deployment profiles, and policy-driven controls.
- v1 must preserve service-ready boundaries through clear separation between domain logic, deployment profile concerns, and policy enforcement hooks, even though only the single-user local-first profile ships in v1.

## Degraded-mode behavior
- When no external provider is configured or reachable, the system should remain usable for ingestion, local storage, browsing, keyword search, and any basic local processing included in v1.
- Provider-dependent features should surface a pending, unavailable, or retryable state instead of failing silently.
- If no embeddings are available locally and no external provider is configured, degraded mode should expose keyword search plus cached semantic results from previously embedded content only.

## Portability
### Requirements
- Users must be able to export raw content, summaries, structured facts, canonical memory, and metadata.
- Exported data must be re-importable into Recalium without bespoke conversion.
- v1 must support at least one open machine-readable export format.
- v1 must support at least one human-readable or human-browsable archive format.
- The first machine-readable export/import format for v1 is a JSON bundle.
- The first human-readable export format for v1 is a zip bundle containing Markdown plus linked assets.
- The human-readable export zip must use a hybrid structure with a top-level index, type-based folders, and manifest metadata that preserves source, session, and provenance links.

## Observability and auditability
- Provenance must be inspectable for summaries, facts, and canonical memory.
- Machine-client access events must be recorded when available.
- Users must be able to inspect when memory was created, derived, modified, and accessed.
- Audit logging and audit UI detail must be configuration-driven.
- The standard v1 configuration should expose a basic event list plus a per-event detail drawer showing items such as source identifiers and retrieval-mode details.
- Configuration must allow operators to enable more detailed audit logging and fuller audit views when needed.
- Access-event history must be retained for at least 90 days in v1.
- Every summary, fact, and canonical item must expose minimum provenance fields: source item ID, source system, captured timestamp, derivation process, derivation timestamp, session or conversation ID where available, import method, source excerpt or hash, and modifying user or client identity where applicable.
- Every audit access event must capture timestamp, client or agent identity, operation type, result count, target or query summary, retrieval mode, success or failure status, source or item IDs touched where applicable, and policy decision reason when access is limited.

## Extraction quality
### Requirements
- Every extracted fact must include a source span: the exact quoted text from the source it was derived from.
- Every extracted fact must include a confidence tier: `high`, `medium`, or `low`, based on extraction model output or heuristic signal.
- Every extracted fact must record the derivation method (e.g., `llm_extraction`, `rule_based`) and the model or method version used.
- Extraction quality must be measurable: a hand-labeled test corpus of at least 200 input/output pairs must be maintained. At the `high` confidence tier, extracted facts must achieve at least 70% precision on this corpus.
- Facts with no attributable source span must not be promoted to canonical memory without explicit user confirmation.

## Cold-start
### Requirements
- A user must be able to go from zero to their first retrieved search result within 30 minutes using a ChatGPT or Claude conversation export.
- v1 first-run setup must offer "import your history" as the primary onboarding path.
- Bulk import from ChatGPT JSON export and Claude JSON export formats must be supported at launch.

## Accessibility and compatibility
### Current baseline
- The local web UI must be clear, responsive, and support efficient review workflows.
- The default v1 deployment target is a local Docker-based service with a localhost web UI.
- The localhost web UI must support the latest Chrome/Chromium browser in v1.
- Keyboard-only operation is required for core workflows including ingest, search, fact review, canonical edit, review queue, and restore.
- Core workflows must have no critical accessibility failures (missing labels, keyboard traps, unannounced state changes). Full WCAG 2.1 AA compliance is a v2 target.
