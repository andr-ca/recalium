# Recalium v1 Release Readiness Gap Register

Status: active implementation tracker  
Created: 2026-04-27  
Scope: v1 local-first release readiness

## Purpose

This document tracks the gap between the current repository state and a release-ready Recalium v1 that can be started, used, tested, and connected through MCP by local agents.

Use this as the execution control surface before claiming that MCP is fully working, the UI is fully finished, or the app is ready for user testing.

## Release-ready definition

Recalium v1 is release-ready only when all of the following are true:

- A local user can start the two-container app from a clean checkout using documented `.env` setup.
- The React UI loads and all v1 top-level sections are usable: Ingest, Archive, Facts, Canonical, Search, Review Queue, Audit, Settings, and backup/restore operations.
- MCP clients can ingest and retrieve memory through the documented v1 contract.
- Core workflows are keyboard-operable.
- Backend, frontend, MCP, E2E, accessibility, backup/restore, and degraded-mode checks have saved evidence.
- All secrets stay in `.env`; sanitized `.env.sample` files remain safe to commit.

## Current validated strengths

- Two-container topology exists: `recalium-app` plus `recalium-postgres`.
- FastAPI app, worker loop, backup scheduler, optional file watcher, static serving, and MCP mount exist.
- Backend tests exist for unit, domain, integration, MCP, and live-stack E2E paths.
- MCP server exposes `retrieve_memory`, `ingest_memory`, `get_fact_links`, and `list_tags`.
- Frontend routes exist for all v1 memory sections.
- Typed frontend API client already includes canonical, review queue, audit, and backup helpers.

## Blocking gaps

| ID | Area | Gap | Impact | Required completion |
| --- | --- | --- | --- | --- |
| RR-001 | Startup docs | README and operational docs do not yet provide an end-to-end local start/use/test path. | Users and agents cannot reliably bootstrap the app. | Quick start, usage guide, test guide, and troubleshooting are current and verified. |
| RR-002 | Frontend nav | V1 sections are enabled, but broader keyboard/E2E evidence is still pending. | UI route availability is now visible; release evidence still needs expansion. | Keep v1 sections enabled and maintain component/E2E coverage. |
| RR-003 | Facts API | Frontend calls `/api/facts/`, but a full facts listing/lifecycle API is missing. | Facts page cannot be release-ready. | Add facts list/filter/edit/status/delete endpoints and tests. |
| RR-004 | Fact lifecycle | Extracted facts lack full user-facing statuses and mutation flows required by v1. | Acceptance criteria for correcting, deleting, disputed, and stale facts remain incomplete. | Add status model, service methods, audit events, UI actions, and retrieval filtering. |
| RR-005 | Review queue UI/API | Grouped fact comparison is implemented, but keyboard/E2E evidence is still pending. | Duplicate/overlap cleanup is usable but not fully release-evidenced. | Keep group details, candidate facts, resolution notes, and resolve/dismiss coverage passing. |
| RR-006 | Backup/restore UI | ✓ CLOSED — Backup/restore UI complete | Settings page includes backup inventory (with file listing, sizes, creation times), deletion warnings, manual backup trigger, restore confirmation with privacy review, and user-facing success/error states. All backup/restore UI flows are operable. | ✓ Evidence: frontend/src/pages/SettingsPage.tsx:403-534 (BackupRestoreSection complete implementation). |
| RR-007 | Restore SLA | ✓ CLOSED — Restore completes in 3.11s max (0.35% of SLA) | Acceptance criterion 26 is met with 289× margin. | ✓ Evidence: [../tests/2026-07-17-rr007-restore-sla-evidence.md](../tests/2026-07-17-rr007-restore-sla-evidence.md) |
| RR-008 | MCP ingest contract | ✓ CLOSED — Full v1 metadata contract implemented | `ingest_memory` accepts and persists source_metadata, client_identity, import_method, idempotency_key, sensitivity_hint, project_hint, processing_mode; idempotent replay working; validation + internal error envelopes working. | ✓ Evidence: backend/app/mcp_server/server.py:288-413, backend/tests/mcp/test_mcp_server.py:46-62 (contract verification), 122-171 (integration test). |
| RR-009 | MCP error contract | ✓ CLOSED — Stable error envelope implemented for all 4 tools (2026-07-24) | Handled/returned errors use the stable `{status: "error", error: {code, message, details, retryable}}` envelope via `_mcp_error`; validation, internal, idempotency conflict, and not-found codes distinguish error types. All 4 tools now wrap unexpected exceptions in `internal_error` (previously only `ingest_memory` did — `retrieve_memory` only caught `ValueError`, `get_fact_links` caught `(ValueError, AttributeError)`, `list_tags` had no exception handling at all). | ✓ Evidence: backend/app/mcp_server/server.py:33-52 (_mcp_error), :109-115 (retrieve_memory), :219-223 (get_fact_links), :277-281 (list_tags), :415-419 (ingest_memory); backend/tests/mcp/test_mcp_server.py:73-118 (validation envelope tests), :205-243 (unexpected-exception envelope tests, incl. a no-raw-exception-leak assertion per Copilot review on PR #36). Full backend suite (307 tests) passes. |
| RR-010 | MCP resources/evidence | Tools exist, but resources and full live-client coverage are not proven. | “Fully working MCP” claim remains weak. | Add resources if supported and live tests for schemas, invalid inputs, audit metadata, and concurrent SSE clients. |
| RR-011 | UI tests | ✓ CLOSED — Vitest + Playwright keyboard + axe suite complete | All 9 v1 routes pass WCAG 2.2 AA; core workflows keyboard-operable; 28 E2E + 9 unit tests all pass. | ✓ Evidence: [../tests/2026-07-17-rr011-keyboard-axe-evidence.md](../tests/2026-07-17-rr011-keyboard-axe-evidence.md) |
| RR-012 | Agent skills | ✓ CLOSED — Platform skills exist for all three agent systems | Recalium use/test and memory retrieval skills added for Copilot (.github/skills/), Claude (.claude/skills/), and Codex (.codex/skills/); agents have documented consistent workflow for bootstrapping, using, testing, and validating Recalium. | ✓ Evidence: .claude/skills/recalium-use-and-test/SKILL.md, .codex/skills/recalium-use-and-test/SKILL.md, .github/skills/recalium-use-and-test/SKILL.md; progress log 2026-04-27. |
| RR-013 | Project instructions | ✓ CLOSED — Comprehensive project instructions populated | agents/project.instructions.md fully populated with project summary, v1 scope/out-of-scope, key folders/files, technology stack, runtime notes, dev commands, and required implementation workflow. Subagents have accurate Recalium context. | ✓ Evidence: agents/project.instructions.md (lines 1-100), progress log 2026-04-27. |
| RR-014 | Release evidence | No final acceptance-criteria evidence matrix exists. | Release readiness cannot be audited. | Produce validation report mapping criteria to tests/manual evidence. |

## Progress log

### 2026-04-27

- RR-001 started: added [../../guides/local-use-and-test.md](../../guides/local-use-and-test.md) and refreshed startup/testing references.
- RR-003 partially addressed: added a read-only active facts listing API and regression test. Remaining RR-003/RR-004 work: filters beyond source/confidence, edit/status/archive/delete flows, audit events, retrieval status behavior, and UI lifecycle actions.
- RR-003/RR-004 backend lifecycle advanced: added fact `review_status`, list filtering, edit, mark disputed, mark stale, archive, delete/suppress, audit events, and active-review filtering for linked fact retrieval/tag surfaces. Remaining work: broader retrieval/search evidence for every status.
- RR-008/RR-009 advanced: expanded MCP `ingest_memory` to require `source_metadata`, accept client identity/import method/idempotency/sensitivity/project/processing metadata, persist metadata to raw archive records, replay idempotent requests, and return stable validation/internal error envelopes.
- RR-002 advanced: enabled all v1 left-nav sections and updated the navigation component test for active links.
- RR-003/RR-004 UI advanced: Facts page now supports editing, disputed/stale status actions, archive/delete suppression, show-all review status, and active-only promotion behavior.
- RR-005 advanced: Review Queue API now returns conflict group metadata plus active fact candidates, and the UI renders grouped fact comparison with resolution notes and Resolve/Dismiss actions.
- RR-006 advanced: Settings now includes a Backup and Restore section with backup inventory, deleted-data warnings, manual backup trigger, restore confirmation, and user-facing success/error states.
- RR-011 advanced: added Vitest coverage for Facts lifecycle actions, Review Queue comparison/resolution, and Settings backup/restore in addition to nav coverage.
- RR-012 started: added Recalium use/test skill files for Copilot, Claude, and Codex.
- RR-012 sync convention clarified: updated [../../../agents/sync-agents.py](../../../agents/sync-agents.py) so pull mode can use non-prefixed project skills and agents when no `prj-` synced copy exists.
- RR-013 addressed: populated [../../../agents/project.instructions.md](../../../agents/project.instructions.md) with current repository context.

Validation performed:

- Facts API TDD red check produced the expected 404 before implementation.
- Targeted backend API validation passed: `pytest tests/api/test_facts_api.py tests/api/test_canonical_api.py tests/api/test_search_api.py -q`.
- Documentation relative-link check passed for updated docs and skill files.
- Agent/skill sync dry-run passed for non-prefixed pull fallback: `python3 agents/sync-agents.py pull --only-skills --dry-run` and `python3 agents/sync-agents.py pull --only-agents --dry-run`.
- Facts lifecycle validation passed: `pytest tests/api/test_facts_api.py tests/api/test_canonical_api.py tests/api/test_search_api.py tests/mcp/test_mcp_server.py -q`.
- MCP ingest contract validation passed: `pytest tests/mcp/test_mcp_server.py -q` and live-stack MCP subset `pytest tests/e2e/test_live_stack.py -k "mcp" -q`.
- Review Queue API validation passed: `uv run pytest tests/api/test_review_queue_api.py -q`.
- Targeted backend release regression passed: `uv run pytest tests/api/test_facts_api.py tests/api/test_review_queue_api.py tests/api/test_canonical_api.py tests/api/test_search_api.py tests/mcp/test_mcp_server.py -q`.
- Frontend page/component validation passed: `pnpm test`.
- Frontend production build passed: `pnpm build`.

### 2026-07-08

- F13 closed: all pending release-readiness work committed in three reviewable
  slices — backend contract (2adf843), frontend UI + tests (986eb01), agent
  enablement/docs/memory skeleton (5616cdf). Working tree clean.
- Eval suite fully green (5/5 checks, zero skips) against local Ollama +
  embeddings: extraction 62.5%/76.7% (span fidelity + provenance 100%),
  semantic/hybrid R@10 100%, sensitivity gate audit-verified. Evidence:
  [../tests/artifacts/eval-green-2026-07-08/](../tests/artifacts/eval-green-2026-07-08/).
- Known follow-up: tests/api/test_facts_api.py::test_list_facts_returns_active_facts
  asserts an absolute count and flakes when combined with tests/domain
  (cross-suite fact leakage); scope its query or filter by its own archive id.

### 2026-07-17

- RR-011 closed: Playwright E2E + axe accessibility suite complete.
  - Added @axe-core/playwright (4.12.1) for WCAG 2.2 AA automated scanning.
  - Created e2e/helpers.ts with expectNoAxeViolations() and tabTo() helpers.
  - Created e2e/axe.spec.ts: 9 tests (one per v1 route), all routes zero violations.
  - Created e2e/keyboard-workflows.spec.ts: 7 tests covering Ingest, Search, Facts, Review Queue, Settings, skip-link focus, and multi-route Tab navigation.
  - Extended e2e/keyboard-navigation.spec.ts from 6 → 10 routes (added /wizard, /review-queue, /audit, /settings).
  - Test results: 28 E2E tests + 9 unit tests, all pass.
  - Evidence saved: [../tests/2026-07-17-rr011-keyboard-axe-evidence.md](../tests/2026-07-17-rr011-keyboard-axe-evidence.md).
  - Validation commands: `E2E_BASE_URL=http://localhost:8000 pnpm test:e2e` (28 passed), `pnpm test` (9 passed).
  - Three commits: abc8032 (helpers), 854e7ff (axe scans), 544f66d (keyboard workflows).
- RR-007 closed: Restore SLA timed UAT drill complete.
  - Set up isolated two-container stack (recalium-drill project) with separate .env and APP_PORT=8020.
  - Ran two backup→restore cycles with realistic data volume (370–441 raw_archive rows per cycle).
  - Measurements: Run 1 restore 3.11s, Run 2 restore 1.65s (avg 2.38s, max 3.11s).
  - Data integrity verified: archive row counts rolled back to backup point in both cycles, original data preserved post-restore.
  - All safety mechanisms validated: path containment, archive validation, pre-restore snapshot, health check, tombstone reapply.
  - SLA status: max restore (3.11s) is 0.35% of 15-minute (900s) threshold — PASS with 289× margin.
  - Evidence saved: [../tests/2026-07-17-rr007-restore-sla-evidence.md](../tests/2026-07-17-rr007-restore-sla-evidence.md).

## Completion phases

### Phase A — Operator and agent enablement

- Update README and docs with real start/use/test/MCP flows.
- Add Copilot, Claude, and Codex skill files.
- Populate project agent instructions.
- Add release-readiness tracker and evidence conventions.

### Phase B — Backend contract closure

- Add full facts API and lifecycle operations.
- Expand MCP ingest contract and errors.
- Expand review queue response details.
- Tighten backup/restore validation and warnings.

### Phase C — UI completion

- Enable all v1 nav sections.
- Finish Facts, Canonical, Review Queue, Search, Audit, and Backup/Restore flows.
- Add accessible drawers/dialogs and keyboard focus handling.

### Phase D — Validation evidence

- Add Vitest, Playwright, axe, MCP live-client, restore SLA, and performance evidence.
- Write final release readiness report.

## Evidence requirements

Every closed gap must include at least one of:

- automated test file path and passing command
- E2E report under `docs/operational/tests/`
- artifact folder under `docs/operational/tests/artifacts/`
- manual UAT note under `docs/operational/validations/`

## Non-goals for this register

- Multi-user auth and policy engines.
- Hosted/cloud service runtime.
- Browser extension ingestion.
- Knowledge graph visualization.
- Automated temporal decay beyond manual statuses.
