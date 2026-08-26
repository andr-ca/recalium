# Recalium Evaluation Report

**Date:** 2026-08-26T13:39:40.902250Z

**Status:** ✓ PASSED

## Summary

| Check | Status | Skipped | Key Metrics |
|-------|--------|---------|-------------|
| ingest | ✓ |  | latency_p50_ms=40.06, latency_p95_ms=41.64, latency_p99_ms=41.72 |
| extraction | ✓ |  | recall=0.69, precision=0.71, span_fidelity=1.00 |
| retrieval | ✓ |  | keyword_recall_at_5=0.50, semantic_recall_at_5=0.75, hybrid_recall_at_5=0.75 |
| sensitivity | ✓ |  | block_verified=1.00, control_allowed=1.00, leaked_fact_count=0.00 |
| mcp | ✓ |  | ingest_accepted=1.00, retrieve_memory_provenance=1.00, retrieve_budget_metadata=1.00 |

## Detailed Findings

### INGEST

**Status:** PASSED

**Details:** Ingested 4/4 conversations. P95 latency: 42ms (threshold: 1000ms). Success rate: 100%.

**Metrics:**

| Metric | Value |
|--------|-------|
| latency_p50_ms | 40.0596 |
| latency_p95_ms | 41.6405 |
| latency_p99_ms | 41.7212 |
| success_rate | 1.0000 |
| count_ingested | 4 |

### EXTRACTION

**Status:** PASSED

**Details:** Extraction metrics (avg across 2 conversations, 18 facts): Recall 69.05% (threshold: 60%), Precision 71.25% (threshold: 70%), Span fidelity 100.00% (threshold: 95%), Provenance completeness 100.00% (threshold: 100%; PIPE-02: span+confidence+method+model).

**Metrics:**

| Metric | Value |
|--------|-------|
| recall | 0.6905 |
| precision | 0.7125 |
| span_fidelity | 1.0000 |
| provenance_completeness | 1.0000 |
| count_facts | 18 |
| count_conversations | 2 |

### RETRIEVAL

**Status:** PASSED

**Details:** Retrieval evaluation across 13 queries:
  KEYWORD: R@5=50.00%, R@10=50.00%, MRR=0.44, nDCG=0.45, P95=100ms (adversarial: 2 tested, 0 crashed)
  SEMANTIC: R@5=75.00%, R@10=75.00%, MRR=0.54, nDCG=0.60, P95=1550ms (adversarial: 2 tested, 0 crashed)
  HYBRID: R@5=75.00%, R@10=75.00%, MRR=0.54, nDCG=0.60, P95=1663ms (adversarial: 2 tested, 0 crashed)
  PARAPHRASE (semantic_only): keyword R@10=0% (expected ~0), semantic R@10=67%, hybrid R@10=67%, semantic_lift=+67% (need ≥66% and lift>0)
Thresholds: R@10≥70% (hybrid), P95≤2000ms, hybrid ≥ best single mode

**Metrics:**

| Metric | Value |
|--------|-------|
| keyword_recall_at_5 | 0.5000 |
| semantic_recall_at_5 | 0.7500 |
| hybrid_recall_at_5 | 0.7500 |
| keyword_recall_at_10 | 0.5000 |
| semantic_recall_at_10 | 0.7500 |
| hybrid_recall_at_10 | 0.7500 |
| keyword_mrr | 0.4375 |
| semantic_mrr | 0.5417 |
| hybrid_mrr | 0.5417 |
| keyword_ndcg_at_10 | 0.4539 |
| semantic_ndcg_at_10 | 0.5952 |
| hybrid_ndcg_at_10 | 0.5952 |
| keyword_latency_p95_ms | 99.6932 |
| semantic_latency_p95_ms | 1549.5458 |
| hybrid_latency_p95_ms | 1663.4194 |
| keyword_paraphrase_recall_at_10 | 0.0000 |
| semantic_paraphrase_recall_at_10 | 0.6667 |
| hybrid_paraphrase_recall_at_10 | 0.6667 |
| semantic_lift | 0.6667 |
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


*Report generated at 2026-08-26T13:39:40.902250Z*
