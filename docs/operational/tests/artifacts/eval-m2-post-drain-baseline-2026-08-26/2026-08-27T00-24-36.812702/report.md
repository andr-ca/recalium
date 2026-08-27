# Recalium Evaluation Report

**Date:** 2026-08-27T00:24:36.812702Z

**Status:** ✗ FAILED

## Summary

| Check | Status | Skipped | Key Metrics |
|-------|--------|---------|-------------|
| ingest | ✓ |  | latency_p50_ms=61.87, latency_p95_ms=64.66, latency_p99_ms=65.00 |
| extraction | ✗ |  | recall=0.71, precision=0.62, span_fidelity=1.00 |
| retrieval | ✗ |  | keyword_recall_at_5=0.25, semantic_recall_at_5=0.38, hybrid_recall_at_5=0.38 |
| sensitivity | ✓ |  | block_verified=1.00, leaked_fact_count=0.00, sensitive_conversations_tested=1.00 |
| mcp | ✓ |  | ingest_accepted=1.00, retrieve_memory_provenance=1.00, retrieve_budget_metadata=1.00 |

## Detailed Findings

### INGEST

**Status:** PASSED

**Details:** Aggregated over 3 run(s): Ingested 4/4 conversations. P95 latency: 70ms (threshold: 1000ms). Success rate: 100%.

**Metrics:**

| Metric | Value |
|--------|-------|
| latency_p50_ms | 61.8714 |
| latency_p50_ms_stdev | 4.2058 |
| latency_p95_ms | 64.6622 |
| latency_p95_ms_stdev | 5.0737 |
| latency_p99_ms | 64.9966 |
| latency_p99_ms_stdev | 5.2311 |
| success_rate | 1.0000 |
| success_rate_stdev | 0.0000 |
| count_ingested | 4.0000 |
| count_ingested_stdev | 0.0000 |

### EXTRACTION

**Status:** FAILED

**Details:** Aggregated over 3 run(s): Extraction metrics (avg across 1 conversations, 8 facts): Recall 71.43% (threshold: 60%), Precision 62.50% (threshold: 70%), Span fidelity 100.00% (threshold: 95%), Provenance completeness 100.00% (threshold: 100%; PIPE-02: span+confidence+method+model). INCOMPLETE COVERAGE: 1/3 conversations produced facts within 600s drain (pipeline still Processing; missing: conv-002, conv-004).

**Metrics:**

| Metric | Value |
|--------|-------|
| recall | 0.7143 |
| recall_stdev | 0.0000 |
| precision | 0.6250 |
| precision_stdev | 0.0000 |
| span_fidelity | 1.0000 |
| span_fidelity_stdev | 0.0000 |
| provenance_completeness | 1.0000 |
| provenance_completeness_stdev | 0.0000 |
| count_facts | 8.0000 |
| count_facts_stdev | 0.0000 |
| count_conversations | 1.0000 |
| count_conversations_stdev | 0.0000 |
| count_conversations_expected | 3.0000 |
| count_conversations_expected_stdev | 0.0000 |

### RETRIEVAL

**Status:** FAILED

**Details:** Aggregated over 3 run(s): Retrieval evaluation across 13 queries:
  KEYWORD: R@5=25.00%, R@10=25.00%, MRR=0.25, nDCG=0.25, P95=109ms (adversarial: 2 tested, 0 crashed)
  SEMANTIC: R@5=37.50%, R@10=37.50%, MRR=0.38, nDCG=0.38, P95=2170ms (adversarial: 2 tested, 0 crashed)
  HYBRID: R@5=37.50%, R@10=37.50%, MRR=0.38, nDCG=0.38, P95=2196ms (adversarial: 2 tested, 0 crashed)
  PARAPHRASE (semantic_only): keyword R@10=0% (expected ~0), semantic R@10=33%, hybrid R@10=33%, semantic_lift=+33% (need ≥66% and lift>0)
Thresholds: R@10≥70% (hybrid), P95≤2000ms, hybrid ≥ best single mode

**Metrics:**

| Metric | Value |
|--------|-------|
| keyword_recall_at_5 | 0.2500 |
| keyword_recall_at_5_stdev | 0.0000 |
| semantic_recall_at_5 | 0.3750 |
| semantic_recall_at_5_stdev | 0.0000 |
| hybrid_recall_at_5 | 0.3750 |
| hybrid_recall_at_5_stdev | 0.0000 |
| keyword_recall_at_10 | 0.2500 |
| keyword_recall_at_10_stdev | 0.0000 |
| semantic_recall_at_10 | 0.3750 |
| semantic_recall_at_10_stdev | 0.0000 |
| hybrid_recall_at_10 | 0.3750 |
| hybrid_recall_at_10_stdev | 0.0000 |
| keyword_mrr | 0.2500 |
| keyword_mrr_stdev | 0.0000 |
| semantic_mrr | 0.3750 |
| semantic_mrr_stdev | 0.0000 |
| hybrid_mrr | 0.3750 |
| hybrid_mrr_stdev | 0.0000 |
| keyword_ndcg_at_10 | 0.2500 |
| keyword_ndcg_at_10_stdev | 0.0000 |
| semantic_ndcg_at_10 | 0.3750 |
| semantic_ndcg_at_10_stdev | 0.0000 |
| hybrid_ndcg_at_10 | 0.3750 |
| hybrid_ndcg_at_10_stdev | 0.0000 |
| keyword_latency_p95_ms | 112.2738 |
| keyword_latency_p95_ms_stdev | 21.8309 |
| semantic_latency_p95_ms | 2022.1281 |
| semantic_latency_p95_ms_stdev | 188.4923 |
| hybrid_latency_p95_ms | 2211.9921 |
| hybrid_latency_p95_ms_stdev | 159.7117 |
| keyword_paraphrase_recall_at_10 | 0.0000 |
| keyword_paraphrase_recall_at_10_stdev | 0.0000 |
| semantic_paraphrase_recall_at_10 | 0.4444 |
| semantic_paraphrase_recall_at_10_stdev | 0.1925 |
| hybrid_paraphrase_recall_at_10 | 0.4444 |
| hybrid_paraphrase_recall_at_10_stdev | 0.1925 |
| semantic_lift | 0.4444 |
| semantic_lift_stdev | 0.1925 |
| semantic_mode_available | 1.0000 |
| semantic_mode_available_stdev | 0.0000 |

### SENSITIVITY

**Status:** PASSED

**Details:** Aggregated over 3 run(s): Differential gate test (no audit events — server predates F15): 1 sensitive conversations processed; 0 facts derived from them (must be 0) while control conversations produced facts. Gate BLOCKED sensitive content from extraction.

**Metrics:**

| Metric | Value |
|--------|-------|
| block_verified | 1.0000 |
| block_verified_stdev | 0.0000 |
| leaked_fact_count | 0.0000 |
| leaked_fact_count_stdev | 0.0000 |
| sensitive_conversations_tested | 1.0000 |
| sensitive_conversations_tested_stdev | 0.0000 |

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


*Report generated at 2026-08-27T00:24:36.812702Z*
