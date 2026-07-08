# Recalium Evaluation Report

**Date:** 2026-07-08T00:23:48.508113Z

**Status:** ✓ PASSED

## Summary

| Check | Status | Skipped | Key Metrics |
|-------|--------|---------|-------------|
| ingest | ✓ |  | latency_p50_ms=21.11, latency_p95_ms=21.41, latency_p99_ms=21.42 |
| extraction | ✗ | ⊘ |  |
| retrieval | ✓ |  | keyword_recall_at_5=0.88, semantic_recall_at_5=1.00, hybrid_recall_at_5=1.00 |
| sensitivity | ✗ | ⊘ | leaked_fact_count=0.00 |
| mcp | ✓ |  | ingest_accepted=1.00, retrieve_memory_provenance=1.00, retrieve_budget_metadata=1.00 |

## Detailed Findings

### INGEST

**Status:** PASSED

**Details:** Ingested 4/4 conversations. P95 latency: 21ms (threshold: 1000ms). Success rate: 100%.

**Metrics:**

| Metric | Value |
|--------|-------|
| latency_p50_ms | 21.1067 |
| latency_p95_ms | 21.4104 |
| latency_p99_ms | 21.4171 |
| success_rate | 1.0000 |
| count_ingested | 4 |

### EXTRACTION

**Status:** Skipped

**Reason:** No facts extracted for any conversation — likely gate-blocked (see details)

### RETRIEVAL

**Status:** PASSED

**Details:** Retrieval evaluation across 13 queries:
  KEYWORD: R@5=87.50%, R@10=87.50%, MRR=0.88, nDCG=0.88, P95=26ms (adversarial: 2 tested, 0 crashed)
  SEMANTIC: R@5=100.00%, R@10=100.00%, MRR=1.00, nDCG=1.00, P95=116ms (adversarial: 2 tested, 0 crashed)
  HYBRID: R@5=100.00%, R@10=100.00%, MRR=1.00, nDCG=1.00, P95=122ms (adversarial: 2 tested, 0 crashed)
  PARAPHRASE (semantic_only): keyword R@10=0% (expected ~0), semantic R@10=100%, hybrid R@10=100%, semantic_lift=+100% (need ≥66% and lift>0)
Thresholds: R@10≥70% (hybrid), P95≤2000ms, hybrid ≥ best single mode

**Metrics:**

| Metric | Value |
|--------|-------|
| keyword_recall_at_5 | 0.8750 |
| semantic_recall_at_5 | 1.0000 |
| hybrid_recall_at_5 | 1.0000 |
| keyword_recall_at_10 | 0.8750 |
| semantic_recall_at_10 | 1.0000 |
| hybrid_recall_at_10 | 1.0000 |
| keyword_mrr | 0.8750 |
| semantic_mrr | 1.0000 |
| hybrid_mrr | 1.0000 |
| keyword_ndcg_at_10 | 0.8750 |
| semantic_ndcg_at_10 | 1.0000 |
| hybrid_ndcg_at_10 | 1.0000 |
| keyword_latency_p95_ms | 26.0683 |
| semantic_latency_p95_ms | 116.0480 |
| hybrid_latency_p95_ms | 121.7408 |
| keyword_paraphrase_recall_at_10 | 0.0000 |
| semantic_paraphrase_recall_at_10 | 1.0000 |
| hybrid_paraphrase_recall_at_10 | 1.0000 |
| semantic_lift | 1.0000 |
| semantic_mode_available | 1.0000 |

### SENSITIVITY

**Status:** Skipped

**Reason:** Extraction control did not produce facts — differential test inconclusive

### MCP

**Status:** PASSED

**Details:** MCP protocol (SSE) contract: ingest_accepted=✓, retrieve_provenance=✓, retrieve_budget_metadata=✓, structured_errors=✓.

**Metrics:**

| Metric | Value |
|--------|-------|
| ingest_accepted | 1.0000 |
| retrieve_memory_provenance | 1.0000 |
| retrieve_budget_metadata | 1.0000 |
| structured_error_correctness | 1.0000 |

## Threshold Comparison

| Metric | Threshold | Operator | Status |
|--------|-----------|----------|--------|

## Recommendations


*Report generated at 2026-07-08T00:23:48.508113Z*
