# Storage and Indexing

## Baseline choices
- Primary database: PostgreSQL
- Keyword search: PostgreSQL full-text search
- Semantic search: `pgvector`
- Hybrid search: application-layer ranking over FTS and vector results

## Core storage areas
### Raw archive
Stores immutable ingested sources and ingestion metadata.

### Artifact storage metadata
Stores authoritative metadata for file/blob-backed artifacts, while raw bytes live in the artifact storage adapter.

### Derived artifacts
Stores summaries, chunks, extracted facts, embedding references, and indexing metadata.

### Canonical memory
Stores user-approved durable memory with higher retrieval priority.

### Audit and provenance
Stores access events, modification events, source linkage, and derivation metadata.

## Separation rules
- Raw archive must remain distinct from derived layers.
- Canonical memory must remain distinct from extracted facts.
- Deletion/redaction state must be representable without destroying traceability.
- Future-service compatibility should be preserved by keeping policy and ownership fields separable from current single-user assumptions.

See [artifact-storage.md](artifact-storage.md) and [deletion-and-tombstones.md](deletion-and-tombstones.md) for the authoritative artifact and removal models.

## Suggested schema groups
- ingestion
- archive
- memory
- retrieval
- audit
- operations

## Indexing strategy
- FTS indexes on raw text, summary text, and searchable fact text
- vector indexes on searchable chunks and selected derived artifacts
- metadata filters on category, source system, project, timestamps, lifecycle status, and canonical/extracted distinction
- configured category/source exclusion rules must be applied before embedding and before search-index publication so excluded content does not become searchable through prohibited paths

## Performance reference
Indexing and query strategy must support the published $P95$ requirements. See [performance-and-operability.md](performance-and-operability.md).
