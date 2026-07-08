"""Retrieval quality evaluation (recall, precision, MRR, nDCG, latency)."""

import asyncio
import os
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

    base_url = settings.get("base_url", "http://localhost:8000")

    # Relevance ground truth: golden fact IDs -> parent conversation ->
    # server-assigned archive_ids recorded by the ingest check. Retrieved items
    # are matched on their source_id (works in no-key mode where items are excerpts).
    fact_to_conv = {
        fact["id"]: conv["id"]
        for conv in golden.get("conversations", [])
        for fact in conv.get("facts", [])
    }
    ingested_map: Dict[str, List[str]] = settings.get("ingested_archive_ids", {})
    if not ingested_map:
        return CheckResult(
            name="retrieval",
            passed=False,
            metrics={},
            details="Ingest check did not record archive IDs; cannot resolve relevance labels",
            skipped=True,
            skip_reason="No ingested_archive_ids from ingest check",
        )

    def relevant_archive_ids(fact_ids: List[str]) -> List[str]:
        conv_ids = {fact_to_conv[fid] for fid in fact_ids if fid in fact_to_conv}
        ids: List[str] = []
        for cid in conv_ids:
            ids.extend(ingested_map.get(cid, []))
        return ids

    async def search(query_text: str, mode: str) -> httpx.Response:
        # 30s: semantic queries embed in-process and compete with the worker's
        # CPU-bound pipeline (local LLM + embedding writes) — 10s flaked under load
        return await client.get(
            f"{base_url}/api/search",
            params={"q": query_text, "mode": mode},
            timeout=30.0,
        )

    search_errors: Dict[str, list] = {}

    def record_error(mode: str, exc: Exception) -> None:
        search_errors.setdefault(mode, []).append(f"{type(exc).__name__}: {exc}")

    async def invalidate_cache() -> None:
        # Retrieval service holds a 60s TTL cache; clear it so fresh pipeline
        # output is visible to the queries below.
        try:
            await client.post(f"{base_url}/api/search/invalidate-cache", timeout=5.0)
        except Exception:
            pass

    # Wait (bounded) for the async pipeline to index ingested conversations:
    # poll the first labeled query until a relevant source_id appears. With an
    # LLM provider configured, FTS/embeddings are written AFTER the summarize/
    # extract steps, so allow generous time (override via EVAL_PIPELINE_TIMEOUT_S).
    pipeline_timeout = float(os.getenv("EVAL_PIPELINE_TIMEOUT_S", "300"))
    probe = next(
        (q for q in queries
         if q.get("relevant_fact_ids") and not q.get("semantic_only")),
        None,
    )
    if probe is not None:
        probe_relevant = set(relevant_archive_ids(probe["relevant_fact_ids"]))
        deadline = time.time() + pipeline_timeout
        while time.time() < deadline:
            await invalidate_cache()
            try:
                resp = await search(probe["text"], "keyword")
                if resp.status_code == 200:
                    found = {i.get("source_id") for i in resp.json().get("items", [])}
                    if found & probe_relevant:
                        break
            except Exception:
                pass
            await asyncio.sleep(5)
        await invalidate_cache()

    # Try semantic search; skip if embeddings not available (degraded mode).
    # degraded_mode=False only means SOME embeddings exist (possibly other
    # items') — so additionally wait until a probe-relevant source_id is
    # semantically retrievable, i.e. THIS run's items have embeddings.
    # Embeddings are written last in the pipeline (after LLM steps + FTS).
    modes = ["keyword"]
    semantic_deadline = time.time() + pipeline_timeout
    semantic_available = False
    while time.time() < semantic_deadline:
        try:
            await invalidate_cache()
            test_response = await search(probe["text"] if probe else "test", "semantic")
            if test_response.status_code == 200 and not test_response.json().get("degraded_mode", False):
                semantic_available = True
                found = {i.get("source_id") for i in test_response.json().get("items", [])}
                if probe is None or (found & set(relevant_archive_ids(probe["relevant_fact_ids"]))):
                    break
        except Exception as exc:
            record_error("semantic-probe", exc)
        await asyncio.sleep(5)
    if semantic_available:
        modes.extend(["semantic", "hybrid"])
    await invalidate_cache()

    # Run search for each query and mode
    results_by_mode: Dict[str, Dict] = {mode: {
        "recalls_at_5": [],
        "recalls_at_10": [],
        "mrrs": [],
        "ndcgs": [],
        "latencies_ms": [],
        "adversarial_count": 0,
        "adversarial_crashes": 0,
        # semantic_only paraphrase queries scored separately — keyword/FTS is
        # EXPECTED to miss them; they measure the recall embeddings add
        "para_recalls_at_10": [],
    } for mode in modes}

    for query in queries:
        query_text = query["text"]
        relevant_ids = relevant_archive_ids(query.get("relevant_fact_ids", []))
        is_adversarial = query.get("is_adversarial", False)
        is_paraphrase = query.get("semantic_only", False)

        for mode in modes:
            try:
                start_time = time.time()
                response = await search(query_text, mode)
                elapsed_ms = (time.time() - start_time) * 1000

                if is_adversarial:
                    # Adversarial queries only assert "no server error" (5xx)
                    results_by_mode[mode]["adversarial_count"] += 1
                    if response.status_code >= 500:
                        results_by_mode[mode]["adversarial_crashes"] += 1
                    continue

                if response.status_code != 200:
                    continue

                data = response.json()
                # Rank order of distinct source archives (items share source_id
                # when several excerpts/facts derive from one conversation)
                retrieved_ids: List[str] = []
                for item in data.get("items", []):
                    sid = item.get("source_id")
                    if sid and sid not in retrieved_ids:
                        retrieved_ids.append(sid)

                if not relevant_ids:
                    continue  # No labels for this query; nothing to score

                if is_paraphrase:
                    results_by_mode[mode]["para_recalls_at_10"].append(
                        recall_at_k(relevant_ids, retrieved_ids, 10)
                    )
                    continue  # Excluded from standard averages by design

                # Calculate metrics
                r_at_5 = recall_at_k(relevant_ids, retrieved_ids, 5)
                r_at_10 = recall_at_k(relevant_ids, retrieved_ids, 10)
                m = mrr(relevant_ids, retrieved_ids)

                relevance_scores = [
                    1.0 if rid in relevant_ids else 0.0
                    for rid in retrieved_ids
                ]
                n = ndcg_at_k(relevance_scores, 10)

                results_by_mode[mode]["recalls_at_5"].append(r_at_5)
                results_by_mode[mode]["recalls_at_10"].append(r_at_10)
                results_by_mode[mode]["mrrs"].append(m)
                results_by_mode[mode]["ndcgs"].append(n)
                results_by_mode[mode]["latencies_ms"].append(elapsed_ms)

            except Exception as exc:
                record_error(mode, exc)
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

    total_adversarial_crashes = sum(
        results_by_mode[mode]["adversarial_crashes"] for mode in modes
    )

    # Paraphrase (semantic_only) metrics: measure what embeddings add.
    # semantic_lift = paraphrase recall gained by semantic over keyword.
    def para_recall(mode: str) -> float:
        vals = results_by_mode.get(mode, {}).get("para_recalls_at_10", [])
        return sum(vals) / len(vals) if vals else 0.0

    para_keyword = para_recall("keyword")
    para_semantic = para_recall("semantic")
    para_hybrid = para_recall("hybrid")
    semantic_lift = para_semantic - para_keyword

    para_recall_threshold = 0.66  # at least 2 of 3 paraphrase queries found

    embeddings_ok = True
    if "semantic" in modes:
        embeddings_ok = (
            max(para_semantic, para_hybrid) >= para_recall_threshold
            and semantic_lift > 0
        )

    passed = (
        hybrid_recall >= recall_at_10_threshold and
        hybrid_recall >= best_single_recall * 0.95 and  # Allow 5% variance
        hybrid_metrics.get("latency_p95_ms", float("inf")) <= latency_p95_threshold and
        total_adversarial_crashes == 0 and
        embeddings_ok
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

    if "semantic" in modes:
        details_parts.append(
            f"\n  PARAPHRASE (semantic_only): keyword R@10={para_keyword:.0%} (expected ~0), "
            f"semantic R@10={para_semantic:.0%}, hybrid R@10={para_hybrid:.0%}, "
            f"semantic_lift={semantic_lift:+.0%} (need ≥{para_recall_threshold:.0%} and lift>0)"
        )
    else:
        details_parts.append(
            "\n  PARAPHRASE: not scored — semantic mode unavailable (degraded/no embeddings)"
        )

    if search_errors:
        error_summary = "; ".join(
            f"{mode}: {len(errs)} errors (last: {errs[-1][:120]})"
            for mode, errs in search_errors.items()
        )
        details_parts.append(f"\n  SEARCH ERRORS: {error_summary}")

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
            **{f"{mode}_paraphrase_recall_at_10": para_recall(mode) for mode in modes},
            "semantic_lift": semantic_lift,
            "semantic_mode_available": 1.0 if "semantic" in modes else 0.0,
        },
        details=details,
    )
