# Platform v1 Rules and Edge Cases

## Core rules
- Raw archive entries are immutable by default except through deletion or redaction workflows.
- Canonical memory cannot be created automatically; promotion requires explicit user action.
- Derived memory must always remain linked to source provenance.
- Extracted memory and canonical memory must remain distinguishable.
- Conflicting or superseded facts must not be silently treated as equally trustworthy without visible status and source history.
- Retrieval defaults to compact, high-signal output rather than exhaustive dumps.
- Duplicate or overlapping extracted facts must be reviewable together.

## Lifecycle rules
Minimum statuses for facts are:
- active
- disputed
- stale
- archived
- deleted

Memory items may also carry created, updated, last confirmed, effective period, and superseded timestamps where applicable.

## Search and retrieval rules
- Retrieval must support filtering by category, source, project, and time.
- Returned memory must distinguish curated memory from inferred or extracted memory.
- Processed memory should be returned before raw excerpts by default.
- Raw excerpts must remain available as source-backed evidence.
- Retrieval must support minimal, normal, and expanded context modes.
- When canonical memory conflicts with extracted memory, canonical memory must rank first, while conflicting extracted memory may appear only as lower-ranked evidence with explicit conflict labeling and source provenance.
- Retrieval must satisfy context budgets using strict priority trimming in this order: canonical memory, structured facts, summaries, then raw excerpts, stopping as soon as the budget is met.
- MCP `retrieve` responses must include returned items, source links, item type, rank score, provenance metadata, conflict labels where applicable, budget or trimming reason, and retrieval-mode metadata.

## Privacy and control rules
- Users must be able to edit, delete, suppress, or promote memory through supported workflows.
- Users must be able to inspect provenance for any summary, fact, or canonical item.
- Users must be able to inspect machine-client access history at a basic level.
- External provider usage, if any, must be explicit and opt-in.
- If the user enables broader-than-localhost exposure, the exposed interface must require authentication, session handling, and transport protection appropriate to that interface.
- Before any external processing occurs, the system must evaluate sensitivity using both user-declared sensitivity and local rule-based pre-classification.
- If content is unknown or cannot be confidently classified locally, the system must block external processing by default until the user explicitly allows it.
- Provenance views for summaries, facts, and canonical items must expose source item ID, source system, captured timestamp, derivation process, derivation timestamp, session or conversation ID where available, import method, source excerpt or hash, and modifying user or client identity where applicable.
- Audit event views must expose timestamp, client or agent identity, operation type, result count, target or query summary, retrieval mode, success or failure status, source or item IDs touched where applicable, and policy decision reason when access is limited.
- If a raw source item is deleted or redacted, all derived summaries, extracted facts, embeddings, and search visibility linked to that source must be immediately suppressed and marked as source-removed.

## Failure and exception cases
### Ingestion failure
- Invalid or unsupported imports must be visible to the user.
- Failed items must remain reviewable and retryable.
- Raw archive persistence failure must block successful-ingestion status.
- MCP ingestion requests must carry raw content, source metadata, client identity, import method, idempotency key where available, sensitivity hints, project hint, and requested processing mode so the system can validate, deduplicate, and route processing correctly.

### Processing failure
- A failure in summarization, extraction, embedding, or indexing must not destroy raw input.
- Partial processing results must not hide that downstream work failed.
- The UI must expose failed or unprocessed states.
- If provider-backed processing is unavailable, local-only features such as keyword search and basic local processing should remain available where implemented.
- If no local embeddings exist and no external provider is available, semantic and hybrid behavior may rely only on previously cached embedded content; keyword search must remain available.

### Duplicate or contradictory memory
- Highly similar extracted facts must not proliferate without review support.
- Contradictory facts should be linkable or at least separately visible with provenance.
- Canonical memory remains user-editable and may override prior extracted interpretations.

### Deletion and redaction propagation
- Deleting or redacting a raw source item must immediately remove linked derived items from retrieval and search results.
- Linked derived items must retain a user-visible source-removed state for audit and review workflows where retained.
- Canonical memory promoted from a deleted or redacted source may remain, but it must be marked as source-removed and placed into a user review-required state.
- Future backups and exports must exclude deleted or redacted content.
- Existing backups and exports do not need in-place rewriting in v1, but the UI must flag them as potentially containing deleted or redacted content.

### Audit gaps
- If client identity is unavailable, access events should still capture timestamp and operation metadata when possible.
- Lack of perfect identity information must not block basic audit visibility.
