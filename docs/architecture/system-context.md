# System Context

## Purpose
Recalium provides a portable local memory layer that captures user interactions and artifacts, preserves raw source material, derives searchable memory layers, and returns governed context to users and MCP-compatible clients.

## Primary actors
- Primary user
- Local web UI
- MCP-compatible client or agent
- Recalium Capture browser extension
- Processing workers
- External AI providers, when configured

## Major components
1. `web-ui` — localhost review and curation client
2. `api` — local application server for UI, MCP, and internal orchestration
3. `recalium-capture-extension` — browser-based capture for zero-friction chat ingestion
4. `worker` — asynchronous processing runner for summaries, extraction, embeddings, indexing, and reprocessing
4. `postgres` — primary store for raw archive metadata, facts, canonical memory, audit events, and search indexes
5. `recalium-backup` — scheduled backup and restore coordination component
6. `import-watcher` — watched-folder ingestion component

See [ui-architecture.md](ui-architecture.md) for UI-specific workflow and accessibility architecture expectations.

## Logical modules
- `ingest`
- `archive`
- `derived-memory`
- `canonical-memory`
- `policy`
- `retrieval`
- `audit`
- `operations`
- `jobs`
- `artifact-storage`
- `portability`

See [component-boundaries.md](component-boundaries.md) for ownership and dependency rules.

## Architectural style
- v1 default: modular monolith split into deployable containers where useful
- internal boundaries: ingest, memory domain, retrieval, policy, audit, and backup modules
- future-service path: preserve deploy-profile separation and policy hooks without adding multi-tenant runtime complexity in v1

## Key system boundaries
- Raw archive boundary
- Derived-memory boundary
- Canonical-memory boundary
- Policy and sensitivity boundary
- Search/retrieval boundary
- Audit/provenance boundary
- Export/import boundary
- Operations and backup boundary
