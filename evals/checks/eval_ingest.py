"""Ingest latency and success rate evaluation."""

import asyncio
import time
from typing import Dict, Any
import httpx

from evals.checks import CheckResult
from evals.metrics import latency_percentiles


async def run_check(client: httpx.AsyncClient, golden: Dict[str, Any], settings: Dict[str, Any]) -> CheckResult:
    """
    Evaluate ingest latency P95 and success rate.

    Ingests each golden conversation via /api/ingest and measures:
    - Latency per ingest (should be ≤1s P95 per product claim)
    - Success rate (no 500 errors)
    - Response format (has canonical ID)

    Args:
        client: httpx.AsyncClient connected to stack
        golden: Parsed golden.json dataset
        settings: Configuration dict with base_url

    Returns:
        CheckResult with ingest_latency_p95_ms, success_rate metrics
    """
    latencies_ms = []
    successes = 0
    failures = 0

    for conv in golden.get("conversations", []):
        conv_id = conv["id"]
        raw_text = conv["raw_text"]

        # Prepare ingest payload
        payload = {
            "content": raw_text,
            "source_metadata": {
                "source": conv.get("source", "synthetic_test"),
                "title": conv.get("title", ""),
                "import_method": conv.get("metadata", {}).get("import_method", "eval_test"),
            },
            "idempotency_key": f"eval-{conv_id}",
            "sensitivity_hint": "public",
        }

        try:
            start_time = time.time()
            response = await client.post(
                f"{settings.get('base_url', 'http://localhost:8000')}/api/ingest",
                json=payload,
                timeout=5.0,
            )
            elapsed_ms = (time.time() - start_time) * 1000

            if response.status_code == 200:
                data = response.json()
                if "canonical_id" in data or "id" in data:
                    successes += 1
                    latencies_ms.append(elapsed_ms)
                else:
                    failures += 1
            else:
                failures += 1

        except Exception as e:
            failures += 1

    total = successes + failures
    if total == 0:
        return CheckResult(
            name="ingest",
            passed=False,
            metrics={},
            details="No ingests attempted",
            skipped=True,
            skip_reason="No conversations in golden dataset",
        )

    success_rate = successes / total
    latency_stats = latency_percentiles(latencies_ms) if latencies_ms else {"p50": 0, "p95": 0, "p99": 0}

    # Check thresholds
    p95_threshold = 1000  # ms
    passed = success_rate == 1.0 and latency_stats["p95"] <= p95_threshold

    details = f"Ingested {successes}/{total} conversations. P95 latency: {latency_stats['p95']:.0f}ms (threshold: {p95_threshold}ms). Success rate: {success_rate:.0%}."

    return CheckResult(
        name="ingest",
        passed=passed,
        metrics={
            "latency_p50_ms": latency_stats["p50"],
            "latency_p95_ms": latency_stats["p95"],
            "latency_p99_ms": latency_stats["p99"],
            "success_rate": success_rate,
            "count_ingested": successes,
        },
        details=details,
    )
