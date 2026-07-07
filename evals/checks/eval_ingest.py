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

    base_url = settings.get("base_url", "http://localhost:8000")

    # Idempotency: soft-delete leftovers from previous eval runs first, so
    # relevance labels (this run's archive IDs) aren't shadowed by identical
    # already-indexed copies, and the user's archive doesn't accumulate dupes.
    try:
        resp = await client.get(
            f"{base_url}/api/archive",
            params={"q": "eval-", "limit": 200},
            timeout=10.0,
        )
        if resp.status_code == 200:
            for item in resp.json().get("items", []):
                if (item.get("source_name") or "").startswith("eval-"):
                    await client.delete(f"{base_url}/api/archive/{item['id']}", timeout=10.0)
    except Exception:
        pass  # Cleanup is best-effort; duplicates only degrade recall

    # conv_id -> list[archive_id] mapping, shared with downstream checks
    # (retrieval relevance is resolved against these server-assigned IDs)
    ingested_map: Dict[str, list] = settings.setdefault("ingested_archive_ids", {})

    for conv in golden.get("conversations", []):
        conv_id = conv["id"]
        raw_text = conv["raw_text"]

        # HTTP ingest contract (POST /api/ingest): mode/content/source_name.
        # source_name tags eval items so they stay identifiable in the archive.
        payload = {
            "mode": "text",
            "content": raw_text,
            "source_name": f"eval-{conv_id}",
        }

        try:
            start_time = time.time()
            response = await client.post(
                f"{settings.get('base_url', 'http://localhost:8000')}/api/ingest",
                json=payload,
                timeout=5.0,
            )
            elapsed_ms = (time.time() - start_time) * 1000

            # API returns 202 Accepted with archive_ids
            if response.status_code in (200, 202):
                data = response.json()
                archive_ids = data.get("archive_ids", [])
                if archive_ids:
                    successes += 1
                    latencies_ms.append(elapsed_ms)
                    ingested_map[conv_id] = archive_ids
                else:
                    failures += 1
            else:
                failures += 1

        except Exception:
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
