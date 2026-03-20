# Work Breakdown

This document is the execution control surface for Recalium v1. Each epic identifies its outcome, included scope, prerequisites, and the evidence required to close it.

## WS1 — Runtime and deployment foundation

### WS1-E1 — Docker topology and local profiles
- Outcome: local runtime can start the required product containers consistently.
- Includes: compose topology, default profiles, local persistence mounts, health baselines.
- Excludes: feature-complete application behavior.
- Prerequisites: none.
- Completion evidence: runtime boots cleanly, services reach healthy state, persistence paths documented.

### WS1-E2 — Service skeletons
- Outcome: API, worker, backup, and optional import-watcher services exist as executable runtime units.
- Includes: process startup, health endpoints or equivalent readiness, shared logging conventions.
- Excludes: business-complete workflows.
- Prerequisites: WS1-E1.
- Completion evidence: each service starts, logs, and reports readiness in the local runtime.

### WS1-E3 — Configuration and startup validation
- Outcome: the product has a stable config model with explicit secret boundaries.
- Includes: environment loading, config validation, missing-config startup failures, safe defaults.
- Excludes: interactive settings UI.
- Prerequisites: WS1-E1.
- Completion evidence: invalid config fails fast, documented required variables, secrets separated from restorable config.

### WS1-E4 — Database baseline and migrations
- Outcome: PostgreSQL baseline supports required extensions and repeatable migrations.
- Includes: extension setup, migration flow, schema bootstrap.
- Excludes: full feature schema.
- Prerequisites: WS1-E1.
- Completion evidence: clean bootstrap, repeatable migration apply, extension readiness validated.

### WS1-E5 — Ingest latency and restart-durability baseline
- Outcome: the team has early control evidence for the synchronous ingest path and restart durability.
- Includes: ingest timing checks for the v1 local profile, restart-survival checks for accepted ingest and queued jobs.
- Excludes: retrieval and restore benchmarking.
- Prerequisites: WS3-E2, WS4-E1.
- Completion evidence: baseline ingest latency and restart-survival evidence exists before leaving the first batch.

## WS2 — Core data and storage foundation

### WS2-E1 — Raw archive and artifact storage contract
- Outcome: accepted source material has a durable system-of-record representation.
- Includes: raw archive records, artifact metadata, blob storage contract, local storage adapter.
- Excludes: portability exports.
- Prerequisites: WS1-E3, WS1-E4.
- Completion evidence: persisted archive record references stored bytes via stable contract.

### WS2-E2 — Provenance and audit schema
- Outcome: ingest, retrieval, review, and destructive actions can emit traceable records.
- Includes: provenance fields, audit event fields, retention-supporting schema.
- Excludes: full audit UI.
- Prerequisites: WS1-E4.
- Completion evidence: schema supports minimum provenance and audit fields defined by architecture.

### WS2-E3 — Operations metadata baseline
- Outcome: job, backup, restore, and review operational states have durable metadata.
- Includes: processing states, retry counters, timestamps, operator-facing status support.
- Excludes: polished operations UX.
- Prerequisites: WS1-E4.
- Completion evidence: core states can be queried and surfaced for operations.

### WS2-E4 — Tombstone and deletion ledger foundation
- Outcome: deletion-safe behavior has a durable representation before user-facing destructive flows exist.
- Includes: tombstones, deletion ledger, suppression anchors, source-removed markers.
- Excludes: full deletion UI.
- Prerequisites: WS1-E4, WS2-E1.
- Completion evidence: deleted or redacted sources can be represented without physical ambiguity.

### WS2-E5 — Retrieval-supporting indexes baseline
- Outcome: archive and derived data have the structural bases needed for later retrieval.
- Includes: FTS and vector-supporting structural setup, metadata filter support.
- Excludes: ranking behavior.
- Prerequisites: WS1-E4.
- Completion evidence: index-supporting structures are present and queryable.

## WS3 — Ingestion surfaces

### WS3-E1 — Canonical ingest contract
- Outcome: all intake paths target one ingestion command and state model.
- Includes: ingest state machine, idempotency behavior, acknowledgment rule, contract versioning, stable error taxonomy.
- Excludes: every concrete surface.
- Prerequisites: WS2-E1, WS2-E2, WS2-E3.
- Completion evidence: contract and error taxonomy documented and testable.

### WS3-E2 — Paste and file upload ingest
- Outcome: user can submit manual ingest through the primary local interface.
- Includes: paste input, file upload, lightweight metadata extraction.
- Excludes: heavy provider-backed processing.
- Prerequisites: WS3-E1.
- Completion evidence: accepted items are durably archived and auditable.

### WS3-E3 — MCP ingest baseline
- Outcome: MCP clients can ingest through the same canonical path.
- Includes: MCP request mapping, idempotency alignment, error contract.
- Excludes: non-v1 protocol expansions.
- Prerequisites: WS3-E1.
- Completion evidence: MCP ingest produces identical persistent outcomes to local ingest.

### WS3-E4 — Watched-folder ingest baseline
- Outcome: file drops can enter the ingest flow automatically.
- Includes: folder polling or watching behavior, duplicate handling, failure visibility.
- Excludes: remote file sync.
- Prerequisites: WS3-E1, WS1-E2.
- Completion evidence: dropped files are processed through the same ingest contract and state transitions.

## WS4 — Durable jobs and derived-memory pipeline

### WS4-E1 — Queue and worker recovery model
- Outcome: async work is durably scheduled, claimed, retried, and recovered.
- Includes: transactional enqueue, claim logic, retry logic, terminal failure handling, reprocessing hooks.
- Excludes: all downstream transforms.
- Prerequisites: WS2-E3, WS3-E1.
- Completion evidence: restart and crash scenarios preserve uncompleted work without duplication drift.

### WS4-E7 — Queue backlog and recovery observability
- Outcome: queue health is measurable early enough to control async delivery risk.
- Includes: queue depth visibility, retry visibility, job age visibility, backlog and recovery checks, foreground API impact checks under backlog conditions.
- Excludes: final release dashboards.
- Prerequisites: WS4-E1.
- Completion evidence: queue backlog, retry, recovery behavior, and backlog impact on foreground APIs can be inspected without database forensics.

### WS4-E2 — Chunking pipeline
- Outcome: archived source material is converted into chunk-level processing units.
- Includes: chunk creation rules, provenance inheritance, retry behavior.
- Excludes: provider-specific transforms.
- Prerequisites: WS4-E1.
- Completion evidence: chunk outputs are stable, attributable, and reprocessable.

### WS4-E3 — Summarization pipeline
- Outcome: provider-eligible content can produce summaries asynchronously.
- Includes: provider adapter call path, result persistence, failure handling.
- Excludes: policy bypasses.
- Prerequisites: WS4-E2, WS6-E1, WS6-E2.
- Completion evidence: eligible items summarize; ineligible items are skipped or blocked with audit evidence.

### WS4-E4 — Fact extraction pipeline
- Outcome: provider-eligible content yields extracted facts with provenance.
- Includes: extraction adapter path, fact persistence, review status support.
- Excludes: canonical conflict resolution.
- Prerequisites: WS4-E2, WS6-E1, WS6-E2.
- Completion evidence: extracted facts retain source and confidence/provenance fields.

### WS4-E5 — Duplicate and overlap grouping
- Outcome: potentially overlapping content is grouped for review.
- Includes: grouping candidates, queue support, review metadata.
- Excludes: automated destructive deduplication.
- Prerequisites: WS4-E2.
- Completion evidence: candidate groups are durable and reviewable.

### WS4-E6 — Embeddings and FTS publication
- Outcome: eligible content is published for search.
- Includes: FTS publication, embedding generation, index update behavior for currently eligible content.
- Excludes: final ranking rules.
- Prerequisites: WS4-E2, WS6-E2, WS2-E5.
- Completion evidence: content that is currently policy-eligible becomes searchable via the supported publication path.

## WS5 — Retrieval and curation

### WS5-E1 — Keyword retrieval
- Outcome: users can retrieve archive and derived memory via keyword search.
- Includes: filters, result assembly, provenance-visible result payloads.
- Excludes: semantic ranking.
- Prerequisites: WS4-E6, WS2-E2.
- Completion evidence: keyword search returns stable, traceable results within defined scope.

### WS5-E2 — Semantic retrieval
- Outcome: vector-backed retrieval works for eligible indexed content.
- Includes: semantic query path, result assembly, eligibility filtering.
- Excludes: hybrid merge.
- Prerequisites: WS4-E6.
- Completion evidence: semantic retrieval respects policy exclusions and provenance.

### WS5-E3 — Hybrid merge and strict priority trimming
- Outcome: hybrid retrieval enforces the architecture-defined ranking and budget behavior.
- Includes: merge, ranking, budget trimming, source precedence.
- Excludes: subjective ranking tuning beyond v1.
- Prerequisites: WS5-E1, WS5-E2.
- Completion evidence: trimming and precedence rules are testable and deterministic.

### WS5-E4 — Conflict labeling and provenance assembly
- Outcome: conflicting or overlapping facts are explainable to the user.
- Includes: conflict markers, source links, response provenance package.
- Excludes: autonomous conflict resolution.
- Prerequisites: WS5-E1, WS4-E4.
- Completion evidence: retrieve responses expose minimum provenance and conflict visibility defined by architecture.

### WS5-E5 — Facts and canonical memory workflows
- Outcome: users can review facts and maintain canonical memory safely.
- Includes: facts review actions, canonical create/update flows.
- Excludes: multi-user collaboration.
- Prerequisites: WS5-E4.
- Completion evidence: facts review and canonical create/update flows work with audit and provenance continuity.

### WS5-E6 — Review queue workflows
- Outcome: duplicate, overlap, and trust-related review items have a durable queue.
- Includes: queue states, assignment-free single-user processing, completion actions.
- Excludes: team workflow features.
- Prerequisites: WS4-E5, WS5-E5.
- Completion evidence: review items can be surfaced, actioned, and audited.

### WS5-E8 — Retrieval and search API contract closure
- Outcome: retrieval and search surfaces satisfy the v1 contract posture for versioning, stable errors, and bounded responses.
- Includes: explicit versioning, stable error taxonomy, bounded result envelopes or pagination behavior, retrieval-mode metadata, trimming-reason behavior.
- Excludes: future-service-only contract expansion.
- Prerequisites: WS5-E3, WS5-E4.
- Completion evidence: retrieval and search contract behavior is explicit, testable, and aligned with the architecture contract rules.

## WS6 — Trust, privacy, and destructive actions

### WS6-E1 — Sensitivity declaration and local pre-classification gate
- Outcome: sensitive or unknown content is identified before provider-backed processing.
- Includes: user-declared sensitivity, local rule-based pre-classification, unknown fallback behavior.
- Excludes: advanced ML-based local classification.
- Prerequisites: WS3-E1.
- Completion evidence: unknown or sensitive content is blocked from external processing by default.

### WS6-E2 — Provider eligibility enforcement
- Outcome: provider calls are allowed only for eligible content.
- Includes: policy checks before summarization, extraction, embeddings.
- Excludes: future multi-tenant policy complexity.
- Prerequisites: WS6-E1.
- Completion evidence: provider-bound jobs cannot bypass policy gate.

### WS6-E3 — Indexing and embedding exclusion enforcement
- Outcome: excluded content never becomes visible through disallowed retrieval paths.
- Includes: publication suppression, existing-entry suppression or removal hooks.
- Excludes: non-v1 archival purge strategies.
- Prerequisites: WS6-E2, WS4-E6.
- Completion evidence: excluded categories and sources do not appear in search or embedding-backed results.

### WS6-E4 — Deletion and redaction suppression flow
- Outcome: removed source material is suppressed from live derived memory and retrieval.
- Includes: deletion triggers, suppression, cascade handling, audit emission.
- Excludes: physical backup rewriting.
- Prerequisites: WS2-E4, WS5-E1.
- Completion evidence: deleted or redacted content disappears from active retrieval and review surfaces immediately.

### WS6-E5 — Canonical `source-removed` handling
- Outcome: canonical entries tied to removed sources become review-required rather than silently remaining trusted.
- Includes: state transition, operator/user visibility, audit linkages.
- Excludes: automated canonical repair.
- Prerequisites: WS6-E4, WS5-E5.
- Completion evidence: affected canonical entries transition to the required review state.

### WS6-E6 — Deleted-data warnings for backups and exports
- Outcome: portability and recovery surfaces reflect known limits for previously produced artifacts.
- Includes: warning language, metadata flags, operator visibility.
- Excludes: mutation of already-produced backups.
- Prerequisites: WS7-E1, WS7-E3, WS6-E4.
- Completion evidence: users are warned where deleted content may still exist in older artifacts.

### WS5-E7 — Retrieval latency benchmark control
- Outcome: retrieval performance risk is measured before release hardening.
- Includes: keyword latency checks, hybrid latency checks, representative dataset benchmark runs.
- Excludes: speculative scaling beyond v1.
- Prerequisites: WS5-E3.
- Completion evidence: keyword and hybrid retrieval latency evidence exists against the representative v1 dataset profile.

## WS7 — Operations, portability, and resilience

### WS7-E1 — Scheduled backups and retention
- Outcome: backup artifacts are created and retained according to v1 policy.
- Includes: backup jobs, manifests, retention enforcement, result visibility.
- Excludes: restore completion.
- Prerequisites: WS2-E1, WS2-E2, WS2-E4.
- Completion evidence: backup inventory reflects scheduled runs and retention policy.

### WS7-E2 — Staged restore and validation
- Outcome: restore completes only after validation and explicit cutover.
- Includes: restore staging, validation checks, cutover logic, post-restore health verification.
- Excludes: backup-side mutation.
- Prerequisites: WS7-E1, WS2-E4.
- Completion evidence: restored system meets cutover criteria and re-applies suppression semantics.

### WS7-E6 — Restore timing validation
- Outcome: restore timing risk is measured against the published v1 target before release signoff.
- Includes: restore-duration benchmark runs, representative dataset validation, timing evidence capture.
- Excludes: unsupported hardware profiles.
- Prerequisites: WS7-E2.
- Completion evidence: restore timing evidence exists for the standard local deployment baseline.

### WS7-E3 — JSON export and import
- Outcome: machine-readable portability works within the defined versioning contract.
- Includes: export manifest, bundle format, import validation, compatibility checks.
- Excludes: unsupported version migrations.
- Prerequisites: WS2-E1, WS2-E2, WS2-E4.
- Completion evidence: exported bundles re-import into compatible versions with expected fidelity.

### WS7-E4 — Markdown-plus-assets export
- Outcome: human-readable export is generated with linked assets.
- Includes: markdown layout, asset packaging, references, manifest integration.
- Excludes: re-import from markdown export.
- Prerequisites: WS2-E1, WS2-E2.
- Completion evidence: exported package can be unpacked and read without product runtime.

### WS7-E5 — Operator-facing operations surfaces
- Outcome: backup, restore, queue, and failure states are visible locally.
- Includes: operations views, state summaries, validation outcomes.
- Excludes: remote fleet management.
- Prerequisites: WS2-E3, WS7-E1, WS7-E2.
- Completion evidence: operator can inspect operational state without direct database access.

## WS8 — Web UI and release validation

### WS8-E1 — Left-nav shell with initial `Ingest` and `Operations` views
- Outcome: the localhost UI has a minimal shell sufficient for the first batch and early operational visibility.
- Includes: route skeleton, navigation frame, `Ingest` view, `Operations` view for ingest and queue state.
- Excludes: full memory workflow coverage and backup/restore management.
- Prerequisites: WS1-E2, WS3-E2, WS4-E7.
- Completion evidence: the first batch can be demonstrated through the web UI without direct database access.

### WS8-E2 — Core memory workflow views
- Outcome: required user-visible memory workflows are accessible in the web UI.
- Includes: Archive, Facts, Canonical, Search, Review Queue, and Audit views.
- Excludes: backup, restore, and deeper operations management.
- Prerequisites: WS5-E5, WS5-E6.
- Completion evidence: each required memory workflow view supports its primary v1 task.

### WS8-E3 — Operations, backup, restore, and settings views
- Outcome: operator-facing recovery and configuration workflows are accessible locally.
- Includes: operations, backup, restore validation, and settings views.
- Excludes: remote fleet management.
- Prerequisites: WS7-E5.
- Completion evidence: operator-facing operations and recovery workflows are visible in the web UI.

### WS8-E4 — Keyboard-only support
- Outcome: core workflows are operable without pointer input.
- Includes: focus order, primary actions, navigability.
- Excludes: unsupported browsers.
- Prerequisites: WS8-E2, WS8-E3.
- Completion evidence: core workflows pass keyboard-only checks.

### WS8-E5 — Accessibility validation
- Outcome: core workflows meet the documented accessibility target.
- Includes: accessibility review, defects, fixes, evidence capture.
- Excludes: unsupported browsers beyond Chrome/Chromium target.
- Prerequisites: WS8-E4.
- Completion evidence: core flows meet the v1 accessibility expectation.

### WS8-E6 — Performance and degraded-mode validation
- Outcome: published latency and degraded-mode expectations are proven.
- Includes: degraded-mode scenarios, consolidation of ingest, retrieval, restore, and queue-backlog foreground-impact benchmark evidence.
- Excludes: speculative scale targets beyond v1.
- Prerequisites: WS1-E5, WS5-E7, WS7-E6.
- Completion evidence: required performance and degraded-mode evidence is recorded.

### WS8-E7 — Release checklist and operator documentation
- Outcome: release readiness and local operation are documented.
- Includes: release checklist, operator startup and recovery guide, known limits.
- Excludes: hosted service operations.
- Prerequisites: WS8-E5, WS8-E6.
- Completion evidence: release checklist can be executed without rediscovery.
