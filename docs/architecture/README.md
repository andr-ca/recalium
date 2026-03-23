# Recalium Architecture

## Status
- Phase: Approved baseline
- Based on: reviewed requirements handoff
- Scope: Recalium v1 local-first Docker deployment

## Document map
- [tech-stack.md](tech-stack.md) — committed tech stack decisions (Python/FastAPI, React/TypeScript, PostgreSQL/pgvector, MCP SDK) — **read this first before implementing anything**
- [../requirements/README.md](../requirements/README.md) — source requirements index and decision log
- [../requirements/product-overview.md](../requirements/product-overview.md) — product scope, goals, and baseline decisions
- [../requirements/nfr.md](../requirements/nfr.md) — measurable non-functional requirements that the architecture must satisfy
- [architect-handoff.md](architect-handoff.md) — architecture handoff entry point
- [../operational/requirements-reviews/recalium-v1-review-handoff.md](../operational/requirements-reviews/recalium-v1-review-handoff.md) — reviewed requirements handoff package used as the architecture baseline
- [../operational/architecture-reviews/README.md](../operational/architecture-reviews/README.md) — architecture QA index and review trail
- [../operational/tests/README.md](../operational/tests/README.md) — QA automation index
- [../operational/tests/qa-automation-stack.md](../operational/tests/qa-automation-stack.md) — selected QA automation tools and gate model
- [../operational/architecture-reviews/recalium-v1-architecture-handoff.md](../operational/architecture-reviews/recalium-v1-architecture-handoff.md) — explicit handoff from reviewed requirements into architecture
- [../operational/architecture-reviews/recalium-v1-architecture-review.md](../operational/architecture-reviews/recalium-v1-architecture-review.md) — current architecture review result
- [../operational/architecture-reviews/recalium-v1-architecture-review-final.md](../operational/architecture-reviews/recalium-v1-architecture-review-final.md) — final architecture review result
- [../operational/architecture-reviews/recalium-v1-return-to-architect.md](../operational/architecture-reviews/recalium-v1-return-to-architect.md) — explicit return path when architecture review requests changes
- [../operational/architecture-reviews/recalium-v1-architect-response.md](../operational/architecture-reviews/recalium-v1-architect-response.md) — architect response and remediation plan for review feedback
- [system-context.md](system-context.md) — system goals, actors, and major components
- [component-boundaries.md](component-boundaries.md) — module ownership, dependency rules, and key sequence flows
- [container-topology.md](container-topology.md) — local Docker deployment model
- [ui-architecture.md](ui-architecture.md) — localhost UI architecture and accessibility-critical workflow expectations
- [storage-and-indexing.md](storage-and-indexing.md) — PostgreSQL, FTS, `pgvector`, and data boundaries
- [artifact-storage.md](artifact-storage.md) — raw artifact/blob storage strategy and consistency model
- [processing-pipeline.md](processing-pipeline.md) — synchronous ingest path and asynchronous jobs
- [queue-and-jobs.md](queue-and-jobs.md) — durable job architecture and retry/recovery model
- [retrieval-and-ranking.md](retrieval-and-ranking.md) — search, ranking, trimming, and degraded mode
- [privacy-and-policy.md](privacy-and-policy.md) — sensitivity classification and external-processing controls
- [deletion-and-tombstones.md](deletion-and-tombstones.md) — deletion/redaction architecture across live state, restore, and export/import
- [audit-and-provenance.md](audit-and-provenance.md) — provenance fields, audit events, and reviewability
- [backup-and-restore.md](backup-and-restore.md) — backup, restore, and deleted-data behavior
- [api-and-mcp.md](api-and-mcp.md) — local API and MCP surface baseline
- [security-and-identity.md](security-and-identity.md) — localhost-only and exposed-mode security architecture
- [portability-and-export.md](portability-and-export.md) — export/import architecture and contract versioning
- [performance-and-operability.md](performance-and-operability.md) — performance tactics, queue durability, and benchmark approach
- [future-service-compatibility.md](future-service-compatibility.md) — service-ready boundaries for future productization
- [delivery-phases.md](delivery-phases.md) — implementation slices and technical risk order

## Architecture posture
This package assumes a modular monolith for v1 running locally in Docker, with clear boundaries that preserve a future path toward a hosted or sellable service without introducing unnecessary v1 runtime complexity.

## Traceability
- Requirements baseline: [../requirements/README.md](../requirements/README.md)
- Reviewed requirements handoff: [../operational/requirements-reviews/recalium-v1-review-handoff.md](../operational/requirements-reviews/recalium-v1-review-handoff.md)
- Architecture QA / review trail:
	- [../operational/architecture-reviews/recalium-v1-architecture-handoff.md](../operational/architecture-reviews/recalium-v1-architecture-handoff.md)
	- [../operational/architecture-reviews/recalium-v1-architecture-review.md](../operational/architecture-reviews/recalium-v1-architecture-review.md)
	- [../operational/architecture-reviews/recalium-v1-return-to-architect.md](../operational/architecture-reviews/recalium-v1-return-to-architect.md)
	- [../operational/architecture-reviews/recalium-v1-architect-response.md](../operational/architecture-reviews/recalium-v1-architect-response.md)
	- [../operational/architecture-reviews/recalium-v1-architecture-review-final.md](../operational/architecture-reviews/recalium-v1-architecture-review-final.md)

## Next step
Implementation planning package:
- [../plans/README.md](../plans/README.md)
