# Architect Handoff

## Status
- Ready for architect: Yes
- Source requirements reviewed: Yes
- Open product-scope questions: No

## Primary source documents
- [../requirements/README.md](../requirements/README.md)
- [../requirements/product-overview.md](../requirements/product-overview.md)
- [../requirements/nfr.md](../requirements/nfr.md)
- [../requirements/assumptions-and-risks.md](../requirements/assumptions-and-risks.md)
- [../requirements/features/platform-v1/overview.md](../requirements/features/platform-v1/overview.md)
- [../requirements/features/platform-v1/workflows.md](../requirements/features/platform-v1/workflows.md)
- [../requirements/features/platform-v1/rules-and-edge-cases.md](../requirements/features/platform-v1/rules-and-edge-cases.md)
- [../requirements/features/platform-v1/acceptance-criteria.md](../requirements/features/platform-v1/acceptance-criteria.md)
- [../operational/requirements-reviews/recalium-v1-review-handoff.md](../operational/requirements-reviews/recalium-v1-review-handoff.md)
- [../operational/architecture-reviews/recalium-v1-architecture-handoff.md](../operational/architecture-reviews/recalium-v1-architecture-handoff.md)

## Product summary
Recalium v1 is a local-first, Docker-based, single-user personal memory platform that ingests conversations and artifacts, preserves raw history, derives searchable memory layers, and exposes governed retrieval through a localhost web UI and MCP-compatible interfaces.

## Architecturally significant constraints
- Local Docker deployment is the primary v1 runtime profile
- PostgreSQL + PostgreSQL FTS + `pgvector` is the baseline storage/search stack
- Raw archive persistence and lightweight metadata extraction are synchronous
- Summaries, facts, embeddings, and indexing are asynchronous
- Sensitive content must be identified locally before any external processing
- Unknown or low-confidence content defaults to blocking external processing
- Retrieval uses strict priority trimming: canonical, facts, summaries, raw excerpts
- Canonical memory outranks conflicting extracted memory, which may appear only as labeled lower-ranked evidence
- Deletion/redaction must cascade-suppress derived artifacts immediately
- Future-service compatibility must be preserved without expanding v1 into multi-user scope

## Architecture deliverables expected next
- System context and container topology
- Component architecture and service boundaries
- Storage and indexing architecture
- Processing pipeline and job model
- Retrieval and ranking architecture
- Privacy and sensitivity enforcement design
- Provenance and audit design
- Backup and restore architecture
- MCP/API contract architecture
- Future-service compatibility strategy
- Delivery phases and technical risk treatment

## Current architecture package
- [README.md](README.md)
- [system-context.md](system-context.md)
- [component-boundaries.md](component-boundaries.md)
- [container-topology.md](container-topology.md)
- [storage-and-indexing.md](storage-and-indexing.md)
- [artifact-storage.md](artifact-storage.md)
- [processing-pipeline.md](processing-pipeline.md)
- [queue-and-jobs.md](queue-and-jobs.md)
- [retrieval-and-ranking.md](retrieval-and-ranking.md)
- [privacy-and-policy.md](privacy-and-policy.md)
- [deletion-and-tombstones.md](deletion-and-tombstones.md)
- [audit-and-provenance.md](audit-and-provenance.md)
- [backup-and-restore.md](backup-and-restore.md)
- [api-and-mcp.md](api-and-mcp.md)
- [security-and-identity.md](security-and-identity.md)
- [portability-and-export.md](portability-and-export.md)
- [performance-and-operability.md](performance-and-operability.md)
- [future-service-compatibility.md](future-service-compatibility.md)
- [delivery-phases.md](delivery-phases.md)

## Handoff note
This file is the explicit handoff from reviewed requirements to architecture. The architect should treat the requirements package as the baseline and raise only contradictions or architecture-forcing gaps, not rediscover product scope.

If architecture review finds blocking issues, use [../operational/architecture-reviews/recalium-v1-return-to-architect.md](../operational/architecture-reviews/recalium-v1-return-to-architect.md) as the explicit return-to-architect package.
