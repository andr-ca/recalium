---
phase: 02-processing-pipeline
plan: "05"
subsystem: backend/processing-pipeline
tags: [embeddings, sentence-transformers, pipeline, PIPE-01, BYOK-08]
dependency_graph:
  requires:
    - 02-03  # derived_memory models (Embedding ORM model)
    - 02-04  # dispatcher with FTS step (stub replaced here)
  provides:
    - embed_text function (asyncio.to_thread wrapping SentenceTransformer)
    - write_embedding / get_existing_embedding service functions
    - dispatcher embedding step (Step 5, replacing plan 04 stub)
  affects:
    - backend/app/worker/dispatcher.py
    - backend/app/domain/derived_memory/service.py
tech_stack:
  added:
    - sentence-transformers 5.3.0 (already in pyproject.toml, imported and used)
    - asyncio.to_thread pattern for CPU-bound inference
  patterns:
    - Module-level lazy singleton for SentenceTransformer model
    - Non-fatal try/except for embedding step in dispatcher
    - BYOK-08 skip pattern: check existing before compute
key_files:
  created: []
  modified:
    - backend/app/domain/derived_memory/service.py
    - backend/app/worker/dispatcher.py
    - backend/tests/domain/test_derived_memory.py
decisions:
  - "Embedding step is non-fatal: local model failure never blocks job completion"
  - "Summary text preferred over raw_text as embed source (more condensed signal)"
  - "Raw text capped at 10,000 chars for embedding when no summary available"
metrics:
  duration_seconds: ~1200
  completed_date: "2026-03-23"
  tasks_completed: 2
  files_modified: 3
  commits: 3
---

# Phase 02 Plan 05: Local Embeddings — Summary

**One-liner:** Local sentence-transformers embeddings (all-MiniLM-L6-v2, 384 dims) wired into dispatcher after FTS step with BYOK-08 skip check and non-fatal error handling.

---

## What Was Built

### Task 1: Embedding functions in derived_memory service

Added to `backend/app/domain/derived_memory/service.py`:

- **`_embed_model` singleton** — `SentenceTransformer | None`, loaded lazily on first call (never at import time)
- **`_get_embed_model()`** — called inside `asyncio.to_thread()` only; safe to block
- **`embed_text(text: str) → list[float]`** — async wrapper; runs `model.encode(text, normalize_embeddings=True)` in `asyncio.to_thread(_encode)`; returns L2-normalized 384-dim float list
- **`write_embedding(session, raw_archive_id, vector, model_name="all-MiniLM-L6-v2") → Embedding`** — creates and commits `Embedding` ORM row with `source_status='active'`; stores `embedding_model` for future model upgrade detection
- **`get_existing_embedding(session, raw_archive_id) → Embedding | None`** — BYOK-08 skip check; returns first active embedding row or None

### Task 2: Dispatcher embedding step (Step 5)

Replaced the plan 04 stub comment in `backend/app/worker/dispatcher.py` with:

```python
# ── Step 5: Embeddings (local sentence-transformers — no API key needed) ──
try:
    from app.domain.derived_memory.service import embed_text, write_embedding, get_existing_embedding
    existing_embedding = await get_existing_embedding(session, job.raw_archive_id)
    if existing_embedding is None:
        embed_source = summary.summary_text if summary else raw_text[:10000]
        vector = await embed_text(embed_source)
        await write_embedding(session, raw_archive_id=job.raw_archive_id, vector=vector)
    else:
        logger.debug("Embedding already exists — skipping (BYOK-08)")
except Exception as e:
    logger.warning("Embedding step failed (non-fatal): %s", e)
```

Step 6 conflict detection stub preserved for plan 06.

---

## Commits

| Hash | Message |
|------|---------|
| `22aab5b` | `test(02-05): add failing embedding tests for embed_text, write_embedding, get_existing_embedding` |
| `f8ab9fb` | `feat(02-05): add embed_text, write_embedding, get_existing_embedding to derived_memory service` |
| `a36f242` | `feat(02-05): wire embedding step into dispatcher after FTS` |

---

## Test Results

```
8 passed in 7.93s   (tests/domain/test_derived_memory.py — all 8 GREEN)
2 passed in 8.90s   (tests/worker/test_dispatcher.py — no regressions)
```

Tests added (RED → GREEN TDD):
- `test_embed_text_returns_384_dim_vector` — PIPE-01 shape check
- `test_embed_text_normalized` — L2 norm ≈ 1.0 within 1% tolerance
- `test_write_embedding_stores_vector` — DB round-trip, model name, source_status
- `test_get_existing_embedding_returns_none_when_absent` — BYOK-08 None case
- `test_get_existing_embedding_returns_embedding_when_present` — BYOK-08 hit case

---

## Deviations from Plan

None — plan executed exactly as written.

---

## Known Stubs

- `# Stub: conflict detection added in 02-06` in `dispatcher.py` Step 6 — intentional, resolved by plan 02-06.

---

## Self-Check: PASSED

Files verified present:
- `backend/app/domain/derived_memory/service.py` — contains `async def embed_text`, `asyncio.to_thread`, `async def write_embedding`, `async def get_existing_embedding`
- `backend/app/worker/dispatcher.py` — contains `await embed_text`, `await write_embedding`, `await get_existing_embedding`

Commits verified:
- `22aab5b` ✓
- `f8ab9fb` ✓
- `a36f242` ✓
