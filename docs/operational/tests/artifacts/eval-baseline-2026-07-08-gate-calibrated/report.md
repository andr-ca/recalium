# Recalium Evaluation Report

**Date:** 2026-07-08T02:49:29.313940Z

**Status:** ✗ FAILED

## Summary

| Check | Status | Skipped | Key Metrics |
|-------|--------|---------|-------------|
| ingest | ✓ |  | latency_p50_ms=21.15, latency_p95_ms=22.74, latency_p99_ms=22.92 |
| extraction | ✗ |  | recall=0.58, precision=0.66, span_fidelity=1.00 |
| retrieval | ✓ |  | keyword_recall_at_5=0.62, semantic_recall_at_5=0.88, hybrid_recall_at_5=0.88 |
| sensitivity | ✓ |  | block_verified=1.00, control_allowed=1.00, leaked_fact_count=0.00 |
| mcp | ✓ |  | ingest_accepted=1.00, retrieve_memory_provenance=1.00, retrieve_budget_metadata=1.00 |

## Detailed Findings

### INGEST

**Status:** PASSED

**Details:** Ingested 4/4 conversations. P95 latency: 23ms (threshold: 1000ms). Success rate: 100%.

**Metrics:**

| Metric | Value |
|--------|-------|
| latency_p50_ms | 21.1514 |
| latency_p95_ms | 22.7436 |
| latency_p99_ms | 22.9232 |
| success_rate | 1.0000 |
| count_ingested | 4 |

### EXTRACTION

**Status:** FAILED

**Details:** Extraction metrics (avg across 3 conversations, 19 facts): Recall 57.74% (threshold: 60%), Precision 65.61% (threshold: 70%), Span fidelity 100.00% (threshold: 95%), Provenance completeness 100.00% (threshold: 100%; PIPE-02: span+confidence+method+model).

**Metrics:**

| Metric | Value |
|--------|-------|
| recall | 0.5774 |
| precision | 0.6561 |
| span_fidelity | 1.0000 |
| provenance_completeness | 1.0000 |
| count_facts | 19 |
| count_conversations | 3 |

### RETRIEVAL

**Status:** PASSED

**Details:** Retrieval evaluation across 13 queries:
  KEYWORD: R@5=62.50%, R@10=62.50%, MRR=0.38, nDCG=0.44, P95=26ms (adversarial: 2 tested, 0 crashed)
  SEMANTIC: R@5=87.50%, R@10=87.50%, MRR=0.62, nDCG=0.69, P95=111ms (adversarial: 2 tested, 0 crashed)
  HYBRID: R@5=87.50%, R@10=87.50%, MRR=0.62, nDCG=0.69, P95=121ms (adversarial: 2 tested, 0 crashed)
  PARAPHRASE (semantic_only): keyword R@10=0% (expected ~0), semantic R@10=100%, hybrid R@10=100%, semantic_lift=+100% (need ≥66% and lift>0)
Thresholds: R@10≥70% (hybrid), P95≤2000ms, hybrid ≥ best single mode

**Metrics:**

| Metric | Value |
|--------|-------|
| keyword_recall_at_5 | 0.6250 |
| semantic_recall_at_5 | 0.8750 |
| hybrid_recall_at_5 | 0.8750 |
| keyword_recall_at_10 | 0.6250 |
| semantic_recall_at_10 | 0.8750 |
| hybrid_recall_at_10 | 0.8750 |
| keyword_mrr | 0.3750 |
| semantic_mrr | 0.6250 |
| hybrid_mrr | 0.6250 |
| keyword_ndcg_at_10 | 0.4405 |
| semantic_ndcg_at_10 | 0.6905 |
| hybrid_ndcg_at_10 | 0.6905 |
| keyword_latency_p95_ms | 26.2887 |
| semantic_latency_p95_ms | 110.7445 |
| hybrid_latency_p95_ms | 121.1650 |
| keyword_paraphrase_recall_at_10 | 0.0000 |
| semantic_paraphrase_recall_at_10 | 1.0000 |
| hybrid_paraphrase_recall_at_10 | 1.0000 |
| semantic_lift | 1.0000 |
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

- **extraction:** Extraction recall < 0.6 may indicate:
  - F3 (truncation on long conversations): test with long_conversation.json
  - F4 (hallucinated spans filtering): verify span_fidelity metric

*Report generated at 2026-07-08T02:49:29.313940Z*
