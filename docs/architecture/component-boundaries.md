# Component Boundaries

## Runtime topology

The v1 runtime consists of two Docker containers:
- **`recalium-app`** — the application container, running API, worker loop, backup scheduler, and import-watcher as in-process tasks.
- **`recalium-postgres`** — the PostgreSQL database container.

The sections below describe the logical process boundaries and responsibilities **within `recalium-app`**. These are architectural modules, not separate containers or processes.

## Logical processes within `recalium-app`
### API process (`recalium-api` logical boundary)
Owns:
- UI-serving endpoints or frontend hosting integration
- local REST/API surface
- MCP-compatible interface surface
- ingest command handling
- retrieval orchestration
- canonical-memory mutation commands
- policy evaluation entry points
- audit event emission for synchronous calls

Must not own:
- long-running derivation work
- scheduled backup execution
- heavy reprocessing loops

### Worker process (`recalium-worker` logical boundary)
Owns:
- queued derivation jobs
- summarization, extraction, duplicate detection, embeddings, and indexing
- reprocessing flows
- deferred deletion/redaction propagation jobs if any non-immediate cleanup remains after synchronous suppression

Must not own:
- direct user session management
- primary request-response retrieval serving

### Database container (`recalium-postgres`)
Owns:
- durable persistence for archive, memory, audit, operations metadata, and search indexes
- FTS indexes
- vector storage and indexes via `pgvector`
- queue tables or durable job state if the v1 queue is database-backed

### Backup scheduler process (`recalium-backup` logical boundary)
Owns:
- scheduled backup creation
- backup manifest generation
- restore orchestration
- backup retention enforcement

### Import-watcher process (`recalium-import-watcher` logical boundary)
Owns:
- watched-folder scan/detect loop
- handoff of detected files into the same ingest contract used by API/MCP ingestion
- duplicate file detection and ingestion status visibility hooks

## Logical modules inside the application
### `ingest`
Responsibilities:
- validate payloads
- normalize source metadata
- persist raw archive
- emit ingest audit event
- enqueue downstream work

Depends on:
- `archive`
- `policy`
- `jobs`
- `audit`

### `archive`
Responsibilities:
- raw item storage
- source metadata
- raw item fetch and source-link lookup
- deletion/redaction state

Must not depend on retrieval or UI concerns.

### `derived-memory`
Responsibilities:
- summaries
- chunks
- extracted facts
- duplicate/overlap groupings
- embedding references
- derivation lineage

### `canonical-memory`
Responsibilities:
- canonical entry CRUD
- provenance linkage to promoting source
- source-removed review-required state management

### `policy`
Responsibilities:
- sensitivity gate decisions
- external-provider eligibility decisions
- exposure-mode policy checks
- retrieval suppression and deletion/redaction policy hooks
- future service/tenant-aware policy seams

### `retrieval`
Responsibilities:
- keyword/semantic/hybrid retrieval orchestration
- ranking merge
- conflict labeling
- strict budget trimming
- response assembly for UI/API/MCP

Depends on:
- `archive`
- `derived-memory`
- `canonical-memory`
- `policy`
- `audit`

### `audit`
Responsibilities:
- provenance read models
- access-event emission
- mutation-event emission
- audit query models

### `operations`
Responsibilities:
- backup metadata
- restore state
- import-watcher operational state
- reprocessing state

### `portability`
Responsibilities:
- JSON export generation
- Markdown-plus-assets export generation
- import manifest validation
- export/import version compatibility handling
- coordination with `archive`, `derived-memory`, `canonical-memory`, `audit`, and `artifact-storage` for portability artifacts

### `jobs`
Responsibilities:
- durable job enqueue/dequeue
- retry bookkeeping
- dead-letter or terminal-failure state
- worker concurrency controls

## Dependency direction rules
Allowed high-level dependency direction:
- `api` -> domain modules
- `worker` -> domain modules
- domain modules -> shared infrastructure adapters
- `retrieval` may read `archive`, `derived-memory`, `canonical-memory`, `policy`, `audit`
- `portability` may read `archive`, `derived-memory`, `canonical-memory`, `audit`, `artifact-storage`, and `operations`
- `policy` must not depend on UI or transport layers
- `archive` must not depend on `retrieval`
- `canonical-memory` must not depend on transport/UI layers

Forbidden examples:
- UI-aware logic inside `policy`
- worker-only orchestration logic inside `archive`
- direct external-provider calls bypassing `policy`

## Sequence flow A — ingest to review
1. UI/API/MCP submits ingest command.
2. `ingest` validates payload and idempotency context.
3. `policy` evaluates sensitivity and provider eligibility hints.
4. `archive` stores raw item and source metadata.
5. `audit` records ingest event.
6. `jobs` enqueues derivation tasks.
7. `worker` executes derivation tasks and writes to `derived-memory`.
8. duplicate/overlap groupings are materialized.
9. UI review surfaces query `archive`, `derived-memory`, and `audit` read models.

## Sequence flow B — retrieval with policy and trimming
1. UI/API/MCP submits retrieval request.
2. `retrieval` normalizes filters and retrieval mode.
3. `policy` evaluates access/suppression rules.
4. `retrieval` queries canonical, fact, summary, and raw candidate sets.
5. conflicts are labeled and ranked.
6. strict budget trimming is applied.
7. `audit` records retrieval event with policy decision context.
8. response is returned through UI/API/MCP adapter.
