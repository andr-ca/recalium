# Platform v1 Workflows

## 1. Manual conversation import
1. The user opens the ingestion view.
2. The user pastes text or uploads a supported file.
3. The system validates the payload and records basic source metadata.
4. The system persists the raw archive entry before downstream processing.
5. The system performs lightweight metadata extraction needed for attribution and pipeline tracking.
6. The system acknowledges ingestion to the user.
7. The system runs or schedules heavier asynchronous processing steps.
8. The user can inspect processing state and any failures.

## 2. Low-friction local import
1. A watched import folder receives a supported file.
2. The system detects the new file.
3. The system records source metadata and ingests the raw content.
4. The UI shows detection, status, and any errors.
5. The user can retry or inspect derived outputs.

## 3. Processing and derivation
1. The system chunks the raw source where needed.
2. The system creates one or more summaries.
3. The system classifies or tags content.
4. The system extracts candidate facts.
5. The system generates embeddings where configured.
6. The system indexes searchable units.
7. The system flags likely duplicates or overlaps among extracted facts.
8. The user can reprocess content later when logic changes.

## 4. Fact review and curation
1. The user browses extracted facts.
2. The user filters by category, status, source, or project.
3. The user inspects provenance and linked source content.
4. The user edits, deletes, disputes, or marks facts stale.
5. The user promotes selected facts into canonical memory.
6. The system preserves the distinction between extracted and canonical memory.

## 5. Retrieval for future work
1. A user or machine client submits a query, prompt, task, project identifier, profile request, or time-bounded request.
2. The system applies filters and retrieval mode selection.
3. The system ranks canonical memory, facts, summaries, and supporting excerpts.
4. The system returns the smallest useful source-backed set within the configured context budget.
5. The system records an access event for machine-client activity where available.

## 6. Duplicate and overlap cleanup
1. The user opens a dedicated duplicate or overlap review queue.
2. The system groups likely related extracted facts.
3. The user compares provenance and source text.
4. The user keeps separate items, removes redundant variants, or conceptually merges through the review workflow where supported.
5. Canonical memory remains cleaner and more stable than extracted memory.
