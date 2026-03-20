# Retrieval and Ranking

## Search modes
- keyword: PostgreSQL FTS
- semantic: `pgvector`
- hybrid: application-layer merge and rerank

## Retrieval precedence
1. canonical memory
2. structured facts
3. summaries
4. raw excerpts

## Conflict behavior
- canonical memory outranks conflicting extracted memory
- conflicting extracted memory may appear only as lower-ranked evidence
- conflict labeling and provenance are required when both appear

## Context budgeting
Trimming order is strict:
1. canonical memory
2. facts
3. summaries
4. raw excerpts

Stop adding items as soon as the budget is met.

## Degraded mode
If no embeddings are available locally and no external provider is configured:
- keyword search remains available
- semantic behavior may only use previously cached embedded content
- provider-dependent capabilities must surface unavailable or pending state clearly

## Filters
Retrieval and search must support filtering by:
- category
- source
- project
- time
- lifecycle status
- canonical vs extracted

## Performance reference
Candidate generation, ranking, and trimming should be evaluated against the benchmark profile defined in [performance-and-operability.md](performance-and-operability.md).
