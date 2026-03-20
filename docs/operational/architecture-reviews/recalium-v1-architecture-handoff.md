# Architecture Handoff

## 1. Handoff status
- Ready for architecture: Yes
- Requirements review completed: Yes
- Product-scope open questions remaining: No

## 2. Source requirements package
- [docs/requirements/README.md](../../requirements/README.md)
- [docs/requirements/product-overview.md](../../requirements/product-overview.md)
- [docs/requirements/glossary.md](../../requirements/glossary.md)
- [docs/requirements/nfr.md](../../requirements/nfr.md)
- [docs/requirements/assumptions-and-risks.md](../../requirements/assumptions-and-risks.md)
- [docs/requirements/features/platform-v1/overview.md](../../requirements/features/platform-v1/overview.md)
- [docs/requirements/features/platform-v1/workflows.md](../../requirements/features/platform-v1/workflows.md)
- [docs/requirements/features/platform-v1/rules-and-edge-cases.md](../../requirements/features/platform-v1/rules-and-edge-cases.md)
- [docs/requirements/features/platform-v1/acceptance-criteria.md](../../requirements/features/platform-v1/acceptance-criteria.md)
- [docs/operational/requirements-reviews/recalium-v1-review-handoff.md](../requirements-reviews/recalium-v1-review-handoff.md)

## 3. Product classification
- New product

## 4. Problem summary
Recalium is a local-first, Docker-based personal memory platform that preserves raw user interactions and artifacts, derives searchable memory layers, and exposes governed retrieval for future AI interactions across tools and models.

## 5. Architecture objectives
- Deliver a single-user local-first v1 without blocking a future sellable service
- Preserve service-ready boundaries for future tenant-aware and hosted deployment profiles
- Support PostgreSQL + PostgreSQL FTS + `pgvector` as the v1 storage and search baseline
- Provide a localhost web UI, MCP-compatible interfaces, and auditable access behavior
- Enforce privacy-sensitive processing defaults and source-backed reviewability

## 6. Architecturally significant requirements
### Deployment and runtime
- Local Docker-based deployment is the primary v1 runtime
- UI, API, and MCP endpoints bind to localhost by default
- Broader exposure is optional and requires authentication, session handling, and transport protection

### Processing model
- Raw archive persistence and lightweight metadata extraction are synchronous
- Summaries, facts, embeddings, and indexing are asynchronous
- External providers are optional and first-run configuration must not block basic usability
- Sensitive-content handling requires user declaration plus local rule-based pre-classification before any external processing
- Unknown or low-confidence content defaults to blocking external processing

### Storage and retrieval
- PostgreSQL is the primary local database
- PostgreSQL FTS is the keyword search baseline
- `pgvector` is the semantic search baseline
- Degraded mode supports keyword search plus cached semantic results from previously embedded content only
- Retrieval conflict rule: canonical memory first, conflicting extracted memory only as lower-ranked labeled evidence
- Retrieval budget rule: strict priority trimming in this order — canonical, facts, summaries, raw excerpts

### Privacy and destructive actions
- Raw-source deletion/redaction must immediately cascade-suppress derived artifacts from search and retrieval
- Canonical memory with removed source remains reviewable but must be marked `source-removed`
- Future backups/exports exclude deleted/redacted data; older backups/exports must be flagged as potentially containing it

### Audit and provenance
- Provenance fields are mandatory on summaries, facts, and canonical items
- Audit access events have a defined minimum field set and 90-day minimum retention
- MCP `retrieve` and ingestion contracts have defined minimum payload expectations

### Reliability and operations
- Zero loss for acknowledged raw archive items across restart/reboot with intact persisted volumes
- Daily backups, 30-day retention, restore within 15 minutes
- Successful restore must recover the minimum required artifact set defined in requirements

## 7. Key constraints
- Single-user local-first scope for v1
- No automated vendor-specific connectors in v1
- No multi-user runtime in v1
- No advanced per-agent permissions in v1
- Must remain future-compatible with a sellable service architecture

## 8. Risks the architecture must address
- False or conflicting memories
- Sensitive-data over-capture
- Retrieval overload and poor context budgeting
- Privacy gaps from external processing
- Trust erosion from weak provenance or deletion semantics
- Future productization blocked by tightly coupled local-only assumptions

## 9. Architecture deliverables requested
Please produce an architecture package that covers at least:
- system context and major components
- deployment topology for the local Docker profile
- storage architecture and data boundaries
- processing pipeline design
- retrieval/search architecture
- privacy/sensitivity enforcement design
- audit/provenance model
- backup/restore design
- MCP/API surface design
- future-service compatibility strategy
- implementation phases and major technical risks

## 10. Handoff note
This handoff is intended to move the project from reviewed requirements into architecture design. Requirements are considered stable enough for architecture unless new contradictions are discovered during design.
