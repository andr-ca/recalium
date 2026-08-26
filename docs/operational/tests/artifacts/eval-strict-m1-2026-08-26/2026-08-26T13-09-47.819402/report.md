# Recalium Evaluation Report

**Date:** 2026-08-26T13:09:47.819402Z

**Status:** ✗ FAILED

## Summary

| Check | Status | Skipped | Key Metrics |
|-------|--------|---------|-------------|
| ingest | ✓ |  | latency_p50_ms=65.42, latency_p95_ms=80.20, latency_p99_ms=82.03 |
| extraction | ✗ | ⊘ |  |
| retrieval | ✗ |  | keyword_recall_at_5=0.12, semantic_recall_at_5=0.12, hybrid_recall_at_5=0.12 |
| sensitivity | ✓ |  | block_verified=1.00, control_allowed=1.00, leaked_fact_count=0.00 |
| mcp | ✓ |  | ingest_accepted=1.00, retrieve_memory_provenance=1.00, retrieve_budget_metadata=1.00 |

## Detailed Findings

### INGEST

**Status:** PASSED

**Details:** Ingested 4/4 conversations. P95 latency: 80ms (threshold: 1000ms). Success rate: 100%.

**Metrics:**

| Metric | Value |
|--------|-------|
| latency_p50_ms | 65.4188 |
| latency_p95_ms | 80.1974 |
| latency_p99_ms | 82.0307 |
| success_rate | 1.0000 |
| count_ingested | 4 |

### EXTRACTION

**Status:** Skipped

**Reason:** No facts extracted for any conversation — likely gate-blocked (see details)

### RETRIEVAL

**Status:** FAILED

**Details:** Retrieval evaluation across 13 queries:
  KEYWORD: R@5=12.50%, R@10=12.50%, MRR=0.12, nDCG=0.12, P95=72ms (adversarial: 2 tested, 0 crashed)
  SEMANTIC: R@5=12.50%, R@10=12.50%, MRR=0.12, nDCG=0.12, P95=717ms (adversarial: 2 tested, 0 crashed)
  HYBRID: R@5=12.50%, R@10=12.50%, MRR=0.12, nDCG=0.12, P95=482ms (adversarial: 2 tested, 0 crashed)
  PARAPHRASE (semantic_only): keyword R@10=0% (expected ~0), semantic R@10=0%, hybrid R@10=0%, semantic_lift=+0% (need ≥66% and lift>0)
Thresholds: R@10≥70% (hybrid), P95≤2000ms, hybrid ≥ best single mode

**Metrics:**

| Metric | Value |
|--------|-------|
| keyword_recall_at_5 | 0.1250 |
| semantic_recall_at_5 | 0.1250 |
| hybrid_recall_at_5 | 0.1250 |
| keyword_recall_at_10 | 0.1250 |
| semantic_recall_at_10 | 0.1250 |
| hybrid_recall_at_10 | 0.1250 |
| keyword_mrr | 0.1250 |
| semantic_mrr | 0.1250 |
| hybrid_mrr | 0.1250 |
| keyword_ndcg_at_10 | 0.1250 |
| semantic_ndcg_at_10 | 0.1250 |
| hybrid_ndcg_at_10 | 0.1250 |
| keyword_latency_p95_ms | 71.8292 |
| semantic_latency_p95_ms | 717.2295 |
| hybrid_latency_p95_ms | 482.0276 |
| keyword_paraphrase_recall_at_10 | 0.0000 |
| semantic_paraphrase_recall_at_10 | 0.0000 |
| hybrid_paraphrase_recall_at_10 | 0.0000 |
| semantic_lift | 0.0000 |
| semantic_mode_available | 1.0000 |

### SENSITIVITY

**Status:** PASSED

**Details:** Audit-based gate verification (F15): 1/1 sensitive conversations have gate audit events; all blocked=True. Control items with gate events: 4, at least one allowed=True (guards against block-everything, F22). Facts leaked from sensitive items: 0 (must be 0). PASS: gate blocks sensitive content while allowing controls.

**Metrics:**

| Metric | Value |
|--------|-------|
| block_verified | 1.0000 |
| control_allowed | 1.0000 |
| leaked_fact_count | 0.0000 |
| sensitive_conversations_tested | 1.0000 |
| gate_events_observed | 5.0000 |

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


*Report generated at 2026-08-26T13:09:47.819402Z*
