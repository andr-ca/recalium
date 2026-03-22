# Recalium Requirements

## Status
- Classification: New product
- Maturity: Detailed draft ready for review
- Review readiness: Ready for reviewer handoff

## Canonical package rules
- This file is the canonical high-level requirements document and index for the requirements package.
- If requirements are split across multiple files, every requirements file must be linked from this document with a one-line description.
- Feature-level `overview.md` files should act as local indexes when a feature is split across several files.
- New or revised atomic requirement statements should use stable unique identifiers in the form `<feature-short-name>-NNN`. This applies to standalone requirement statements in dedicated requirements files (e.g., acceptance criteria, import-quality rules). Narrative prose, working decision log entries, and assumptions do not require IDs. Note: requirements added in this PR predate full ID enforcement and will be back-filled in a follow-on pass before implementation begins.

## Document map
- [../architecture/architect-handoff.md](../architecture/architect-handoff.md) — explicit architect-facing handoff package
- [product-overview.md](product-overview.md) — purpose, problem, goals, scope, actors, product principles, feature priority, validation gates, and key bets
- [personas.md](personas.md) — user personas grounding requirements in concrete user profiles
- [competitive-differentiation.md](competitive-differentiation.md) — competitor comparison, protocol play, and business model
- [glossary.md](glossary.md) — working domain vocabulary
- [nfr.md](nfr.md) — cross-cutting non-functional requirements including processing cost visibility, API key management (BYOK), usage telemetry, and extraction quality targets
- [assumptions-and-risks.md](assumptions-and-risks.md) — assumptions, dependencies, risks, competitive response scenarios, and open questions
- [features/platform-v1/overview.md](features/platform-v1/overview.md) — v1 product capability scope
- [features/platform-v1/workflows.md](features/platform-v1/workflows.md) — primary user and system workflows including first-run setup
- [features/platform-v1/rules-and-edge-cases.md](features/platform-v1/rules-and-edge-cases.md) — rules, lifecycle handling, and exception behavior
- [features/platform-v1/acceptance-criteria.md](features/platform-v1/acceptance-criteria.md) — testable v1 acceptance criteria including anti-criteria and BYOK criteria
- [features/platform-v1/import-quality.md](features/platform-v1/import-quality.md) — import data quality requirements for ChatGPT, Claude, and generic exports
- [../operational/architecture-reviews/recalium-v1-architecture-handoff.md](../operational/architecture-reviews/recalium-v1-architecture-handoff.md) — explicit handoff package for architecture work

## Current scope baseline
This requirements set captures the user's initial consolidated draft for Recalium v1: a local-first, MCP-enabled, single-user personal memory platform that ingests conversations and related artifacts, preserves raw sources, derives structured and searchable memory, enables governed retrieval, and provides a local web UI for review and curation.

## Discovery status
The current draft is strong on product intent and functional scope. No product-scope open questions are currently tracked.

## Working decision log
- Recalium v1 is local-first and single-user.
- Recalium v1 runs as a local Docker-based service with two containers: `recalium-app` and `recalium-postgres`.
- Tech stack is committed: Python/FastAPI, React/TypeScript, PostgreSQL/pgvector. See docs/architecture/tech-stack.md.
- Recalium v1 decisions should not block a future sellable service or later multi-tenant productization.
- v1 must NOT add tenant-aware columns, multi-user auth, or enterprise policy engines. Add these when a second tenant exists, not before.
- The open memory bundle format (JSON export/import) is a first-class deliverable and intended as a publishable open spec.
- Cold-start is a first-class requirement: bulk import from ChatGPT and Claude exports must ship at launch.
- Every extracted fact must include source span, confidence tier, derivation method, and derivation model.
- Hybrid retrieval uses Reciprocal Rank Fusion (RRF) with k=60, top-50 candidate pool per mode, top-20 merged results.
- Browser extension ("Recalium Capture") is deferred to v2.
- Temporal decay, confidence-based auto-curation are deferred to v2.
- WCAG 2.1 AA full compliance is a v2 target; v1 requires no critical accessibility failures and keyboard operability.
- Recalium v1 may use external providers for summarization, extraction, or embeddings from day one.
- If external providers are unavailable, v1 should still support keyword search and some basic local processing, while advanced processing waits.
- The first structured machine-readable export/import format for v1 should be a JSON bundle.
- The first human-readable export format for v1 should be a zip bundle containing Markdown plus assets.
- Personal profile and relationships should be treated as sensitive by default in v1.
- During ingestion, only raw archive persistence and lightweight metadata extraction should run synchronously; summaries, facts, embeddings, and indexing should run asynchronously.
- The v1 storage and search baseline should be PostgreSQL with built-in full-text search and `pgvector`.
- Sensitive categories should be blocked from external processing by default unless the user explicitly overrides that behavior.
- Sensitive-content identification before external processing should use user declaration plus local rule-based pre-classification.
- Content that is unknown or not confidently classified must be blocked from external processing by default.
- When a raw source item is deleted or redacted, derived summaries, facts, embeddings, and search visibility must be immediately cascade-suppressed and marked as source-removed.
- If canonical memory originated from a deleted or redacted source, it should remain but be marked as source-removed and require user review.
- Future backups and exports must exclude deleted or redacted data, and the UI must flag older backups or exports that may still contain that data.
- In degraded mode without local embeddings or an external provider, v1 should support keyword search plus cached semantic results from previously embedded content only.
- When canonical and extracted memory conflict, retrieval should return canonical memory first and include conflicting extracted memory only as lower-ranked evidence with explicit conflict labeling.
- Retrieval should use strict priority trimming: canonical first, then facts, then summaries, then raw excerpts, stopping as soon as the context budget is met.
- Every summary, fact, and canonical item should expose minimum provenance fields: source item ID, source system, captured timestamp, derivation process, derivation timestamp, session or conversation ID where available, import method, source excerpt or hash, and modifying user or client identity where applicable.
- Every audit access event should capture timestamp, client or agent identity, operation type, result count, target or query summary, retrieval mode, success or failure status, source or item IDs touched where applicable, and policy decision reason when access is limited.
- MCP `retrieve` responses should include returned items, source links, item type, rank score, provenance metadata, conflict labels, budget or trimming reason, and retrieval-mode metadata.
- MCP ingestion requests should include raw content, source metadata, client identity, import method, idempotency key where available, sensitivity hints, project hint, and requested processing mode.
- The first low-friction local ingestion workflow for v1 should be a watched import folder.
- Duplicate and overlap review in v1 should use a dedicated review queue with grouped similar facts and compare actions.
- The first web UI navigation model should be a left-nav app with top-level sections for Ingest, Archive, Facts, Canonical, Search, Review Queue, Audit, and Settings.
- Audit visibility should be configuration-driven: the standard default should expose a basic event list plus per-event detail drawer, while configuration should allow more detailed logging and UI exposure when enabled.
- Ingestion acknowledgement should meet $P95 \le 1\text{ s}$ for paste import and file upload up to 5 MB under normal local conditions.
- Search and retrieval should meet $P95 \le 2\text{ s}$ on personal-scale datasets up to 100k stored items.
- No acknowledged raw archive item may be lost after a container restart or host reboot, assuming persisted Docker volumes remain intact.
- Failed processing jobs should retry automatically with bounded attempts before surfacing final failure for manual retry.
- v1 should include built-in scheduled local backups plus a restore UI.
- v1 backups should run daily, retain 30 days of backups, and restore any successful backup within 15 minutes.
- The localhost web UI should support the latest Chrome/Chromium only in v1.
- Keyboard-only operation should be required for core workflows in v1.
- Core workflows in the localhost web UI should meet WCAG 2.1 AA.
- First-run setup should offer external-provider configuration, but the system should still start usable without it.
- Access-event history should be retained for at least 90 days in v1.
- The Markdown-plus-assets export zip should use a hybrid structure with a top-level index, type-based folders, and manifest metadata carrying source and session links.
- Canonical memory requires explicit user action.
- Automated vendor-specific connectors are out of scope for v1.
- A local web UI is the primary review surface for v1.
- Advanced per-agent permissions are deferred beyond v1.
- Duplicate/overlap management is required, but sophisticated automatic merge logic is not required for v1.
- v1 uses a BYOK (Bring Your Own Key) model as the default: users provide their own provider API keys. A managed processing tier is a future paid upsell.
- API keys must be stored only in local configuration, never in backups, exports, or transmitted to any Recalium-operated service.
- Processing cost estimation and display are required before bulk import confirmation.
- Import preview with filtering (conversation count, token volume, cost estimate, trivial-conversation filter) is required for the first-run experience.
- Feature priority follows MoSCoW classification defined in product-overview.md.
- Validation gates at Slice A, Slice B, and 4 weeks post-launch are required before proceeding to full release hardening.
- Extraction quality requires both precision (≥70% at high confidence) and recall (≥50% at high confidence) targets measured against a labeled corpus of real export data.
- Local-only usage telemetry is required for validation gate measurement.
- Competitive response scenarios for vendor memory export, MCP stall, funded competitor local-first pivot, and OS-level AI memory are documented in assumptions-and-risks.md.
