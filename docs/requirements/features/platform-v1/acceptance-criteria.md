# Platform v1 Acceptance Criteria

## Product-level acceptance criteria
1. Given a user has prior AI conversations, when the user imports them by paste or JSON/Markdown file upload, then Recalium stores the raw content with source metadata and shows the item in the review UI.
2. Given an ingested item exists, when processing completes, then the system exposes linked summaries, extracted facts, and searchable representations without losing the raw archive.
3. Given extracted facts are available, when the user reviews them, then the user can inspect provenance, edit, delete, mark disputed or stale, and promote selected facts to canonical memory.
4. Given canonical memory exists, when retrieval runs for a relevant query or task, then canonical memory is clearly distinguished and prioritized over unconfirmed extracted memory.
5. Given a user searches by keyword, semantic query, or hybrid mode, when results are returned, then results include relevant ranked items with source links and filter support.
6. Given a retrieval request includes a bounded context budget, when results are assembled, then the system returns the smallest useful ranked set for the selected retrieval mode.
7. Given a machine client or MCP-compatible agent retrieves memory, when the operation completes, then the access event is recorded with available client identity, timestamp, and operation metadata.
8. Given a derived memory item is incorrect, when the user corrects or deletes it, then the updated state is visible in future review and retrieval behavior.
9. Given duplicate or overlapping extracted facts exist, when the user opens the review surface, then similar facts are grouped or flagged for manageable cleanup.
10. Given the user needs trustworthy review, when viewing any summary, fact, or canonical memory item, then the user can navigate to its source provenance.
11. Given external providers are not configured during first-run setup, when the user starts Recalium, then the system remains usable for local storage, browsing, keyword search, and supported basic local processing.
12. Given external providers are configured, when content is categorized as personal profile or relationships, then external processing is blocked by default unless the user explicitly overrides that protection.
13. Given content is evaluated before any external processing, when user-declared sensitivity or local rule-based pre-classification marks it as sensitive, then external processing is blocked unless the user explicitly overrides that protection.
14. Given content is unknown or not confidently classified before an external-processing step, when the system evaluates that content, then it blocks external processing by default until the user explicitly allows it.
15. Given a raw source item is deleted or redacted, when linked derived summaries, facts, embeddings, or search entries exist, then those linked derived artifacts are immediately suppressed from retrieval and search and marked as source-removed.
16. Given canonical memory was promoted from a source that is later deleted or redacted, when the source-removal event is processed, then the canonical entry remains available only with a source-removed marker and a required-review state.
17. Given source data is deleted or redacted, when future backups or exports are created, then the deleted or redacted data is excluded, and previously created backups or exports are flagged as potentially still containing that data.
18. Given no embeddings are available locally and no external provider is configured, when the user runs search, then keyword search remains available and semantic results may only come from previously embedded cached content.
19. Given canonical memory conflicts with extracted memory during retrieval, when results are returned, then canonical memory appears first and conflicting extracted memory appears only as lower-ranked evidence with explicit conflict labeling.
20. Given a retrieval request has a constrained context budget, when the result set is trimmed, then trimming occurs in strict priority order: canonical memory, structured facts, summaries, then raw excerpts, and stops as soon as the budget is met.
21. Given the user inspects provenance for a summary, fact, or canonical item, when provenance is shown, then it includes source item ID, source system, captured timestamp, derivation process, derivation timestamp, session or conversation ID where available, import method, source excerpt or hash, and modifying user or client identity where applicable.
22. Given an audit access event is recorded, when the user inspects it, then it includes timestamp, client or agent identity, operation type, result count, target or query summary, retrieval mode, success or failure status, source or item IDs touched where applicable, and policy decision reason when access is limited.
23. Given an MCP-compatible client performs a `retrieve` request, when the response is returned, then it includes returned items, source links, item type, rank score, provenance metadata, conflict labels where applicable, budget or trimming reason, and retrieval-mode metadata.
24. Given an MCP-compatible client performs an ingestion request, when the request is accepted, then it includes raw content, source metadata, client identity, import method, idempotency key where available, sensitivity hints, project hint, and requested processing mode.
25. Given the user enables broader-than-localhost exposure for a UI, API, or MCP interface, when that interface becomes reachable beyond localhost, then authentication, session handling, and transport protection are required for that exposed interface.
26. Given scheduled backups are enabled, when the system runs under normal local conditions, then it creates daily backups, retains 30 days of successful backups, and allows restoring any successful backup within 15 minutes.
27. Given a successful restore is performed from a valid backup, when restore completes, then raw archive items, summaries, structured facts, canonical memory, provenance metadata, retained audit events, and dataset-required configuration are available in the restored system state.
28. Given the user uses core workflows by keyboard only, when navigating ingest, search, fact review, canonical edit, review queue, or restore flows, then the workflow remains operable without requiring a mouse.
29. Given the user exports a human-readable archive, when the zip is opened, then it contains a top-level index, type-based folders, and manifest metadata that preserves provenance and source/session links.

## Cross-cutting NFR acceptance criteria
1. Given a paste import or file upload up to 5 MB under normal local conditions, when ingestion is acknowledged, then acknowledgement occurs within $P95 \le 1\text{ s}$.
2. Given a personal-scale dataset up to 100k stored items, when search or retrieval runs, then response time is within $P95 \le 2\text{ s}$.
3. Given an ingest has been acknowledged, when the container restarts or the host reboots with persisted Docker volumes intact, then the raw archive item remains durable and retrievable.
4. Given machine-client access events are recorded, when the user inspects audit history, then at least 90 days of access-event history are available.

## Scope guard acceptance criteria
1. v1 does not require automated vendor-specific connectors.
2. v1 does not require multi-user support.
3. v1 does not require advanced per-agent permissions.
4. v1 does not require graph visualization.
5. v1 does not require automated memory decay logic beyond manual status handling.
