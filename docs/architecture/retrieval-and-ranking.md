# Retrieval and Ranking

## Search modes
- keyword: PostgreSQL full-text search (`tsvector` / `tsquery`)
- semantic: `pgvector` cosine similarity
- hybrid: Reciprocal Rank Fusion (RRF) — see algorithm below

## Hybrid ranking algorithm
v1 uses Reciprocal Rank Fusion as the merge strategy for hybrid retrieval.

For each candidate item `d` returned by search mode `m` at rank position `r`:

```
RRF_score(d) = Σ_m  1 / (k + r_m(d))
```

Where:
- `k = 60` (standard constant; dampens the impact of top rank positions)
- `r_m(d)` is the 1-based rank of item `d` in mode `m` (items not present in a mode are excluded from that mode's term)
- Summation is over all search modes that returned the item

Candidate pool per mode: top 50 results before merging. Final merged list: top 20 after RRF scoring.

Minimum score threshold: any item with an RRF score below `1 / (k + 25) ≈ 0.012` is excluded from the result set regardless of pool size. This prevents low-quality noise from appearing in results.

## Reranking (optional)
If a cross-encoder reranker is available (configurable), apply it to the top 20 RRF results before budget trimming. Reranking is optional and degrades gracefully: if no reranker is configured, RRF score order is used directly.

## Retrieval precedence
Before RRF scoring is applied, results are segmented by memory layer. Budget trimming respects this order strictly:

1. canonical memory
2. structured facts
3. summaries
4. raw excerpts

Within each layer, items are ordered by RRF score descending.

## Conflict behavior
- canonical memory outranks conflicting extracted memory
- conflicting extracted memory may appear only as lower-ranked evidence
- conflict labeling and provenance are required when both appear in the same response

## Context budgeting
Budget trimming order is strict — same as retrieval precedence above:

1. canonical memory (add all that fit)
2. facts (add until budget met)
3. summaries (add until budget met)
4. raw excerpts (add until budget met)

Stop adding items as soon as the token/character budget is met. Never truncate an item mid-content; skip it entirely if it does not fit.

## Context assembly format
The response returned to MCP clients and the UI must follow this structure:

```json
{
  "query": "<original query>",
  "retrieval_mode": "hybrid | keyword | semantic",
  "budget_used": 1240,
  "budget_limit": 2000,
  "trimming_reason": "budget_met | result_exhausted",
  "items": [
    {
      "id": "<item_id>",
      "type": "canonical | fact | summary | excerpt",
      "content": "<text>",
      "score": 0.042,
      "source_id": "<raw_archive_id>",
      "source_system": "<e.g. claude, chatgpt, manual>",
      "captured_at": "<ISO8601>",
      "conflict_label": null,
      "provenance": {
        "derivation_method": "<e.g. llm_extraction, user_canonical>",
        "derivation_model": "<e.g. gpt-4o>",
        "source_excerpt": "<quoted span the fact was derived from>"
      }
    }
  ]
}
```

## Caching
To meet the P95 ≤ 2s retrieval target, an in-process LRU cache is maintained for recent retrieval results:

- Cache key: `hash(query_text + filters + retrieval_mode + budget)`
- TTL: 60 seconds
- Max size: 256 entries
- Cache is invalidated for a query key when new items are published into the search index
- Cache must not serve results across a policy change (sensitivity overrides or deletion events must flush relevant cache entries)

## Degraded mode
If no embeddings are available locally and no external provider is configured:
- keyword search remains fully available
- semantic search uses only previously cached embedded content
- hybrid mode falls back to keyword-only automatically with a visible status flag
- provider-dependent capabilities must surface `unavailable` or `pending` state, not silent failure

## Filters
Retrieval and search must support filtering by:
- category
- source system
- project
- time range
- lifecycle status
- canonical vs extracted

## Performance reference
Candidate generation, RRF scoring, and budget trimming must be evaluated against the benchmark profile in [performance-and-operability.md](performance-and-operability.md).
