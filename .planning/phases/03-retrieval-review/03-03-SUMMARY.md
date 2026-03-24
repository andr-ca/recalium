# 03-03 Summary: Core Retrieval Service

## Status: DONE

## What Was Implemented

Created `backend/app/domain/retrieval/` with:

- `__init__.py` — domain package marker
- `service.py` — full retrieval service implementation

### Key components in `service.py`:

**Dataclasses:**
- `RetrievalFilters` — optional filters (category, source_system, time range, canonical_only)
- `RetrievalRequest` — query, mode, budget, filters, actor, limit
- `RetrievalItem` — id, type, content, score, source_id, source_system, captured_at, conflict_label, provenance
- `RetrievalResponse` — query, retrieval_mode, budget_used, budget_limit, trimming_reason, items, degraded_mode

**Functions:**
- `rrf_score(rank, k)` — Reciprocal Rank Fusion formula: `1 / (k + rank)`
- `apply_budget_trimming(items, budget)` — strict priority (canonical → fact → summary → excerpt), no mid-item truncation
- `retrieve(session, req)` — main async entry point; dispatches to keyword/semantic/hybrid paths, emits AuditEvent, uses TTL cache
- `invalidate_cache()` — clears the 256-entry / 60s TTL LRU cache

**Constants:**
- `RRF_K = 60`
- `RRF_MIN_THRESHOLD = 1 / (60 + 25)` ≈ 0.01176
- `RRF_CANDIDATES_PER_MODE = 50`
- `RRF_FINAL_TOP_N = 20`

**Modes:**
- `keyword` — PostgreSQL FTS via `websearch_to_tsquery('english', query)` on `fts_entries` and `canonical_memory`
- `semantic` — pgvector cosine similarity on `embeddings`; degrades gracefully when sentence-transformers unavailable
- `hybrid` — RRF merge of keyword + semantic; falls back to keyword-only when no embeddings (sets `degraded_mode=True`)

## Dependency Added

`cachetools>=5.0,<6` added to `pyproject.toml` and installed (v5.5.2).

## Test Results

```
11 passed in 0.49s
```

All 11 tests in `tests/domain/test_retrieval.py` pass, covering SRCH-01, SRCH-02, SRCH-03, SRCH-04, SRCH-06, MCP-01, MCP-03.

## Files Changed

- `backend/pyproject.toml` — added `cachetools>=5.0,<6`
- `backend/app/domain/retrieval/__init__.py` — new
- `backend/app/domain/retrieval/service.py` — new
