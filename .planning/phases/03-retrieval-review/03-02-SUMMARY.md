# 03-02 Summary: RED-State Test Scaffold for Phase 3

## Status: DONE

## What Was Implemented

### conftest.py additions
- Added top-level `import importlib` to module imports
- Added Phase 3 guarded imports for `app.domain.canonical_memory.models` and `app.domain.review_queue.models`
- Added `db_session_phase3` fixture (same rollback semantics as `db_session_phase2`)

### New test files (5 files, all RED/skipped until implementation plans run)

| File | Requirements covered | Skips on missing |
|------|---------------------|------------------|
| `tests/domain/test_retrieval.py` | SRCH-01/02/03/04/06, MCP-01/03 | `app.domain.retrieval.service` |
| `tests/domain/test_canonical_memory.py` | CANM-01/02/03/04, WEBUI-05 | `app.domain.canonical_memory.service` |
| `tests/domain/test_review_queue.py` | CANM-05 | `app.domain.review_queue.service` |
| `tests/api/test_search_api.py` | SRCH-01/03/05, MCP-03/04 | `app.domain.retrieval.service` |
| `tests/api/test_canonical_api.py` | CANM-01/03/04 | `app.domain.canonical_memory.service` |

## Verification

```
collected 0 items / 5 skipped  (all skip gracefully via pytest.importorskip)
All files compile OK (py_compile)
```

## Plans That Will Turn These GREEN

- **03-03**: retrieval service → `test_retrieval.py`
- **03-04**: canonical_memory service → `test_canonical_memory.py`
- **03-05**: review_queue service → `test_review_queue.py`
- **03-06**: API routes → `test_search_api.py`, `test_canonical_api.py`
