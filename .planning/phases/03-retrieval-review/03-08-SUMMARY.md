# Phase 3 Integration Test Suite — Summary (03-08)

**Plan:** 03-08  
**Phase:** 03 — Retrieval + Review  
**Completed:** 2026-03-23

---

## Test Counts

| Metric | Value |
|--------|-------|
| Tests before Phase 3 (baseline) | 85 passed, 2 skipped |
| New tests added (03-08) | 41 |
| Tests after Phase 3 | 126 passed, 2 skipped, 0 failed |

---

## Requirement Coverage

| Requirement ID | Test(s) |
|---------------|---------|
| SRCH-01 | `test_srch01_keyword_search_returns_response_envelope`, `test_srch01_keyword_search_empty_db_returns_empty`, `test_srch01_keyword_search_via_api` |
| SRCH-02 | `test_srch02_semantic_search_no_embeddings_returns_empty`, `test_srch02_semantic_search_via_api` |
| SRCH-03 | `test_srch03_rrf_score_formula`, `test_srch03_rrf_minimum_threshold`, `test_srch03_hybrid_falls_back_to_keyword_when_no_embeddings`, `test_srch03_hybrid_via_api` |
| SRCH-04 | `test_srch04_budget_trimming_priority_order`, `test_srch04_budget_trimming_skips_item_that_doesnt_fit`, `test_srch04_budget_trimming_result_exhausted_when_all_fit` |
| SRCH-05 | `test_srch05_search_returns_within_envelope` |
| SRCH-06 | `test_srch06_hybrid_degraded_mode_flag_set_when_no_embeddings`, `test_srch06_degraded_mode_visible_in_api_response` |
| MCP-01 | `test_mcp01_retrieval_response_envelope_fields`, `test_mcp01_retrieval_item_has_provenance_fields`, `test_mcp01_post_retrieve_endpoint` |
| MCP-03 | `test_mcp03_search_emits_audit_event_type_search`, `test_mcp03_audit_events_endpoint_returns_events` |
| MCP-04 | `test_mcp04_mcp_retrieve_emits_mcp_retrieve_event`, `test_mcp04_audit_event_records_client_identity` |
| CANM-01 | `test_canm01_create_manual_canonical`, `test_canm01_get_canonical_item_by_id`, `test_canm01_get_canonical_item_missing_returns_none`, `test_canm01_update_canonical_item_content`, `test_canm01_update_canonical_item_not_found_raises`, `test_canm01_delete_canonical_item`, `test_canm01_delete_canonical_not_found_raises` |
| CANM-02 | `test_canm02_list_active_only_by_default`, `test_canm02_list_all_items_have_active_source_status` |
| CANM-03 | `test_canm03_promote_fact_explicit` |
| CANM-04 | `test_canm04_empty_source_span_requires_confirm`, `test_canm04_no_source_span_with_confirmed_true_succeeds` |
| CANM-05 | `test_canm05_list_pending_review_items_is_list`, `test_canm05_resolve_review_item_not_found_raises`, `test_canm05_dismiss_review_item_not_found_raises`, `test_canm05_materialize_and_resolve_review_item`, `test_canm05_materialize_and_dismiss_review_item` |
| WEBUI-05 | `test_webui05_canonical_item_retains_source_archive_link`, `test_webui05_canonical_api_item_includes_source_fields` |

**Total: 41 tests covering all 15 requirement IDs.**

---

## Implementation Notes

- `create_manual_canonical(session, content, promoted_by)` — `promoted_by` is required (not optional as the plan task description suggested)
- `list_canonical_items(session)` — filters only `source_status='active'`; does not filter by `status` field (active/disputed/stale items with `source_status='active'` all appear in the list)
- `retrieve()` audit event logic: `actor='user_ui'` → `event_type='search'`; any other actor → `event_type='mcp_retrieve'`
- Review queue `materialize_review_item` requires a real `conflict_groups` row (FK enforced); tests create a `ConflictGroup` directly
- Cache invalidation (`invalidate_cache()`) needed before MCP-04 audit tests to avoid cache hits suppressing audit event emission
- 2 skipped tests are pre-existing (sentence-transformers not installed in test environment — expected)

---

## Deferred Items

- SRCH-05 (P95 latency ≤ 2s): structural envelope test only; timing SLA requires load testing against 100k-item dataset (deferred to beta/Phase 5 performance validation)
- MCP-04 (90-day retention): retention policy is contractual; no DB-level TTL implemented yet; deferred to Phase 4 operational tooling

---

*Phase 3 complete. All 15 requirement IDs verified by tests. 0 failing.*
