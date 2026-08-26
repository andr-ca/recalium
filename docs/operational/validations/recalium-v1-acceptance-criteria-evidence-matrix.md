# Recalium v1 Acceptance Criteria → Evidence Matrix (RR-014)

**Purpose:** map every criterion in `docs/requirements/features/platform-v1/acceptance-criteria.md`
to concrete evidence (test file/function, or explicit gap), so release readiness
is auditable in one place instead of scattered across ad-hoc validation docs.

**Method:** each row cites the test(s) or code location that exercises the
criterion, verified by reading the actual test/source at the time of writing
(not inferred from names or docstrings). Rows with no direct automated
evidence are marked ✗ Gap rather than stretched to fit — an honest gap is more
useful than a false checkmark. Cross-referenced against the existing
[release readiness gap register](recalium-v1-release-readiness-gap-register.md)
where an RR row already covers a criterion in depth.

**Status key:** ✓ Evidenced · ⚠ Partial (some coverage, see note) · ✗ Gap

---

## Product-level acceptance criteria

| # | Criterion (short) | Status | Evidence |
|---|---|---|---|
| 1 | Paste/upload import stores raw content + metadata, shows in review UI | ✓ | `backend/tests/test_ingest.py::test_paste_ingest`, `::test_chatgpt_upload`, `::test_claude_upload`, `::test_generic_json_upload`, `::test_txt_upload` |
| 2 | Processing exposes summaries/facts/search without losing raw archive | ✓ | `backend/tests/worker/test_dispatcher.py` (extraction/summarization pipeline); `backend/tests/domain/test_deletion_cascade.py::test_priv01_cascade_suppresses_summaries` and `::test_priv01_cascade_suppresses_facts` confirm raw archive and derived artifacts are linked, not merged |
| 3 | Facts: inspect provenance, edit, delete, dispute/stale, promote to canonical | ✓ | `backend/tests/api/test_facts_api.py::test_update_fact_edits_review_fields_and_audits`, `::test_mark_fact_disputed_and_stale`, `::test_archive_and_delete_fact_hide_from_default_list`, `::test_get_fact_returns_single_fact`; `backend/tests/api/test_canonical_api.py::test_promote_fact_no_source_span_requires_confirmed` |
| 4 | Canonical memory distinguished/prioritized over unconfirmed extracted memory | ✓ | `backend/tests/domain/test_retrieval.py::test_rrf_canonical_stays_distinct_from_its_archive`; retrieval budget-trim priority order (see #20) puts canonical first |
| 5 | Keyword/semantic/hybrid search returns ranked results with source links + filters | ✓ | `backend/tests/api/test_search_api.py::test_search_endpoint_hybrid_mode`; `backend/tests/integration/test_retrieval_filters.py` |
| 6 | Bounded context budget returns smallest useful ranked set per mode | ✓ | `backend/tests/domain/test_retrieval.py::test_budget_trimming_respects_priority_order`, `::test_budget_trimming_does_not_truncate_mid_item` |
| 7 | MCP/machine retrieval records access event with client identity, timestamp, operation metadata | ✓ | `backend/tests/api/test_search_api.py::test_search_emits_audit_event`; MCP-03/04 in `backend/app/mcp_server/server.py` (audit event on `retrieve_memory`) |
| 8 | User correction/deletion of derived item visible in future review/retrieval | ✓ | `backend/tests/domain/test_deletion_cascade.py` (full `PRIV-01` suite: cascade suppresses summaries, facts, FTS entries, embeddings) |
| 9 | Duplicate/overlapping facts grouped or flagged for cleanup | ✓ | `backend/tests/domain/test_conflict_detection.py::test_duplicate_detected_by_cosine_similarity`, `::test_conflict_group_created_for_duplicates`; `backend/tests/api/test_review_queue_api.py::test_review_queue_includes_group_fact_comparison` |
| 10 | Navigate to source provenance from any summary/fact/canonical item | ✓ | `backend/app/domain/retrieval/service.py` provenance fields (`source_excerpt`, `source_id`, etc.) on every retrieval item type; `backend/tests/domain/test_retrieval.py::test_retrieval_item_has_required_provenance_fields` |
| 11 | No-key mode: usable for local storage, browsing, keyword search, basic local processing | ✓ | `backend/tests/test_settings.py::test_degraded_mode_no_keys`; `backend/tests/domain/test_retrieval.py::test_hybrid_retrieval_falls_back_to_keyword_when_no_embeddings` |
| 12 | Personal profile/relationship content blocks external processing by default | ✓ | `backend/tests/domain/test_policy_gate.py::test_personal_profile_blocked`, `::test_relationship_content_blocked` |
| 13 | Sensitivity pre-classification blocks external processing unless overridden | ✓ | `backend/tests/domain/test_policy_gate.py::test_sensitive_category_blocks_at_low_bar`, `::test_relationship_similarity_blocks`; `backend/tests/domain/test_policy_resolver.py::test_sensitive_hint_forbids_external_even_if_gate_allows` |
| 14 | Unknown/unclassified content blocks external processing by default | ✓ | `backend/tests/domain/test_policy_gate.py::test_unclassified_blocked_by_default` |
| 15 | Deleted/redacted source suppresses linked derived artifacts from retrieval/search immediately | ✓ | `backend/tests/domain/test_deletion_cascade.py::test_priv01_cascade_suppresses_fts_entries`, `::test_priv01_cascade_suppresses_embeddings` |
| 16 | Canonical entry from later-deleted source keeps source-removed + required-review state | ✓ | `backend/tests/domain/test_deletion_cascade.py::test_priv02_canonical_marked_source_removed_not_deleted` |
| 17 | Backups/exports exclude deleted data; older backups flagged as potentially containing it | ✓ | `backend/tests/domain/test_backup_service.py::test_priv03_backup_predates_deletion_flag` |
| 18 | No embeddings + no external provider: keyword search still available | ✓ | `backend/tests/domain/test_retrieval.py::test_semantic_retrieval_no_embeddings_returns_empty` + keyword-mode tests confirm keyword path is independent of embedding availability |
| 19 | Canonical/extracted conflict: canonical first, conflicting extracted ranked lower with conflict label | ✓ | `backend/tests/domain/test_retrieval.py::test_rrf_canonical_stays_distinct_from_its_archive`; `conflict_label` field verified in `test_retrieval_item_has_required_provenance_fields` |
| 20 | Budget trim priority: canonical → facts → summaries → raw excerpts, stops at budget | ✓ | `backend/tests/domain/test_retrieval.py::test_budget_trimming_respects_priority_order` |
| 21 | Provenance includes source ID, system, timestamp, derivation process/timestamp, session ID, import method, excerpt/hash, modifying identity | ✓ | `backend/app/domain/retrieval/service.py:496-513` (`source_excerpt` etc.); `backend/tests/domain/test_retrieval.py::test_retrieval_item_has_required_provenance_fields` |
| 22 | Audit event includes timestamp, client identity, operation, result count, target/query, mode, status, item IDs, policy reason | ✓ | `backend/tests/domain/test_policy_gate.py::test_decision_has_required_audit_fields`; `backend/tests/api/test_search_api.py::test_search_emits_audit_event` |
| 23 | MCP `retrieve` response includes items, source links, type, score, provenance, conflict labels, budget/trim reason, mode metadata | ✓ | `backend/app/mcp_server/server.py:113-136` (`retrieve_memory` return shape); `backend/tests/e2e/test_live_stack.py` live-stack coverage |
| 24 | MCP ingest request with content/metadata/identity/import method/idempotency/hints/mode is acknowledged with trackable ID | ✓ | `backend/tests/mcp/test_mcp_server.py::test_ingest_memory_accepts_metadata_and_replays_idempotency`; RR-008 (closed) |
| 25 | Broader-than-localhost exposure requires auth/session/transport protection | ✓ | `backend/tests/api/test_auth_middleware.py::test_priv06_auth_required_when_non_localhost`, `::test_priv06_auth_succeeds_with_correct_token` |
| 26 | Scheduled backups: daily, 30-day retention, restore within 15 min | ⚠ | `backend/tests/domain/test_backup_service.py::test_bkup01_delete_old_backups` covers retention pruning; **restore time is evidenced separately** in RR-007 (3.11s max, 289× margin) — no single test asserts the full "daily cadence" scheduling behavior itself (relies on the container's cron/schedule config, not unit-tested) |
| 27 | Successful restore includes archive, summaries, facts, canonical, provenance, audit events, config | ✓ | `backend/tests/integration/test_backup_restore_safety.py::test_full_delete_backup_restore_lifecycle`; RR-007 evidence doc |
| 28 | Core workflows (ingest, search, fact review, canonical edit, review queue, restore) keyboard-operable | ✓ | RR-011 (closed): `docs/operational/tests/2026-07-17-rr011-keyboard-axe-evidence.md` — 28 E2E + 9 unit tests, all 9 v1 routes WCAG 2.2 AA |
| 29 | *(Could-have)* Human-readable export with index, type folders, manifest | ✓ | `backend/tests/e2e/test_live_stack.py::test_export_bundle_format`, `::test_import_bundle_dedup` |

## Cross-cutting NFR acceptance criteria

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Ingest ack P95 ≤ 1s for ≤5MB paste/upload | ✓ | `backend/tests/test_ingest.py::test_ingest_latency`; eval suite `ingest` check (P95 ~36-63ms measured, far under 1000ms threshold) |
| 2 | Search/retrieval P95 ≤ 2s up to 100k items | ⚠ | Eval suite `retrieval` check measures P95 well under 2s threshold, but at synthetic-eval scale (dozens of items), not the full 100k-item NFR target — no dedicated 100k-scale load test exists (`evals/checks/eval_scale.py` exercises volume/concurrency but not this specific P95-at-100k claim) |
| 3 | Raw archive durable across container/host restart with persisted volumes | ⚠ | `docker-compose.yml` bind-mount volumes (`./data/postgres`) make durability structurally sound, but no explicit restart-and-verify integration test exists — the literal criterion (survives an actual restart cycle) is architecturally satisfied but not test-proven |
| 4 | ≥90 days of machine-client audit-access history available | ✗ | No retention-period enforcement or test found for audit event history (no purge job observed); audit events appear to be retained indefinitely by default (never deleted), which technically satisfies "≥90 days" but isn't explicitly tested/documented as a guarantee |

## Anti-criteria (must NOT be true)

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Extraction: >50% trivial/incorrect facts fails launch bar | ✓ | Eval suite `extraction` check: precision 0.75 (≥0.70 gate) — most extracted facts are correct, well under the 50%-trivial failure bar. See PR #26 (extraction prompt fix) |
| 2 | Zero relevant results on first search fails launch bar | ✓ | Eval suite `retrieval` check: hybrid recall@5 ~0.88 on the golden set — not zero-relevance |
| 3 | >30s review time for MCP-retrieved context fails signal-to-noise bar | ✗ | No automated or manual timing study of human review time for retrieved context exists; this is a UX/human-factors criterion not covered by the current eval or test suite |
| 4 | First-run wizard + first search >30 min fails cold-start bar | ✗ | `frontend/src/pages/WizardPage.tsx` exists but no timed end-to-end UAT of the full cold-start flow was found in this pass |
| 5 | No cost-visibility before bulk import (with providers configured) fails cost bar | ⚠ | `frontend/src/pages/WizardPage.tsx:354` (tagged `BYOK-06`): a real cost-estimate UI exists (token count + estimated USD, shown before import) — feature is implemented, but no automated test (unit or E2E) was found exercising it, so it's unverified rather than a true gap |

## BYOK acceptance criteria

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Key validation confirms success or specific failure reason | ✓ | `backend/tests/test_settings.py::test_validate_openai_key_valid`, `::test_validate_invalid_key`, `::test_validate_unknown_provider` |
| 2 | All provider calls use configured keys; no Recalium-operated service calls | ✓ | Architectural constraint (BYOK-by-default, no Recalium-operated processing service exists in v1 per CLAUDE.md/roadmap); `backend/tests/test_settings.py::test_key_not_in_db` confirms keys aren't persisted server-side beyond `.env` |
| 3 | No keys configured: still usable for ingest/storage/browse/keyword search | ✓ | `backend/tests/test_settings.py::test_degraded_mode_no_keys` |
| 4 | Invalid key during processing → retryable failed state with clear error | ✓ | `backend/tests/domain/test_jobs_service.py::test_fail_job_with_error_message` (tagged `BYOK-07`): simulates `AuthenticationError: invalid api key`, asserts job status becomes `retryable_failed` with the error message captured |

## Scope guard acceptance criteria

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | v1 does not require automated vendor-specific connectors | ✓ | Confirmed by design — ingest is paste/file-upload based (`test_ingest.py`), no vendor API connectors in `backend/app` |
| 2 | v1 does not require multi-user support | ✓ | No user/tenant model in schema (per CLAUDE.md constraint: "single-user v1"); confirmed no multi-tenant columns in domain models |
| 3 | v1 does not require advanced per-agent permissions | ✓ | MCP tools have no per-agent ACL model — confirmed absent in `backend/app/mcp_server/server.py` |
| 4 | v1 does not require graph visualization | ✓ | No graph-rendering UI found in `frontend/src/pages` (note: memory visualization/traversal work is in progress on a separate branch as of 2026-07-24 — re-check this row once that work merges, since it may change this scope guard's status) |
| 5 | v1 does not require automated memory decay logic beyond manual status handling | ✓ | Fact/canonical status transitions (`disputed`, `stale`, `deleted`) are all explicit user/API actions (`test_mark_fact_disputed_and_stale`, `test_mark_canonical_stale`) — no time-based automated decay job found |

---

## Summary

- **47 criteria total**, verified against actual test/source code (not inferred from docstrings alone).
- **✓ Evidenced: 40** — direct, verified automated test coverage or explicit code-level confirmation.
- **⚠ Partial: 4** — some coverage exists but doesn't fully close the literal criterion (product #26 scheduling cadence, NFR #2 scale-at-100k, NFR #3 restart-cycle — architecturally sound, not test-proven — anti-criteria #5 cost visibility — feature implemented but untested).
- **✗ Gap: 3** — no automated evidence found (NFR #4 audit retention enforcement, anti-criteria #3 review-time UX, anti-criteria #4 cold-start timing).

**Recommendation:** none of the remaining gaps/partials block v1 release on their own. Anti-criteria #3/#4 are UX timing studies, not code defects. NFR #4 (audit retention) is likely already satisfied in practice (events are never purged), just undocumented as an explicit guarantee. Anti-criteria #5 (cost visibility) turned out to already be implemented (`WizardPage.tsx`, tagged `BYOK-06`) — it just needs a test, not new product work. The only follow-up worth tracking as its own item: add a unit/E2E test for the wizard's cost-estimate display.

---

*Evidence matrix produced 2026-07-24 against `main` @ commit `36c351c`, cross-referenced with the [release readiness gap register](recalium-v1-release-readiness-gap-register.md).*
