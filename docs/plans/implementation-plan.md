# Implementation Plan

## Objective
Deliver Recalium v1 as a local-first Docker-based product through dependency-driven execution that proves durability, policy enforcement, retrieval correctness, and recoverability before release hardening.

## Planning principles
1. Build the durability-critical path first.
2. Keep synchronous ingest minimal from day one.
3. Establish audit, provenance, and policy capture before expanding feature breadth.
4. Deliver keyword retrieval before semantic and hybrid retrieval.
5. Treat deletion safety, backup correctness, and restore validation as core product behavior.
6. Validate measurable quality targets during delivery, not only at the end.

## Workstreams

### WS1 — Runtime and deployment foundation
Outcome: a reproducible local runtime exists for the product containers, configuration model, and database baseline.

Includes:
- Docker topology and local profiles
- service skeletons for API, worker, backup, and optional import watcher
- environment and configuration model
- secrets boundary and startup validation
- PostgreSQL baseline with required extensions and migration flow
- early ingest latency and restart-durability control points

### WS2 — Core data and storage foundation
Outcome: the system-of-record structures exist for archive, provenance, audit, operations, and deletion-safe behavior.

Includes:
- raw archive schema
- artifact storage contract and metadata model
- provenance schema
- audit event schema
- operations metadata
- tombstone and deletion ledger baseline
- retrieval-supporting indexes baseline

### WS3 — Ingestion surfaces
Outcome: all v1 intake paths converge on one durable ingest contract.

Includes:
- canonical ingest command contract
- paste and file upload ingest
- MCP ingest baseline
- watched-folder ingest baseline
- lightweight metadata extraction
- idempotency behavior

### WS4 — Durable jobs and derived-memory pipeline
Outcome: heavy processing happens asynchronously with recoverable queue behavior.

Includes:
- PostgreSQL-backed queue and worker recovery
- chunking
- summarization
- fact extraction
- duplicate and overlap grouping
- embeddings and FTS publication
- retry, failure, and reprocessing flows
- queue backlog, retry, and recovery observability

### WS5 — Retrieval and curation
Outcome: the user can search, review, and curate memory with provenance visibility.

Includes:
- keyword retrieval
- semantic retrieval
- hybrid merge and ranking
- strict priority trimming
- conflict labeling
- facts review
- canonical memory workflows
- review queue behavior

### WS6 — Trust, privacy, and destructive actions
Outcome: policy enforcement controls provider use, visibility, and removal behavior.

Includes:
- sensitivity declaration and local pre-classification gate
- provider eligibility enforcement
- source and category exclusion from indexing and embedding
- deletion and redaction suppression
- canonical `source-removed` state
- deleted-data warnings for older backups and exports

### WS7 — Operations, portability, and resilience
Outcome: the system can be backed up, restored, exported, and operated reliably.

Includes:
- scheduled backups and retention
- staged restore with validation and cutover
- JSON export and import
- Markdown-plus-assets export
- operator-facing operations surfaces

### WS8 — Web UI and release validation
Outcome: the required localhost UI is usable and release quality is proven.

Includes:
- left-nav application shell with initial `Ingest` and `Operations` routes
- core memory sections: Archive, Facts, Canonical, Search, Review Queue, Audit
- backup, restore, and settings operations views
- keyboard-only support for core flows
- accessibility validation
- performance validation
- degraded-mode validation
- operator documentation and release checklist

### WS9 — Intelligence and Ecosystem
Outcome: advanced intelligence features and low-friction ingestion surfaces are delivered.

Includes:
- Recalium Capture browser extension for chat ingestion
- conflict detection logic and UI for fact resolution
- temporal decay and relevance weighting in retrieval
- confidence scoring for extraction and auto-curation
- local embedding support (Ollama/Sentence Transformers)
- ecosystem reference clients (VS Code extension baseline)

## Sequencing model

### Hard prerequisites
- WS1 and WS2 foundations must exist before production ingest paths are considered complete.
- Audit and provenance structures must land before ingest and retrieval workflows are closed.
- Queue durability must land before any derived-memory pipeline work is treated as stable.
- Policy gating must land before any external-provider-backed processing is enabled.
- Embedding publication must land before semantic and hybrid retrieval are closed.
- Tombstone and deletion-ledger behavior must land before deletion, restore correctness, or export correctness are claimed complete.
- API and MCP contract versioning and stable error taxonomy must be defined before API and MCP surfaces are considered complete.
- Conflict detection and auto-curation (WS9) depend on stable derived-memory (WS4).

### Recommended execution order
1. WS1 runtime foundation and WS2 data foundation
2. WS3 ingest contract, one primary ingest path, and initial UI shell
3. WS4 durable jobs and minimal pipeline behavior
4. WS3 remaining ingest surfaces and API/MCP contract hardening
5. WS5 keyword retrieval before semantic and hybrid retrieval
6. WS6 trust controls before broader provider-backed behavior
7. WS7 backup, restore, and portability after stable storage semantics
8. WS8 hardening, validation, and release readiness

### Parallelizable areas
- Container skeletons, configuration model, and database baseline can progress in parallel.
- UI shell can begin once core route and API contracts stabilize.
- Export formats can begin after archive, provenance, and artifact storage contracts stabilize.
- Validation harnesses can be created alongside delivery instead of waiting for hardening.

## First implementation batch

### Batch 1 — Durable ingest spine
This is the mandatory first execution batch.

Scope:
- local Docker runtime skeleton
- PostgreSQL baseline with migrations and required extensions
- API and worker skeletons
- environment and config model
- raw archive schema
- artifact storage contract with local adapter
- canonical ingest command contract
- exact user-facing ingest surface: localhost web UI `Ingest` view supporting paste submission and single-file upload
- lightweight metadata extraction only
- ingest audit and provenance records
- transactional job insertion on successful ingest
- minimal worker able to claim placeholder jobs
- exact operator visibility surface: localhost web UI `Operations` view limited to accepted ingest, failed ingest, pending jobs, and terminal failures
- explicit API and ingest error taxonomy baseline for validation, policy denial, unavailable capability, and internal failure
- initial ingest latency and restart-durability checks against the v1 local profile

Explicit exclusions:
- watched-folder ingest
- MCP ingest
- summarization and fact extraction
- retrieval and search
- canonical editing
- privacy gate UI
- deletion and redaction flows
- backup, restore, export, import
- full navigation application

Exit criteria:
- accepted ingest is acknowledged only after raw archive persistence and required records commit
- accepted raw items survive restart without loss
- queued jobs survive restart without loss
- each accepted ingest has provenance and audit records
- failed ingest does not leave orphaned active records
- operator visibility can distinguish accepted, pending, failed, and terminal states
- the web UI `Ingest` and `Operations` views are sufficient to demonstrate the batch without direct database inspection
- ingest acknowledgment behavior and error taxonomy are stable enough to guide implementation of later MCP and watched-folder surfaces

## Validation model
Each major delivery unit should produce one or more of these evidence types:
- Contract evidence — schemas, state transitions, and error surfaces
- Behavior evidence — scenario coverage for success, retry, failure, and recovery
- Operational evidence — metrics, queue behavior, backup inventories, restore validation
- NFR evidence — performance, degraded mode, deletion-safe recovery, accessibility

## Definition of planning success
The implementation plan is successful when delivery can proceed milestone by milestone without rediscovering sequencing, scope boundaries, evidence requirements, or trust constraints.
