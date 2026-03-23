# Architecture QA Tech Stack

## Purpose
This document summarizes the Recalium v1 technology stack that architecture QA reviewed and approved.

## Runtime stack
- Deployment model: local-first Docker deployment
- Runtime posture: modular monolith
- Default runtime components:
  - `recalium-app` — application container; hosts the FastAPI API, React UI static assets, worker loop, backup scheduler, and import watcher as in-process tasks
  - `recalium-postgres` — PostgreSQL database container with `pgvector`

## Storage and retrieval stack
- Primary database: PostgreSQL
- Keyword search: PostgreSQL full-text search
- Semantic search: `pgvector`
- Hybrid retrieval: application-layer merge and ranking over FTS and vector results
- Blob and artifact bytes: artifact storage adapter backed by persisted local storage

## Processing stack
- Synchronous path: raw archive persistence and lightweight metadata extraction
- Asynchronous path: chunking, summarization, fact extraction, duplicate/overlap grouping, embeddings, and search publication
- Job model: PostgreSQL-backed durable queue with retry and recovery behavior

## Interface stack
- Primary user surface: localhost web UI with left-nav workflow structure
- Programmatic surface: local API and MCP-compatible tools
- Exposure posture: localhost-only by default, broader exposure optional with added security controls

## Security and policy stack
- Sensitive-content gate: local user declaration plus local rule-based pre-classification
- External-processing control: policy gate before provider-backed processing
- Deletion model: tombstones and suppression behavior across live state, restore, and export/import
- Audit and provenance: explicit audit events and provenance metadata

## Portability and resilience stack
- Backup model: scheduled backups with staged restore and validation
- Portability formats:
  - machine-readable JSON export/import
  - human-readable Markdown-plus-assets export

## Source architecture references
- [../../architecture/container-topology.md](../../architecture/container-topology.md)
- [../../architecture/storage-and-indexing.md](../../architecture/storage-and-indexing.md)
- [../../architecture/artifact-storage.md](../../architecture/artifact-storage.md)
- [../../architecture/processing-pipeline.md](../../architecture/processing-pipeline.md)
- [../../architecture/queue-and-jobs.md](../../architecture/queue-and-jobs.md)
- [../../architecture/api-and-mcp.md](../../architecture/api-and-mcp.md)
- [../../architecture/ui-architecture.md](../../architecture/ui-architecture.md)
- [../../architecture/privacy-and-policy.md](../../architecture/privacy-and-policy.md)
- [../../architecture/deletion-and-tombstones.md](../../architecture/deletion-and-tombstones.md)
- [../../architecture/audit-and-provenance.md](../../architecture/audit-and-provenance.md)
- [../../architecture/backup-and-restore.md](../../architecture/backup-and-restore.md)
- [../../architecture/portability-and-export.md](../../architecture/portability-and-export.md)
