# Task 01-08: Integration Tests — Summary

## Status: COMPLETE

All backend and frontend tests pass (18 + 5).

---

## Test Files Created (prior tasks)

| File | Requirements Covered |
|------|---------------------|
| `backend/tests/conftest.py` | Shared fixtures: engine, db_session, client |
| `backend/tests/test_ingest.py` | INGT-01 (paste ingest), INGT-02 (file upload), INGT-03 (latency) |
| `backend/tests/test_archive.py` | INGT-03 (archive listing, pagination, soft-delete filter) |
| `backend/tests/test_settings.py` | BYOK-02 (status endpoint), BYOK-03 (validate), BYOK-04 (key not in DB), BYOK-05 (degraded mode) |
| `frontend/src/tests/LeftNav.test.tsx` | WEBUI-01 (nav sidebar items, order, disabled states) |

---

## Final Test Counts

- **Backend**: 18 passed, 0 failed, 0 skipped (`uv run --no-sync pytest tests/ -v`)
- **Frontend**: 5 passed, 0 failed, 0 skipped (`pnpm test --run`)
- **Security gate** (`test_key_not_in_db`): PASSED

---

## Intentionally Skipped Tests

None. All 18 backend and 5 frontend tests run and pass.

---

## Fixes Applied in This Task

### Root Cause: asyncio event-loop mismatch in conftest.py

**Problem**: The original `conftest.py` used a **session-scoped** `test_engine` fixture
(`scope="session"`, `loop_scope="session"`) while `db_session` and `client` were
function-scoped (the pytest-asyncio default). asyncpg connections are bound to the
event loop in which they are created. The session-scoped engine created the connection
pool on the session-level loop, but each test function ran in a new function-scoped
loop — causing:

```
RuntimeError: Task ... got Future ... attached to a different loop
```

**Fix**: Changed all three async fixtures (`test_engine`, `db_session`, `client`) to
**function scope**. To avoid re-creating the DB schema on every test (which would be
slow), a module-level `_schema_created` flag ensures `DROP ALL` / `CREATE ALL` runs
only once per process, while each test still gets a fresh engine and asyncpg connection
pool tied to its own event loop.

Also updated the default `TEST_DATABASE_URL` fallback in `conftest.py` from the
old wrong port/password (`localhost:5432`, `changeme`) to the correct test DB
(`localhost:5435`, `change_me_in_production`).

### Files Changed

| File | Change |
|------|--------|
| `backend/tests/conftest.py` | Changed `test_engine` from session-scoped to function-scoped; added `_schema_created` guard; fixed default `TEST_DATABASE_URL`; added `loop_scope` annotations on `db_session` and `client` |
| `backend/pyproject.toml` | `asyncio_default_fixture_loop_scope` remains `"function"` (reverted attempted change to `"session"`) |

---

## Deviations from Plan

| Area | Expected | Actual | Notes |
|------|----------|--------|-------|
| Route paths | `/api/ingest`, `/api/ingest/file`, `/api/archive`, `/api/settings/keys` | Same | No path mismatches |
| Response fields | `archive_ids`, `item_count`, `status_badge`, `conversation_count` | Same | No field name mismatches |
| Loop scope | Session-scoped shared engine | Function-scoped engine per test | Required to avoid asyncpg loop binding errors |

---

## Test Database

- Host: `localhost:5435` (Docker-mapped port)
- DB: `recalium_test`
- Extension: `pgvector` (created via `CREATE EXTENSION IF NOT EXISTS vector`)
