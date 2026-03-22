# Processing Pipeline

## Ingestion path
### Synchronous path
Must complete before success acknowledgement:
1. validate request or import payload
2. capture source metadata and ingestion metadata
3. persist raw archive record
4. extract lightweight metadata for attribution and pipeline tracking
5. enqueue downstream processing work

### Asynchronous path
Runs through background jobs:
1. chunking
2. summarization
3. classification
4. fact extraction
5. overlap or duplicate detection
6. embeddings
7. FTS or retrieval indexing
8. review-queue materialization

## Failure model
- raw archive persistence failure blocks success
- downstream failures are visible and retryable
- bounded automatic retries occur before terminal failed state
- reprocessing must be supported after pipeline or logic changes
- job state must be durable enough that queued work is not lost across container restart when persisted storage is intact

## Queue architecture decision
v1 uses a PostgreSQL-backed durable job queue. See [queue-and-jobs.md](queue-and-jobs.md).

## Privacy gate
Before any external-provider call:
1. read user-declared sensitivity
2. run local rule-based pre-classification
3. if sensitive or low-confidence/unknown, block external processing unless explicitly overridden
4. if category/source exclusion rules disable embedding or indexing for the item, skip those downstream steps and record the policy decision in pipeline metadata

## Extraction quality requirements
Every extracted fact produced by the async pipeline must include:
- `source_span`: the exact quoted text from the source that the fact was derived from. Facts with no attributable span are marked `low` confidence and must not be auto-promoted.
- `confidence_tier`: `high`, `medium`, or `low`. Determined by extraction model output or heuristic signal.
- `derivation_method`: identifier for the extraction method (e.g., `llm_extraction`, `rule_based`).
- `derivation_model`: the model or method version used (e.g., `gpt-4o`, `local_rules_v1`).

These fields are required. A fact record without a `source_span` and `confidence_tier` is incomplete and must not be published to the search index or retrieval surface.

## Idempotency
MCP ingestion should honor an idempotency key where available to avoid duplicate ingestion caused by retries.

## Module ownership reference
See [component-boundaries.md](component-boundaries.md) for ingest, jobs, archive, and worker ownership boundaries.

## Operability reference
See [performance-and-operability.md](performance-and-operability.md) for queue durability, backpressure, and benchmark expectations.
