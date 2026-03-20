# Platform v1 Workflows

## 0. First-run setup and cold-start
1. The user starts Recalium for the first time.
2. The system presents a setup wizard with sequential steps.
3. Step 1 — Provider configuration (BYOK):
   a. The system explains the BYOK model: "Recalium uses AI providers for summarization, extraction, and semantic search. You provide your own API keys. Processing costs appear on your provider bill."
   b. The system shows supported providers with links to their key creation pages.
   c. The user enters API keys for: embeddings provider, completion provider.
   d. The system validates each key with a lightweight test call and reports success or failure.
   e. The user may skip this step. The system clearly states: keyword search only, no extraction or summarization until providers are configured.
4. Step 2 — Import prompt:
   a. The system presents "Import your AI history" as the primary call to action.
   b. The system shows the supported format list and a file picker.
   c. The user selects an export file.
5. Step 3 — Import preview:
   a. The system validates the file format and displays: conversation count, estimated token volume, estimated processing cost (if providers configured), trivial-conversation filter option, and distribution by length and date.
   b. The user adjusts filters (e.g., skip conversations shorter than 3 turns).
   c. The user confirms the import (with cost estimate visible if providers are configured).
6. The system begins synchronous archive persistence and enqueues async processing.
7. The system shows a progress view with: archived count, processing count, completed count, estimated time remaining.
8. When the first batch of items is searchable, the system prompts: "Try searching your memory" with a pre-filled example query based on conversation topics detected during import.
9. The user runs their first search and sees results from their own history.
10. The setup wizard marks onboarding complete.

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
