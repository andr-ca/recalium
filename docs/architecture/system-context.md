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

## Runtime components
Two Docker containers:

1. `recalium-app` — combined application container:
   - FastAPI API server (Uvicorn)
   - React UI (served as static files)
   - In-process background worker (asyncio job loop)
   - Scheduled backup cron task
   - Optional import watcher background task

2. `recalium-postgres` — PostgreSQL 16+ with pgvector

See [container-topology.md](container-topology.md) for the rationale and [tech-stack.md](tech-stack.md) for committed stack decisions.

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
