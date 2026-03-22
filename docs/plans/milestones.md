# Milestones

Each milestone is a control gate. A milestone is complete only when its scope is delivered and its required evidence exists.

## Milestone 1 — Foundation proven

### Goal
Prove that Recalium can run locally with durable archive, stable configuration, repeatable schema setup, and recoverable queue foundations.

### Included scope
- WS1-E1 through WS1-E4
- WS2-E1 through WS2-E3
- WS3-E1 and WS3-E2
- WS4-E1 and WS4-E7
- WS8-E1
- WS1-E5

### Non-goals
- provider-backed transforms
- retrieval
- full UI beyond initial `Ingest` and `Operations` views
- portability
- deletion-complete workflows

### Required evidence
- clean local bootstrap evidence
- repeatable migration evidence
- accepted-ingest durability evidence across restart
- queue claim and recovery evidence
- config validation evidence
- ingest latency baseline evidence
- UI demonstration evidence for the first batch

### Exit criteria
- local runtime starts with required services and persistent storage
- database migrations apply cleanly on first boot and re-run safely
- accepted ingest is acknowledged only after durable commit of raw archive and required metadata
- accepted ingest survives restart without loss
- queued work survives restart without loss
- audit and provenance schema are active for accepted ingest
- the localhost UI provides working `Ingest` and `Operations` views for the first batch

## Milestone 2 — Ingest and derived pipeline proven

### Goal
Prove that all required v1 ingest paths converge on one contract and can feed a recoverable async pipeline.

### Included scope
- WS3-E3 and WS3-E4
- WS4-E2 through WS4-E6
- WS6-E1 and WS6-E2

### Non-goals
- final retrieval ranking
- final deletion behavior
- release hardening

### Required evidence
- ingest contract evidence for manual, MCP, and watched-folder paths
- retry and terminal-failure evidence
- provider eligibility enforcement evidence
- reprocessing evidence
- searchable publication evidence for eligible content
- queue backlog and retry observability evidence

### Exit criteria
- paste, file upload, MCP ingest, and watched-folder ingest all target the canonical ingest contract
- chunking, summarization, fact extraction, grouping, and publication occur asynchronously
- retries and terminal failures are visible and recoverable
- provider-ineligible content is blocked from provider-backed processing
- eligible content can be published into FTS and embedding-backed structures

## Milestone 3 — Retrieval and review usable

### Goal
Prove that users can retrieve, review, and curate memory with provenance visibility.

### Included scope
- WS5-E1 through WS5-E6
- WS5-E7
- WS5-E8
- WS8-E2

### Non-goals
- backup and restore completion
- release hardening completion

### Required evidence
- keyword retrieval evidence
- semantic and hybrid retrieval evidence
- strict priority trimming evidence
- provenance and conflict visibility evidence
- facts, canonical, and review queue workflow evidence
- retrieval latency benchmark evidence

### Exit criteria
- keyword retrieval is usable on indexed items
- semantic and hybrid retrieval produce policy-compliant results
- strict priority trimming behaves deterministically
- provenance and conflict signals are visible in retrieval and review flows
- core views for archive, facts, canonical, search, review queue, and audit are usable locally

## Milestone 4 — Trust and deletion safety proven

### Goal
Prove that sensitive-content controls and deletion-safe behavior operate correctly across live workflows.

### Included scope
- WS2-E4
- WS6-E3 through WS6-E5

### Non-goals
- full restore and export readiness
- release hardening signoff

### Required evidence
- exclusion-from-indexing evidence
- deletion and redaction suppression evidence
- canonical `source-removed` transition evidence

### Exit criteria
- excluded content does not appear through disallowed indexing or embedding paths
- deleted or redacted source material is suppressed from active retrieval and derived-memory surfaces
- canonical entries dependent on removed sources become review-required

## Milestone 5 — Recoverability and release readiness proven

### Goal
Prove that the product can be recovered, exported, validated, and locally released within the documented v1 envelope.

### Included scope
- WS7-E1 through WS7-E6
- WS6-E6
- WS8-E3 through WS8-E7

### Non-goals
- hosted service operations
- multi-user support
- broader browser support than documented v1 target

### Required evidence
- scheduled backup and retention evidence
- staged restore and cutover evidence
- export and import fidelity evidence
- performance benchmark evidence
- degraded-mode evidence
- keyboard-only and accessibility evidence
- release checklist completion evidence
- deleted-data warning evidence for older artifacts

### Exit criteria
- scheduled backups run and retention is enforced
- restore completes in staged mode and cuts over only after validation passes
- JSON export/import and Markdown-plus-assets export behave within the documented contract
- ingest, retrieval, and restore targets are validated against the documented v1 expectations
- warning behavior exists for older backups and exports that may still contain deleted data
- core workflows satisfy keyboard-only and accessibility expectations within the supported browser target
- release checklist and operator documentation are complete enough to support local deployment and recovery
