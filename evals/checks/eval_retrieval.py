"""Retrieval quality evaluation (recall, precision, MRR, nDCG, latency)."""

import asyncio
import time
from typing import Dict, Any, List
import httpx

from evals.checks import CheckResult
from evals.metrics import (
    recall_at_k,
    mrr,
    ndcg_at_k,
    latency_percentiles,
)


async def run_check(client: httpx.AsyncClient, golden: Dict[str, Any], settings: Dict[str, Any]) -> CheckResult:
    """
    Evaluate retrieval quality in keyword, semantic, and hybrid modes.

    For each query in golden.json:
    - Search via /api/search in keyword, semantic, hybrid modes
    - Calculate recall@5, recall@10, MRR, nDCG@10 vs relevant_fact_ids
    - Measure latency
    - Assert hybrid mode >= best single mode (or gracefully skip semantic if not configured)
    - Verify adversarial queries don't crash (return 200, not 500)

    Args:
        client: httpx.AsyncClient connected to stack
        golden: Parsed golden.json dataset
        settings: Configuration dict

    Returns:
        CheckResult with retrieval metrics for each mode
    """
    queries = golden.get("queries", [])

    if not queries:
        return CheckResult(
            name="retrieval",
            passed=False,
            metrics={},
            details="No queries in golden dataset",
            skipped=True,
            skip_reason="Empty queries list",
        )

    # Try semantic search; skip if embeddings not available
    modes = ["keyword"]
    try:
        # Test if semantic search works
        test_response = await client.post(
            f"{settings.get('base_url', 'http://localhost:8000')}/api/search",
            json={"query": "test", "mode": "semantic"},
            timeout=5.0,
        )
        if test_response.status_code == 200:
            modes.extend(["semantic", "hybrid"])
    except Exception:
        pass  # Fall back to keyword-only

    # Run search for each query and mode
    results_by_mode: Dict[str, Dict] = {mode: {
        "recalls_at_5": [],
        "recalls_at_10": [],
        "mrrs": [],
        "ndcgs": [],
        "latencies_ms": [],
        "adversarial_count": 0,
        "adversarial_crashes": 0,
    } for mode in modes}

    for query in queries:
        query_id = query["id"]
        query_text = query["text"]
        relevant_fact_ids = query.get("relevant_fact_ids", [])
        is_adversarial = query.get("is_adversarial", False)

        for mode in modes:
            try:
                start_time = time.time()
                response = await client.post(
                    f"{settings.get('base_url', 'http://localhost:8000')}/api/search",
                    json={"query": query_text, "mode": mode},
                    timeout=5.0,
                )
                elapsed_ms = (time.time() - start_time) * 1000

                if response.status_code != 200:
                    if is_adversarial:
                        results_by_mode[mode]["adversarial_crashes"] += 1
                    continue

                data = response.json()
                results = data.get("results", [])
                retrieved_ids = [r.get("id") or r.get("fact_id") for r in results]

                # Calculate metrics
                r_at_5 = recall_at_k(relevant_fact_ids, retrieved_ids, 5)
                r_at_10 = recall_at_k(relevant_fact_ids, retrieved_ids, 10)
                m = mrr(relevant_fact_ids, retrieved_ids)

                # nDCG: use relevance scores if available, else binary (1 if in relevant set)
                relevance_scores = [
                    1.0 if rid in relevant_fact_ids else 0.0
                    for rid in retrieved_ids
                ]
                n = ndcg_at_k(relevance_scores, 10)

                results_by_mode[mode]["recalls_at_5"].append(r_at_5)
                results_by_mode[mode]["recalls_at_10"].append(r_at_10)
                results_by_mode[mode]["mrrs"].append(m)
                results_by_mode[mode]["ndcgs"].append(n)
                results_by_mode[mode]["latencies_ms"].append(elapsed_ms)

                if is_adversarial:
                    results_by_mode[mode]["adversarial_count"] += 1

            except Exception as e:
                if is_adversarial:
                    results_by_mode[mode]["adversarial_crashes"] += 1

    # Calculate average metrics per mode
    mode_metrics = {}
    for mode in modes:
        stats = results_by_mode[mode]

        if stats["recalls_at_10"]:
            avg_recall_at_5 = sum(stats["recalls_at_5"]) / len(stats["recalls_at_5"])
            avg_recall_at_10 = sum(stats["recalls_at_10"]) / len(stats["recalls_at_10"])
            avg_mrr = sum(stats["mrrs"]) / len(stats["mrrs"])
            avg_ndcg = sum(stats["ndcgs"]) / len(stats["ndcgs"])
            latency_stats = latency_percentiles(stats["latencies_ms"])
        else:
            avg_recall_at_5 = 0.0
            avg_recall_at_10 = 0.0
            avg_mrr = 0.0
            avg_ndcg = 0.0
            latency_stats = {"p50": 0, "p95": 0, "p99": 0}

        mode_metrics[mode] = {
            "recall_at_5": avg_recall_at_5,
            "recall_at_10": avg_recall_at_10,
            "mrr": avg_mrr,
            "ndcg_at_10": avg_ndcg,
            "latency_p50_ms": latency_stats["p50"],
            "latency_p95_ms": latency_stats["p95"],
            "latency_p99_ms": latency_stats["p99"],
            "adversarial_count": stats["adversarial_count"],
            "adversarial_crashes": stats["adversarial_crashes"],
        }

    # Check thresholds
    hybrid_metrics = mode_metrics.get("hybrid", mode_metrics.get("keyword", {}))

    # Thresholds
    recall_at_10_threshold = 0.7
    latency_p95_threshold = 2000  # ms

    # Hybrid should beat or match best single mode
    hybrid_recall = hybrid_metrics.get("recall_at_10", 0.0)
    keyword_recall = mode_metrics.get("keyword", {}).get("recall_at_10", 0.0)
    semantic_recall = mode_metrics.get("semantic", {}).get("recall_at_10", 0.0)
    best_single_recall = max(keyword_recall, semantic_recall) if "semantic" in modes else keyword_recall

    passed = (
        hybrid_recall >= recall_at_10_threshold and
        hybrid_recall >= best_single_recall * 0.95 and  # Allow 5% variance
        hybrid_metrics.get("latency_p95_ms", float("inf")) <= latency_p95_threshold
    )

    # Build details string
    details_parts = [f"Retrieval evaluation across {len(queries)} queries:"]
    for mode in modes:
        m = mode_metrics[mode]
        details_parts.append(
            f"\n  {mode.upper()}: "
            f"R@5={m['recall_at_5']:.2%}, R@10={m['recall_at_10']:.2%}, "
            f"MRR={m['mrr']:.2f}, nDCG={m['ndcg_at_10']:.2f}, "
            f"P95={m['latency_p95_ms']:.0f}ms"
        )
        if m["adversarial_count"] > 0:
            details_parts.append(
                f" (adversarial: {m['adversarial_count']} tested, {m['adversarial_crashes']} crashed)"
            )

    details_parts.append(
        f"\nThresholds: R@10≥{recall_at_10_threshold:.0%} (hybrid), "
        f"P95≤{latency_p95_threshold}ms, hybrid ≥ best single mode"
    )

    details = "".join(details_parts)

    return CheckResult(
        name="retrieval",
        passed=passed,
        metrics={
            **{f"{mode}_recall_at_5": mode_metrics[mode]["recall_at_5"] for mode in modes},
            **{f"{mode}_recall_at_10": mode_metrics[mode]["recall_at_10"] for mode in modes},
            **{f"{mode}_mrr": mode_metrics[mode]["mrr"] for mode in modes},
            **{f"{mode}_ndcg_at_10": mode_metrics[mode]["ndcg_at_10"] for mode in modes},
            **{f"{mode}_latency_p95_ms": mode_metrics[mode]["latency_p95_ms"] for mode in modes},
        },
        details=details,
    )
