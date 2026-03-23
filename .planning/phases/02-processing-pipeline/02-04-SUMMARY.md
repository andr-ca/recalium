---
phase: 02-processing-pipeline
plan: "04"
subsystem: worker-pipeline
tags: [dispatcher, derived-memory, llm-routing, byok, reprocess-api]
key-decisions:
  - "Gate mocks needed in tests when sentence_transformers unavailable — test env doesn't load NLI model"
  - "importlib.import_module avoids rebinding 'app' variable in conftest (bare import app.X.Y rebinds namespace)"
  - "FTS runs even when gate blocks (local operation, no external call)"
  - "pending_provider jobs reactivated on valid key save, not on any key save"
requires:
  - 02-03  # jobs service, gate, worker loop
provides:
  - derived_memory_write_service
  - job_dispatcher_pipeline
  - reprocess_api_endpoint
  - settings_reactivation_hook
affects:
  - backend/app/worker/loop.py  # dispatcher.py is called from loop.py
  - backend/app/api/routes/settings.py  # reactivation added
tech-stack:
  added: []
  patterns:
    - "Gate-first pipeline: classify_async() before any external API call (PIPE-01)"
    - "BYOK-07: catch provider errors as retryable_failed with error captured"
    - "BYOK-08: check get_existing_summary() before calling LLM — skip if present"
    - "importlib.import_module() for guarded imports to avoid namespace rebinding"
key-files:
  created:
    - backend/app/domain/derived_memory/service.py
    - backend/app/worker/dispatcher.py
    - backend/app/api/routes/jobs.py
  modified:
    - backend/app/infrastructure/settings.py  # added ollama_model field
    - backend/app/api/routes/__init__.py  # added jobs router
    - backend/app/api/routes/settings.py  # added reactivate_pending_provider_jobs call
    - backend/tests/conftest.py  # fixed app variable rebinding bug
    - backend/tests/worker/test_dispatcher.py  # added gate mock + archive FK helper
    - backend/tests/api/test_reprocess.py  # added archive FK helper
metrics:
  duration_seconds: 673
  completed_at: "2026-03-23T13:15:20Z"
  tasks_completed: 3
  files_changed: 9
---

# Phase 02 Plan 04: LLM Pipeline Dispatcher and Reprocess API Summary

**One-liner:** Full LLM processing pipeline with gate-first dispatch (OpenAI/Anthropic/Ollama routing), derived-memory write service, and reprocess endpoint with pending_provider reactivation.

## What Was Built

### Task 1: derived_memory service (COMMITTED: `08b7c64`)
`backend/app/domain/derived_memory/service.py` — already committed before this plan execution.

Functions:
- `write_summary(session, raw_archive_id, summary_text, model_used, derivation_method)` — writes Summary row with source_status='active'
- `write_facts(session, raw_archive_id, facts_data)` — PIPE-02: validates source_span; empty → forces confidence_tier='low'; validates confidence_tier in (high/medium/low)
- `write_fts_entry(session, raw_archive_id, text_content)` — writes FtsEntry and populates search_vector via `to_tsvector('english', ...)`
- `get_existing_summary(session, raw_archive_id)` — returns first active summary (BYOK-08 skip check)

### Task 2: Settings + dispatcher (COMMITTED: `66d82a8`)
`backend/app/infrastructure/settings.py`:
- Added `ollama_model: str = "llama3.2"` field

`backend/app/worker/dispatcher.py`:
- `dispatch_job(session, job)` — full pipeline: load archive → gate.classify_async() → LLM summarize/extract → FTS index → complete
- `_run_summarize_job(text)` — OpenAI gpt-4o-mini / Anthropic claude-3-haiku / Ollama routing
- `_run_extract_job(text)` — same provider routing, JSON extraction with facts array
- BYOK-07: all provider exceptions → `fail_job(retryable=True)` with `{error_type}: {error[:500]}`
- BYOK-08: `get_existing_summary()` check before LLM call — skips if summary exists
- No provider → `set_pending_provider()` with descriptive reason

### Task 3: Reprocess API endpoint (COMMITTED: `5012aef`)
`backend/app/api/routes/jobs.py`:
- `POST /api/jobs/{job_id}/reprocess` → 200 `{status, job_id}` or 404

`backend/app/api/routes/__init__.py`:
- Added `jobs_router` with prefix `/jobs`

`backend/app/api/routes/settings.py`:
- Added `reactivate_pending_provider_jobs(session)` call when validation returns `status == "valid"`

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Gate blocks → job completes (not fails) | Blocked content is intentional privacy protection, not an error |
| FTS runs even when gate blocks | FTS is local, no external call — always safe to index |
| FTS failure is non-fatal | FTS indexing failing doesn't prevent job completion |
| Gate error → retryable_failed | Gate failure is unexpected and should retry |
| Provider not configured → pending_provider (not failed) | Missing key is user workflow state, not an error |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] conftest.py app variable rebinding**
- **Found during:** Task 3 (running reprocess tests)
- **Issue:** `import app.domain.derived_memory.models` (bare `import`) rebinds the module-level `app` variable from FastAPI instance to the `app` package module, causing `AttributeError: module 'app' has no attribute 'dependency_overrides'` in all API tests
- **Fix:** Changed to `importlib.import_module("app.domain.derived_memory.models")` which doesn't rebind namespace variables
- **Files modified:** `backend/tests/conftest.py`
- **Commit:** `5012aef`

**2. [Rule 1 - Bug] test_dispatcher.py: gate blocks test content in CI**
- **Found during:** Task 2 (running dispatcher tests)
- **Issue:** In test env without `sentence_transformers`, gate defaults to "unclassified" (blocked) for all content not matching keyword heuristics. This prevented `_run_summarize_job` from being called, so BYOK-07 test was asserting `retryable_failed` but getting `completed`
- **Fix:** Added mock for `_gate.classify_async` returning `general` (non-blocked) and `_has_llm_provider` returning True so the LLM path is exercised
- **Files modified:** `backend/tests/worker/test_dispatcher.py`
- **Commit:** `66d82a8`

**3. [Rule 1 - Bug] FK constraint violations in tests**
- **Found during:** Tasks 2 and 3
- **Issue:** Test jobs created with random `raw_archive_id` that had no corresponding `raw_archive` row, violating FK constraint
- **Fix:** Added `_make_archive_item()` helper in both test files to create minimal `RawArchiveItem` before jobs
- **Files modified:** `backend/tests/worker/test_dispatcher.py`, `backend/tests/api/test_reprocess.py`
- **Commit:** `66d82a8`, `5012aef`

**4. [Rule 3 - Blocking] openai package not installed in venv**
- **Found during:** Task 2 (running dispatcher tests)
- **Issue:** `openai` and `anthropic` packages listed in `pyproject.toml` dependencies but not installed in `.venv`
- **Fix:** Ran `uv pip install openai anthropic` to install packages
- **Effect:** Tests now have access to `openai.AuthenticationError` for BYOK-07 test

## Known Stubs

- `dispatch_job` has a comment: "Stub: embedding and conflict detection are added in 02-05 and 02-06" — this is intentional, embeddings and conflict detection are wired in subsequent plans (02-05, 02-06)

## Self-Check: PASSED

All key files found on disk:
- FOUND: backend/app/domain/derived_memory/service.py
- FOUND: backend/app/worker/dispatcher.py
- FOUND: backend/app/api/routes/jobs.py
- FOUND: .planning/phases/02-processing-pipeline/02-04-SUMMARY.md

All commits verified in git log:
- FOUND: 08b7c64 (derived_memory service)
- FOUND: 66d82a8 (dispatcher + settings)
- FOUND: 5012aef (reprocess endpoint + settings reactivation)
- FOUND: 5d6976b (docker-compose port alignment)

All tests passing: 8/8 (test_derived_memory: 3, test_dispatcher: 2, test_reprocess: 3)
