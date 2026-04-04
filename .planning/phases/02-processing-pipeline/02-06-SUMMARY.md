---
phase: "02"
plan: "06"
subsystem: conflict-detection
tags: [pgvector, duplicate-detection, embeddings, pipeline]
dependency-graph:
  requires: [02-05]
  provides: [conflict-detection-module, dispatcher-step6]
  affects: [dispatcher-pipeline, derived-memory]
tech-stack:
  added: []
  patterns: [pgvector-cosine-distance, non-fatal-try-except, cascade-contract-filtering]
key-files:
  created:
    - backend/app/domain/conflict_detection.py
  modified:
    - backend/app/worker/dispatcher.py
    - backend/tests/domain/test_conflict_detection.py
decisions:
  - "create_conflict_group accepts optional fact_ids parameter for API compatibility with test stubs — parameter is stored when schema supports a linking table in future plans"
  - "Conflict detection wrapped in try/except — failure is non-fatal, job always completes"
metrics:
  duration: "126s"
  completed: "2026-03-23T13:26:22Z"
  tasks_completed: 2
  files_changed: 3
---

# Phase 02 Plan 06: Conflict/Duplicate Detection Summary

**One-liner:** pgvector cosine-distance duplicate detection (threshold 0.15) wired non-fatally into dispatcher Step 6 after embeddings.

---

## What Was Built

### Task 1 — `conflict_detection.py` module

Created `backend/app/domain/conflict_detection.py` with:

- **`DUPLICATE_DISTANCE_THRESHOLD = 0.15`** — cosine distance threshold for flagging duplicates
- **`find_duplicate_candidates(session, embedding, exclude_id)`** — executes pgvector `<=>` cosine distance SQL query against the `embeddings` table; filters `source_status = 'active'` (CASCADE CONTRACT); excludes the source embedding by ID; returns up to 10 UUIDs ordered by distance
- **`create_conflict_group(session, group_type, fact_ids=None)`** — creates a `ConflictGroup` row, commits, refreshes and returns it; `fact_ids` accepted for API compatibility with existing test stubs

### Task 2 — Wire Step 6 in `dispatcher.py`

Replaced stub comment in `dispatch_job()` Step 6 with real implementation:
- Loads current embedding via `get_existing_embedding()`
- Calls `find_duplicate_candidates()` if embedding exists
- Creates a `ConflictGroup` if any near-duplicate candidates found
- Entire block wrapped in `try/except Exception` — failure is **non-fatal** (logs warning, job still proceeds to `complete_job()`)
- `complete_job()` remains AFTER the conflict detection block

---

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1    | f946758 | feat(02-06): implement conflict/duplicate detection module |
| 2    | 5d18b14 | feat(02-06): wire conflict detection into dispatcher Step 6 |

---

## Verification Results

All 3 acceptance criteria passed:

```
✅ python -c "from app.domain.conflict_detection import find_duplicate_candidates, create_conflict_group, DUPLICATE_DISTANCE_THRESHOLD; print('OK')"
   → OK

✅ python -c "...assert 'find_duplicate_candidates' in src; print('wired OK')"
   → wired OK

✅ pytest tests/domain/test_conflict_detection.py -x -q
   → 3 passed in 0.40s
```

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed FK violation in `test_duplicate_detected_by_cosine_similarity`**
- **Found during:** Task 1 test run
- **Issue:** Test stub inserted an `Embedding` row with a random `raw_archive_id` that had no corresponding `raw_archive` record, violating the FK constraint `embeddings_raw_archive_id_fkey`
- **Fix:** Added `_make_archive_item()` helper function (following the pattern established in `test_derived_memory.py`) that inserts a minimal `RawArchiveItem` first; updated test to use it
- **Files modified:** `backend/tests/domain/test_conflict_detection.py`
- **Commit:** f946758

**2. [Rule 2 - API Compatibility] `create_conflict_group` accepts `fact_ids` parameter**
- **Found during:** Task 1 implementation — test stub calls `create_conflict_group(fact_ids=..., group_type=...)`
- **Issue:** Plan spec showed a 2-argument signature but the test requires `fact_ids`
- **Fix:** Added `fact_ids: Sequence[uuid.UUID] | None = None` optional parameter with comment noting it's accepted for API compatibility; no linking table exists yet in the schema
- **Files modified:** `backend/app/domain/conflict_detection.py`

---

## Security Notes

- All SQL queries filter `source_status = 'active'` (CASCADE CONTRACT)
- No `SentenceTransformer` import in `conflict_detection.py` — embeddings passed in as pre-computed vectors
- No API keys in this module

---

## Self-Check

### Files Exist
- `backend/app/domain/conflict_detection.py` ✅
- `backend/app/worker/dispatcher.py` (modified) ✅
- `backend/tests/domain/test_conflict_detection.py` (modified) ✅

### Commits Exist
- f946758 ✅
- 5d18b14 ✅

## Self-Check: PASSED
