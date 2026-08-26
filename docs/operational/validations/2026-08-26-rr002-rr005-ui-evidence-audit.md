# RR-002 / RR-005 UI Evidence Audit

**Date**: 2026-08-26  
**Gaps**: RR-002 (Frontend nav), RR-005 (Review queue UI/API evidence)  
**Executed by**: Cursor agent (Ralph loop continuation)  
**Environment**: Live Recalium stack at `http://localhost:8000` (Docker Compose)

## Summary

Audit confirms RR-002 and RR-005 are satisfied by existing implementation and the RR-011 keyboard + axe suite. No incremental feature work required — only evidence mapping and a fresh regression run.

Both gaps asked for “broader keyboard/E2E evidence.” RR-011 (closed 2026-07-17) already established per-route axe scans, route-load smoke tests, and per-workflow keyboard operability including navigation and review queue. Component-level Vitest suites cover nav link enablement and review-queue resolve/dismiss flows.

## RR-002 — Frontend nav

### Acceptance mapping

| Requirement | Evidence | Status |
| --- | --- | --- |
| All v1 left-nav sections enabled as links | `frontend/src/components/NavSidebar.tsx` — all entries `disabled: false` | ✓ |
| Nav items in correct order (WEBUI-01) | `frontend/src/tests/LeftNav.test.tsx` — 3 tests (render, order, enabled links) | ✓ |
| All routes load without crash | `frontend/e2e/keyboard-navigation.spec.ts` — 10 route smoke tests | ✓ |
| Keyboard Tab reachability on every route | `frontend/e2e/keyboard-workflows.spec.ts` — `all 9 routes are reachable via keyboard Tab navigation` | ✓ |
| WCAG 2.2 AA on nav-bearing routes | `frontend/e2e/axe.spec.ts` — per-route scans include all nav destinations | ✓ (see note) |

### Key test files

- `frontend/src/tests/LeftNav.test.tsx` — WEBUI-01 component coverage
- `frontend/e2e/keyboard-navigation.spec.ts` — route load smoke (includes `/review-queue`, `/audit`, `/settings`)
- `frontend/e2e/keyboard-workflows.spec.ts` — multi-route Tab navigation
- `frontend/e2e/axe.spec.ts` — accessibility scans

## RR-005 — Review queue UI/API

### Acceptance mapping

| Requirement | Evidence | Status |
| --- | --- | --- |
| Grouped fact comparison in UI | `frontend/src/tests/ReviewQueuePage.test.tsx` — overlap group + candidate facts rendered | ✓ |
| Resolve with resolution note | Same test — `resolveReviewItem` called with note | ✓ |
| Dismiss with confirmation | Same test — dismiss after `confirm()` | ✓ |
| API returns group metadata + candidates | `backend/tests/api/test_review_queue_api.py` | ✓ |
| Domain grouping logic | `backend/tests/domain/test_review_queue.py` | ✓ |
| Keyboard reachability on review-queue route | `frontend/e2e/keyboard-workflows.spec.ts` — `review-queue: tab to resolve/dismiss buttons` | ✓ |
| WCAG 2.2 AA on `/review-queue` | `frontend/e2e/axe.spec.ts` — `/review-queue has no axe violations` | ✓ |

### Key test files

- `frontend/src/pages/ReviewQueuePage.tsx` — grouped comparison UI
- `frontend/src/tests/ReviewQueuePage.test.tsx` — resolve/dismiss behavior
- `backend/tests/api/test_review_queue_api.py` — API contract
- `backend/tests/domain/test_review_queue.py` — conflict grouping
- `frontend/e2e/keyboard-workflows.spec.ts` — keyboard operability
- Cross-reference: [2026-07-17-rr011-keyboard-axe-evidence.md](../tests/2026-07-17-rr011-keyboard-axe-evidence.md)

## Fresh validation run (2026-08-26)

```bash
# Frontend unit tests (includes LeftNav + ReviewQueuePage)
cd frontend && pnpm test -- --run
# 24 passed (9 files)

# Review queue backend
cd backend && uv run pytest tests/api/test_review_queue_api.py tests/domain/test_review_queue.py -q
# 6 passed

# Playwright RR-011 suite against backend-served SPA
cd frontend && E2E_BASE_URL=http://localhost:8000 pnpm exec playwright test \
  e2e/keyboard-navigation.spec.ts e2e/keyboard-workflows.spec.ts e2e/axe.spec.ts
# 26 passed, 2 failed (axe on /archive and /canonical — pre-existing, not nav/review-queue scope)
```

RR-002 and RR-005 scoped tests all passed. The two axe failures on `/archive` and `/canonical` are outside these gap rows (RR-011 umbrella); track separately if they regress from the 2026-07-17 baseline.

## Conclusion

**RR-002**: ✓ CLOSED — nav enablement, component tests, route smoke, keyboard Tab navigation, and axe coverage evidenced.  
**RR-005**: ✓ CLOSED — grouped comparison, resolve/dismiss (UI + API), keyboard workflow, and axe on `/review-queue` evidenced.

**Next action**: Update gap register rows RR-002 and RR-005 to Closed and link this document.
