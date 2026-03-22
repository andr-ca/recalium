# Release Slices

Release slices are demoable delivery increments. Each slice is intended to produce a coherent, reviewable capability set rather than a disconnected technical theme.

## Slice A — Durable ingest spine

### Outcome
A user can submit source material and receive acknowledgment only after durable archive persistence and required metadata commit.

### Includes
- WS1-E1 through WS1-E4
- WS2-E1 through WS2-E3
- WS3-E1 and WS3-E2
- WS4-E1 and WS4-E7
- WS8-E1
- WS1-E5

### Excludes
- watched-folder ingest
- MCP ingest
- provider-backed transforms
- retrieval
- deletion flows
- backup and export

### Acceptance evidence
- manual ingest succeeds through one supported local path
- accepted items survive restart without loss
- queue records survive restart without loss
- audit and provenance records exist for accepted ingest
- failed ingest does not leave orphaned active state
- the slice is demoable through the localhost web UI `Ingest` and `Operations` views

## Slice B — Async derivation baseline

### Outcome
Eligible source material produces derived records asynchronously with retry and failure visibility.

### Includes
- WS3-E3 and WS3-E4
- WS4-E2 through WS4-E6
- WS6-E1 and WS6-E2

### Excludes
- final retrieval ranking
- deletion propagation
- backup and restore

### Acceptance evidence
- chunking, summarization, extraction, grouping, and publication run asynchronously
- provider-ineligible content is blocked from provider-backed processing
- retries and terminal failures are visible
- reprocessing is possible for failed or stale jobs
- queue backlog and retry state are visible through supported operator surfaces

## Slice C — Search and review baseline

### Outcome
The user can find memory, inspect provenance, and perform core review actions.

### Includes
- WS5-E1, WS5-E4, WS5-E5, WS5-E6
- WS5-E7
- WS8-E2

### Excludes
- semantic retrieval
- hybrid ranking
- full trust and deletion enforcement

### Acceptance evidence
- keyword retrieval returns traceable results
- provenance and conflict indicators are visible
- facts, canonical, archive, search, review queue, and audit views support their core workflows

## Slice D — Semantic and ranked retrieval

### Outcome
The product supports semantic and hybrid retrieval with deterministic trimming and policy-compliant result assembly.

### Includes
- WS5-E2 and WS5-E3
- WS5-E8
- remaining retrieval-related parts of WS8-E2

### Excludes
- backup and restore
- portability exports
- release hardening

### Acceptance evidence
- semantic retrieval operates on eligible indexed content only
- hybrid merge and ranking behave according to the architecture rules
- strict priority trimming is deterministic and testable

## Slice E — Trust, deletion, and recovery safety

### Outcome
Sensitive-content restrictions and deletion-safe behavior are enforceable across live use and recovery surfaces.

### Includes
- WS2-E4
- WS6-E3 through WS6-E5
- WS7-E1 and WS7-E2

### Excludes
- portability completion
- final release signoff

### Acceptance evidence
- excluded content does not surface through disallowed indexing or embedding paths
- deletion and redaction suppress active visibility immediately
- canonical `source-removed` state works as designed
- scheduled backups and staged restore preserve suppression behavior

## Slice F — Portability and release hardening

### Outcome
The product reaches v1 release readiness within the documented local-first envelope.

### Includes
- WS7-E3 through WS7-E6
- WS6-E6
- WS8-E3 through WS8-E7

### Excludes
- hosted service concerns
- multi-user features

### Acceptance evidence
- JSON export/import works within compatibility rules
- Markdown-plus-assets export is readable outside the product runtime
- warning behavior exists for older backups and exports where required
- restore timing evidence exists against the standard local profile
- core workflows pass keyboard-only and accessibility checks
- performance, degraded-mode, and restore validation evidence is complete
- operator documentation and release checklist are complete
