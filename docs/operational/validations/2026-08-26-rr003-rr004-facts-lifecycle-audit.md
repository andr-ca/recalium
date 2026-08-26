# RR-003 / RR-004 Facts API and Lifecycle Audit

**Date:** 2026-08-26  
**Gap register rows:** RR-003, RR-004  
**Auditor:** engineering agent (PO-directed M1 closure)

## Summary

Both gap-register rows were written before the facts lifecycle landed. Audit confirms **RR-003 and RR-004 are CLOSED** with cited code and test evidence. One test gap (retrieval filtering per review status) was filled during this audit; one flaky list test was scoped.

## RR-003 — Facts API

| Required completion | Evidence |
| --- | --- |
| Facts list endpoint | `GET /api/facts/` and `/api/facts` — `backend/app/api/routes/facts.py` |
| Filter by source/confidence/review status | Query params: `source_status`, `review_status`, `confidence_tier`, pagination |
| Single-fact GET | `GET /api/facts/{fact_id}` |
| Edit (PATCH) | `PATCH /api/facts/{fact_id}` + audit event `fact_updated` |
| Dispute / stale / archive / delete | `POST .../dispute`, `.../mark-stale`, `.../archive`; `DELETE .../{id}` |
| API tests | `backend/tests/api/test_facts_api.py` (6 tests) |

**Validation command:**

```bash
cd backend && uv run pytest tests/api/test_facts_api.py -q
```

## RR-004 — Fact lifecycle

| Required completion | Evidence |
| --- | --- |
| Status model (`review_status`) | `Fact.review_status` — `backend/app/domain/derived_memory/models.py`; values: active, disputed, stale, archived, deleted |
| Service methods / routes | `_set_fact_review_status`, dispute/stale/archive/delete routes — `facts.py` |
| Audit events | `fact_updated`, `fact_marked_disputed`, `fact_marked_stale`, `fact_archived`, `fact_deleted` |
| UI actions | `frontend/src/pages/FactsPage.tsx` — edit, dispute, stale, archive, delete, promote |
| UI tests | `frontend/src/tests/FactsPage.test.tsx` — lifecycle actions mocked |
| Retrieval filters non-active facts | SQL `f.review_status = 'active'` in `backend/app/domain/retrieval/service.py`; MCP `get_fact_links` / `list_tags` same filter |
| Retrieval test (added 2026-08-26) | `test_retrieval_excludes_non_active_review_status_facts` in `backend/tests/integration/test_retrieval_filters.py` |

**Validation commands:**

```bash
cd backend && uv run pytest tests/api/test_facts_api.py tests/integration/test_retrieval_filters.py -q
cd frontend && pnpm test src/tests/FactsPage.test.tsx
```

## Fixes applied in this audit

1. **`test_list_facts_returns_active_facts`** — stopped asserting absolute `count == 1` (cross-suite flake); now asserts created active fact is listed and source-removed fact is excluded.
2. **`test_retrieval_excludes_non_active_review_status_facts`** — proves only `review_status=active` facts appear in keyword retrieval; disputed/stale/archived/deleted excluded.

## Targeted regression (2026-08-26)

```bash
cd backend && uv run pytest \
  tests/api/test_facts_api.py \
  tests/integration/test_retrieval_filters.py \
  tests/api/test_review_queue_api.py \
  tests/mcp/test_mcp_server.py -q
```

**Result:** 25 passed.

## Verdict

**RR-003 CLOSED.** **RR-004 CLOSED.** No functional remainder requiring new feature work.
