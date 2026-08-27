# Recalium Evaluation Report

**Date:** 2026-08-27T01:56:27.691259Z

**Status:** ✗ FAILED

## Summary

| Check | Status | Skipped | Key Metrics |
|-------|--------|---------|-------------|
| ingest | ✓ |  | latency_p50_ms=45.16, latency_p95_ms=49.23, latency_p99_ms=49.47 |
| extraction | ✗ |  | recall=0.70, precision=0.67, span_fidelity=1.00 |
| retrieval | ✓ |  | keyword_recall_at_5=0.67, semantic_recall_at_5=0.92, hybrid_recall_at_5=0.92 |
| sensitivity | ✓ |  | block_verified=1.00, control_allowed=1.00, leaked_fact_count=0.00 |
| mcp | ✓ |  | ingest_accepted=1.00, retrieve_memory_provenance=1.00, retrieve_budget_metadata=1.00 |

## Detailed Findings

### INGEST

**Status:** PASSED

**Details:** Aggregated over 3 run(s): Ingested 4/4 conversations. P95 latency: 37ms (threshold: 1000ms). Success rate: 100%.

**Metrics:**

| Metric | Value |
|--------|-------|
| latency_p50_ms | 45.1640 |
| latency_p50_ms_stdev | 7.8890 |
| latency_p95_ms | 49.2295 |
| latency_p95_ms_stdev | 10.9337 |
| latency_p99_ms | 49.4692 |
| latency_p99_ms_stdev | 11.1244 |
| success_rate | 1.0000 |
| success_rate_stdev | 0.0000 |
| count_ingested | 4.0000 |
| count_ingested_stdev | 0.0000 |

### EXTRACTION

**Status:** FAILED

**Details:** Aggregated over 3 run(s): Extraction metrics (avg across 3 conversations, 28 facts): Recall 69.84% (threshold: 60%), Precision 64.17% (threshold: 70%), Span fidelity 100.00% (threshold: 95%), Provenance completeness 100.00% (threshold: 100%; PIPE-02: span+confidence+method+model).

**Metrics:**

| Metric | Value |
|--------|-------|
| recall | 0.6958 |
| recall_stdev | 0.0046 |
| precision | 0.6653 |
| precision_stdev | 0.0409 |
| span_fidelity | 1.0000 |
| span_fidelity_stdev | 0.0000 |
| provenance_completeness | 1.0000 |
| provenance_completeness_stdev | 0.0000 |
| count_facts | 24.6667 |
| count_facts_stdev | 5.7735 |
| count_conversations | 2.6667 |
| count_conversations_stdev | 0.5774 |
| count_conversations_expected | 3.0000 |
| count_conversations_expected_stdev | 0.0000 |

### RETRIEVAL

**Status:** PASSED

**Details:** Aggregated over 3 run(s): Retrieval evaluation across 13 queries:
  KEYWORD: R@5=75.00%, R@10=75.00%, MRR=0.56, nDCG=0.61, P95=101ms (adversarial: 2 tested, 0 crashed)
  SEMANTIC: R@5=100.00%, R@10=100.00%, MRR=0.66, nDCG=0.74, P95=603ms (adversarial: 2 tested, 0 crashed)
  HYBRID: R@5=100.00%, R@10=100.00%, MRR=0.48, nDCG=0.61, P95=627ms (adversarial: 2 tested, 0 crashed)
  PARAPHRASE (semantic_only): keyword R@10=0% (expected ~0), semantic R@10=100%, hybrid R@10=100%, semantic_lift=+100% (need ≥66% and lift>0)
Thresholds: R@10≥70% (hybrid), P95≤2000ms, hybrid ≥ best single mode

**Metrics:**

| Metric | Value |
|--------|-------|
| keyword_recall_at_5 | 0.6667 |
| keyword_recall_at_5_stdev | 0.1443 |
| semantic_recall_at_5 | 0.9167 |
| semantic_recall_at_5_stdev | 0.1443 |
| hybrid_recall_at_5 | 0.9167 |
| hybrid_recall_at_5_stdev | 0.1443 |
| keyword_recall_at_10 | 0.6667 |
| keyword_recall_at_10_stdev | 0.1443 |
| semantic_recall_at_10 | 0.9167 |
| semantic_recall_at_10_stdev | 0.1443 |
| hybrid_recall_at_10 | 0.9167 |
| hybrid_recall_at_10_stdev | 0.1443 |
| keyword_mrr | 0.5208 |
| keyword_mrr_stdev | 0.0722 |
| semantic_mrr | 0.6181 |
| semantic_mrr_stdev | 0.0662 |
| hybrid_mrr | 0.4792 |
| hybrid_mrr_stdev | 0.0000 |
| keyword_ndcg_at_10 | 0.5590 |
| keyword_ndcg_at_10_stdev | 0.0911 |
| semantic_ndcg_at_10 | 0.6946 |
| semantic_ndcg_at_10_stdev | 0.0861 |
| hybrid_ndcg_at_10 | 0.5927 |
| hybrid_ndcg_at_10_stdev | 0.0378 |
| keyword_latency_p95_ms | 106.1509 |
| keyword_latency_p95_ms_stdev | 5.6517 |
| semantic_latency_p95_ms | 977.4133 |
| semantic_latency_p95_ms_stdev | 616.6847 |
| hybrid_latency_p95_ms | 945.1206 |
| hybrid_latency_p95_ms_stdev | 528.1407 |
| keyword_paraphrase_recall_at_10 | 0.0000 |
| keyword_paraphrase_recall_at_10_stdev | 0.0000 |
| semantic_paraphrase_recall_at_10 | 1.0000 |
| semantic_paraphrase_recall_at_10_stdev | 0.0000 |
| hybrid_paraphrase_recall_at_10 | 1.0000 |
| hybrid_paraphrase_recall_at_10_stdev | 0.0000 |
| semantic_lift | 1.0000 |
| semantic_lift_stdev | 0.0000 |
| semantic_mode_available | 1.0000 |
| semantic_mode_available_stdev | 0.0000 |

### SENSITIVITY

**Status:** PASSED

**Details:** Aggregated over 3 run(s): Audit-based gate verification (F15): 1/1 sensitive conversations have gate audit events; all blocked=True. Control items with gate events: 4, at least one allowed=True (guards against block-everything, F22). Facts leaked from sensitive items: 0 (must be 0). PASS: gate blocks sensitive content while allowing controls.

**Metrics:**

| Metric | Value |
|--------|-------|
| block_verified | 1.0000 |
| block_verified_stdev | 0.0000 |
| control_allowed | 1.0000 |
| control_allowed_stdev | 0.0000 |
| leaked_fact_count | 0.0000 |
| leaked_fact_count_stdev | 0.0000 |
| sensitive_conversations_tested | 1.0000 |
| sensitive_conversations_tested_stdev | 0.0000 |
| gate_events_observed | 5.0000 |
| gate_events_observed_stdev | 0.0000 |

### MCP

**Status:** PASSED

**Details:** Aggregated over 3 run(s): MCP protocol (SSE) contract: ingest_accepted=✓, retrieve_provenance=✓, retrieve_budget_metadata=✓, structured_errors=✓.

**Metrics:**

| Metric | Value |
|--------|-------|
| ingest_accepted | 1.0000 |
| ingest_accepted_stdev | 0.0000 |
| retrieve_memory_provenance | 1.0000 |
| retrieve_memory_provenance_stdev | 0.0000 |
| retrieve_budget_metadata | 1.0000 |
| retrieve_budget_metadata_stdev | 0.0000 |
| structured_error_correctness | 1.0000 |
| structured_error_correctness_stdev | 0.0000 |

## Threshold Comparison

| Metric | Threshold | Operator | Status |
|--------|-----------|----------|--------|

## Recommendations


*Report generated at 2026-08-27T01:56:27.691259Z*
