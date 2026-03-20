# Risks and Dependencies

## Dependency register

### Hard dependencies
- approved requirements package
- approved architecture package
- PostgreSQL with required extensions including `pgvector`
- local artifact storage adapter and persistence path

### Architectural dependencies
- policy gate must exist before any provider-backed processing is enabled
- provenance and audit structures must exist before ingest and retrieval are treated as complete
- tombstone and deletion-ledger behavior must exist before deletion-safe claims are made
- embedding and FTS publication must exist before semantic and hybrid retrieval are treated as complete
- restore validation must verify suppression semantics before restore is treated as complete

### Sequencing dependencies
- runtime and migrations precede all feature delivery
- archive and artifact storage precede all ingest closure
- canonical ingest contract precedes manual, MCP, and watched-folder surfaces
- queue recovery precedes derived-memory pipeline closure
- keyword retrieval should land before semantic and hybrid retrieval
- stable archive, provenance, and deletion semantics should land before portability completion
- initial `Ingest` and `Operations` web UI surfaces should land with the first execution batch, while memory workflow views can land later
- API and MCP contract versioning and stable error taxonomy should land before non-web ingest and retrieval surfaces expand

### Soft dependencies
- benchmark dataset availability for early performance validation
- representative local hardware profile for restore timing validation
- stable UI shell routes before full workflow views
- at least one provider adapter strategy for summarization, extraction, and embeddings before provider-backed pipeline scope begins in Slice B / Milestone 2

## Risk register

### Risk 1 — Queue durability failure
- Trigger: accepted ingest does not survive restart or job claims duplicate or disappear after worker failure.
- Impact: core product trust collapses and all downstream features become unreliable.
- Mitigation: close durable ingest spine first, validate restart and recovery before adding pipeline breadth.
- Earliest detection point: Slice A.

### Risk 2 — Provider coupling drift
- Trigger: pipeline logic depends directly on one provider API or response shape.
- Impact: policy enforcement weakens and future provider substitution becomes expensive.
- Mitigation: keep provider calls behind dedicated adapters and policy checks; treat provider selection as infrastructure, not domain logic.
- Earliest detection point: Slice B.

### Risk 3 — Sensitive-content policy bypass
- Trigger: unknown or sensitive content reaches provider-backed summarization, extraction, or embeddings.
- Impact: privacy guarantees are violated.
- Mitigation: land sensitivity declaration, local pre-classification, and provider eligibility gate before provider-backed transforms are enabled.
- Earliest detection point: Slice B.

### Risk 4 — Deletion-safe behavior is incomplete
- Trigger: deleted or redacted content remains retrievable, reappears after restore, or remains silently trusted in canonical memory.
- Impact: trust and correctness are undermined.
- Mitigation: implement tombstone foundation before deletion completion, validate suppression in live retrieval and restore flows, enforce `source-removed` review state.
- Earliest detection point: Slice E.

### Risk 5 — UI scope creep
- Trigger: non-essential UX work expands before core review and operations surfaces are usable.
- Impact: schedule slips without improving release readiness.
- Mitigation: restrict UI scope to architecture-required sections and core workflows; defer polish and non-core extensions.
- Earliest detection point: Slice C.

### Risk 6 — Performance surprises arrive too late
- Trigger: retrieval latency, ingest latency, or restore timing are measured only near release.
- Impact: major redesign may be required late in delivery.
- Mitigation: create benchmark harnesses early, validate ingest in Slice A, retrieval in Slices C and D, restore in Slice E/F.
- Earliest detection point: Slice A.

### Risk 7 — Portability and operational backup are conflated
- Trigger: the team treats backup/restore as equivalent to export/import.
- Impact: recovery guarantees and portability guarantees become ambiguous or incorrect.
- Mitigation: maintain separate epics, contracts, evidence, and operator messaging for backup/restore versus export/import.
- Earliest detection point: Slice E.

## Control rules
- Do not start semantic or hybrid retrieval closure before searchable publication is stable.
- Do not mark deletion complete before suppression is validated in retrieval and review surfaces.
- Do not mark restore complete before staged validation and suppression re-application are proven.
- Do not mark portability complete until JSON export/import and Markdown-plus-assets export both meet their defined contracts.
- Do not mark release-ready until performance, degraded mode, keyboard-only, and accessibility evidence is complete.
- Do not expand MCP or external API usage claims before contract versioning and stable error taxonomy are locked for the v1 line.
