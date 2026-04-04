---
phase: 02-processing-pipeline
plan: 02
subsystem: backend/tests
tags: [tdd, test-scaffold, processing-pipeline, red-state]
dependency_graph:
  requires:
    - 02-01 (derived_memory models — test stubs reference them via importorskip)
  provides:
    - Failing test scaffold for plans 03–07 to turn GREEN
  affects:
    - backend/tests/worker/
    - backend/tests/domain/
    - backend/tests/api/
    - backend/tests/conftest.py
tech_stack:
  added: []
  patterns:
    - pytest.importorskip for graceful RED-state test collection
    - db_session_phase2 fixture alias for Phase 2 test self-documentation
    - function-scoped test engine with rollback isolation (existing pattern extended)
key_files:
  created:
    - backend/tests/worker/__init__.py
    - backend/tests/worker/test_loop.py
    - backend/tests/worker/test_dispatcher.py
    - backend/tests/domain/__init__.py
    - backend/tests/domain/test_derived_memory.py
    - backend/tests/domain/test_policy_gate.py
    - backend/tests/domain/test_jobs_service.py
    - backend/tests/domain/test_conflict_detection.py
    - backend/tests/api/__init__.py
    - backend/tests/api/test_reprocess.py
  modified:
    - backend/tests/conftest.py
decisions:
  - "`pytest.importorskip` chosen over `pytest.mark.xfail` — cleanly skips entire module at collection when implementation absent, avoids misleading xfail noise in CI before implementation plans run"
  - "test_engine_phase2 / db_session_phase2 fixtures kept as thin aliases of existing fixtures — self-documents Phase 2 DB dependency without duplicating rollback logic"
  - "test_reprocess.py uses no importorskip — API test will fail at runtime (404 from non-existent endpoint) rather than at collection, making pipeline failure mode explicit"
metrics:
  duration_minutes: 6
  completed_date: "2026-03-23"
  tasks_completed: 2
  files_changed: 11
---

# Phase 02 Plan 02: Test Scaffold (RED State) Summary

**One-liner:** Full TDD test scaffold for Phase 2 pipeline — 7 test files covering 10 requirement IDs using pytest.importorskip for graceful RED collection until plans 03–07 implement the modules.

---

## What Was Built

Created the complete test scaffold for Phase 2's processing pipeline. All test files are in FAILING (RED) state — 6 of 7 files use `pytest.importorskip` so pytest collects them gracefully (skipping the whole module) rather than crashing with ImportError. The 7th file (`test_reprocess.py`) collects successfully and will fail at runtime once run against a live app (no `/api/jobs/{id}/reprocess` endpoint exists yet).

### Files Created

| File | Requirements Covered | Strategy |
|------|---------------------|----------|
| `tests/worker/test_loop.py` | PIPE-01, PIPE-04 | importorskip: app.worker.loop, app.domain.jobs.service |
| `tests/worker/test_dispatcher.py` | BYOK-07, BYOK-08 | importorskip: app.worker.dispatcher |
| `tests/domain/test_derived_memory.py` | PIPE-02 | importorskip: app.domain.derived_memory.service |
| `tests/domain/test_policy_gate.py` | PIPE-03, PRIV-04, PRIV-05 | importorskip: app.domain.policy.gate |
| `tests/domain/test_jobs_service.py` | PIPE-04, PIPE-05 | importorskip: app.domain.jobs.service |
| `tests/domain/test_conflict_detection.py` | CANM-06 | importorskip: app.domain.conflict_detection |
| `tests/api/test_reprocess.py` | PIPE-05 | No importorskip — API runtime failure |

### conftest.py Extensions

- `try: import app.domain.derived_memory.models` guard block — ensures derived_memory tables are included in `Base.metadata.create_all` once Plan 02-01 models exist, without crashing pre-implementation
- `test_engine_phase2` fixture — alias of `test_engine`, self-documents DB dependency for Phase 2 tests
- `db_session_phase2` fixture — per-test async session with rollback, follows identical pattern to existing `db_session`

---

## Verification

```
$ pytest tests/worker/ tests/domain/ tests/api/test_reprocess.py --collect-only -q
tests/api/test_reprocess.py::test_reprocess_endpoint_returns_200
tests/api/test_reprocess.py::test_reprocess_unknown_job_returns_404
tests/api/test_reprocess.py::test_reprocess_pending_provider_returns_200

3 tests collected in 0.02s
```

6 files skip at collection (expected RED — importorskip fires immediately). 3 tests from `test_reprocess.py` collect successfully and will fail at runtime against the unimplemented endpoint.

---

## Deviations from Plan

None — plan executed exactly as written.

---

## Known Stubs

None — this plan intentionally creates test stubs, not production code. The test files themselves are the planned output. All tests reference modules that don't exist yet; this is the correct RED state.

---

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | `09c372a` | extend conftest.py with phase2 fixtures and create test subdirectory __init__ files |
| Task 2 | `9443b26` | add failing test stubs for all Phase 2 requirements (RED state) |

---

## Self-Check: PASSED
