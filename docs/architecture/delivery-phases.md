# Delivery Phases

## Phase 1 — foundational local platform
- local Docker topology
- PostgreSQL with FTS and `pgvector`
- raw archive ingest
- basic web UI shell
- provenance and audit foundations

## Phase 2 — derived memory pipeline
- background workers
- summaries
- extracted facts
- duplicate/overlap queue materialization
- reprocessing support

## Phase 3 — retrieval and review
- keyword, semantic, and hybrid retrieval
- strict priority trimming
- canonical-memory workflows
- review queue and fact management

## Phase 4 — privacy and operations hardening
- sensitivity gate
- deletion/redaction propagation
- scheduled backups and restore UI
- degraded-mode handling
- external-provider setup flow

## Phase 5 — future-service hardening
- service-ready boundary review
- deploy-profile separation cleanup
- API/MCP contract hardening
- architecture readiness for a future sellable service
