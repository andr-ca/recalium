# Recalium Evaluation Report

**Date:** 2026-07-07T18:36:24.654852Z

**Status:** ✓ PASSED

## Summary

| Check | Status | Skipped | Key Metrics |
|-------|--------|---------|-------------|
| ingest | ✓ |  | latency_p50_ms=5.37, latency_p95_ms=9.11, latency_p99_ms=9.64 |
| extraction | ✗ | ⊘ |  |
| retrieval | ✓ |  | keyword_recall_at_5=0.88, keyword_recall_at_10=0.88, keyword_mrr=0.88 |
| sensitivity | ✗ | ⊘ | sensitive_conversations_ingested=1, sensitive_conversations_total=1 |
| mcp | ✓ |  | ingest_accepted=1.00, retrieve_memory_provenance=1.00, retrieve_budget_metadata=1.00 |

## Detailed Findings

### INGEST

**Status:** PASSED

**Details:** Ingested 4/4 conversations. P95 latency: 9ms (threshold: 1000ms). Success rate: 100%.

**Metrics:**

| Metric | Value |
|--------|-------|
| latency_p50_ms | 5.3653 |
| latency_p95_ms | 9.1101 |
| latency_p99_ms | 9.6372 |
| success_rate | 1.0000 |
| count_ingested | 4 |

### EXTRACTION

**Status:** Skipped

**Reason:** No OPENAI_API_KEY, ANTHROPIC_API_KEY, or OLLAMA_BASE_URL in environment

### RETRIEVAL

**Status:** PASSED

**Details:** Retrieval evaluation across 10 queries:
  KEYWORD: R@5=87.50%, R@10=87.50%, MRR=0.88, nDCG=0.88, P95=38ms (adversarial: 2 tested, 0 crashed)
Thresholds: R@10≥70% (hybrid), P95≤2000ms, hybrid ≥ best single mode

**Metrics:**

| Metric | Value |
|--------|-------|
| keyword_recall_at_5 | 0.8750 |
| keyword_recall_at_10 | 0.8750 |
| keyword_mrr | 0.8750 |
| keyword_ndcg_at_10 | 0.8750 |
| keyword_latency_p95_ms | 38.1573 |

### SENSITIVITY

**Status:** Skipped

**Reason:** Sensitivity gate decision is not observable via API — needs an audit event or job field exposing gate category/blocked (see docs/recommendations.md)

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


*Report generated at 2026-07-07T18:36:24.654852Z*
