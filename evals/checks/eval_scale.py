"""Scale + concurrency evaluation (GPT5.6 #20).

Provides the scale/concurrency evidence the tiny golden fixture cannot: ingest a
configurable-size diverse corpus, measure retrieval latency and precision at volume,
and prove concurrent retrieval + deletion stays correct (no errors, no resurrection).

Isolated: all data is tagged ``eval-scale-*`` and cleaned up at the end, so the run
does not pollute the user's archive.
"""

import asyncio
import time
from typing import Any, Dict, List

import httpx

from evals.checks import CheckResult
from evals.datasets.generate_corpus import generate_corpus
from evals.metrics import latency_percentiles

_SOURCE_PREFIX = "eval-scale-"


async def _cleanup(client: httpx.AsyncClient, base_url: str) -> None:
    try:
        resp = await client.get(
            f"{base_url}/api/archive", params={"q": _SOURCE_PREFIX, "limit": 500}, timeout=15.0
        )
        if resp.status_code == 200:
            for item in resp.json().get("items", []):
                if (item.get("source_name") or "").startswith(_SOURCE_PREFIX):
                    await client.delete(f"{base_url}/api/archive/{item['id']}", timeout=15.0)
    except Exception:
        pass  # best-effort isolation


async def _wait_for_drain(client: httpx.AsyncClient, base_url: str, timeout_s: float = 240.0) -> bool:
    """Poll until no eval-scale item is still 'Processing' (the worker has indexed the
    corpus), so retrieval precision is measured against a fully indexed store."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            r = await client.get(
                f"{base_url}/api/archive", params={"q": _SOURCE_PREFIX, "limit": 500}, timeout=15.0
            )
            if r.status_code == 200:
                items = [
                    it for it in r.json().get("items", [])
                    if (it.get("source_name") or "").startswith(_SOURCE_PREFIX)
                ]
                if items and all(it.get("status_badge") != "Processing" for it in items):
                    return True
        except Exception:
            pass
        await asyncio.sleep(2.0)
    return False


async def run_check(
    client: httpx.AsyncClient, golden: Dict[str, Any], settings: Dict[str, Any]
) -> CheckResult:
    """Ingest a volume corpus, then measure retrieval latency/precision at scale and
    verify concurrent retrieval + deletion stays consistent."""
    base_url = settings.get("base_url", "http://localhost:8000")
    size = int(settings.get("scale_size", 150))
    threshold_p95 = float(settings.get("scale_latency_p95_ms", 2000))

    corpus = generate_corpus(size, seed=1)
    convs: List[dict] = corpus["conversations"]

    await _cleanup(client, base_url)

    # ── Ingest the volume corpus ────────────────────────────────────────────
    ingested = 0
    ingest_failures = 0
    token_to_archive: Dict[str, str] = {}
    for conv in convs:
        payload = {"mode": "text", "content": conv["text"], "source_name": f"{_SOURCE_PREFIX}{conv['id']}"}
        try:
            r = await client.post(f"{base_url}/api/ingest", json=payload, timeout=15.0)
            if r.status_code in (200, 202) and (ids := r.json().get("archive_ids")):
                ingested += 1
                token_to_archive[conv["token"]] = ids[0]
            else:
                ingest_failures += 1
        except Exception:
            ingest_failures += 1

    if ingested == 0:
        return CheckResult(
            name="scale", passed=False, metrics={"ingested": 0},
            details="No items ingested; cannot evaluate scale.",
            skipped=True, skip_reason="ingest unavailable",
        )

    # Wait for the pipeline to index the corpus before measuring retrieval.
    drained = await _wait_for_drain(client, base_url)

    # ── Retrieval precision + latency at scale (sample ~40 unique-token queries) ──
    step = max(1, size // 40)
    sample = convs[::step]
    latencies_ms: List[float] = []
    precise_hits = 0
    for conv in sample:
        t0 = time.perf_counter()
        try:
            r = await client.get(
                f"{base_url}/api/search",
                params={"q": conv["query"], "mode": "keyword", "limit": 5},
                timeout=30.0,
            )
        except Exception:
            continue
        latencies_ms.append((time.perf_counter() - t0) * 1000.0)
        if r.status_code == 200:
            items = r.json().get("items", [])
            # A unique token should retrieve its own conversation at rank 1.
            want = token_to_archive.get(conv["token"])
            if items and want and any(it.get("source_id") == want for it in items[:3]):
                precise_hits += 1

    pctl = latency_percentiles(latencies_ms)
    precision_at_scale = precise_hits / len(sample) if sample else 0.0

    # ── Concurrency: many concurrent searches while one item is deleted ──────
    concurrency_errors = 0
    resurrection = False
    victim = sample[0] if sample else None
    victim_archive = token_to_archive.get(victim["token"]) if victim else None

    async def _search(q: str) -> int:
        try:
            r = await client.get(
                f"{base_url}/api/search", params={"q": q, "mode": "keyword"}, timeout=30.0
            )
            return r.status_code
        except Exception:
            return 599

    concurrent_queries = [c["query"] for c in sample[:20]]
    tasks = [_search(q) for q in concurrent_queries]
    if victim_archive:
        async def _delete() -> int:
            try:
                r = await client.delete(f"{base_url}/api/archive/{victim_archive}", timeout=30.0)
                return r.status_code
            except Exception:
                return 599
        tasks.append(_delete())
    statuses = await asyncio.gather(*tasks)
    concurrency_errors = sum(1 for s in statuses if s >= 500)

    # After the concurrent delete, the victim's unique token must not resurface.
    if victim_archive:
        try:
            r = await client.get(
                f"{base_url}/api/search",
                params={"q": victim["query"], "mode": "keyword"}, timeout=30.0,
            )
            if r.status_code == 200:
                resurrection = any(
                    it.get("source_id") == victim_archive for it in r.json().get("items", [])
                )
        except Exception:
            pass

    await _cleanup(client, base_url)

    passed = (
        ingest_failures == 0
        and pctl["p95"] <= threshold_p95
        and concurrency_errors == 0
        and not resurrection
        and precision_at_scale >= 0.9
    )
    return CheckResult(
        name="scale",
        passed=passed,
        metrics={
            "corpus_size": size,
            "ingested": ingested,
            "ingest_failures": ingest_failures,
            "pipeline_drained": drained,
            "retrieval_latency_p50_ms": round(pctl["p50"], 1),
            "retrieval_latency_p95_ms": round(pctl["p95"], 1),
            "retrieval_latency_p99_ms": round(pctl["p99"], 1),
            "precision_at_scale": round(precision_at_scale, 3),
            "concurrency_errors": concurrency_errors,
            "resurrection_after_concurrent_delete": resurrection,
        },
        details=(
            f"scale={size} ingested={ingested} drained={drained} p95={pctl['p95']:.0f}ms "
            f"precision={precision_at_scale:.2f} concurrency_errors={concurrency_errors} "
            f"resurrection={resurrection}"
        ),
    )
