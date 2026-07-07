"""Sensitivity gate evaluation (personal/relationship fact blocking)."""

import asyncio
from typing import Dict, Any
import httpx

from evals.checks import CheckResult


async def run_check(client: httpx.AsyncClient, golden: Dict[str, Any], settings: Dict[str, Any]) -> CheckResult:
    """
    Evaluate that personal/relationship-labeled facts are blocked from external dispatch.

    Ingests facts labeled with sensitivity_level="personal" or "relationship".
    Verifies via job audit log that these facts were NOT dispatched to external providers
    (job status should be 'deferred' or 'local', not 'completed' with external call).

    No provider key required — validates gate logic via audit, not by triggering calls.

    Args:
        client: httpx.AsyncClient connected to stack
        golden: Parsed golden.json dataset
        settings: Configuration dict

    Returns:
        CheckResult with sensitivity_block_rate metric (must be 1.0)
    """
    # Find conversations with personal/relationship facts
    sensitive_conversations = []

    for conv in golden.get("conversations", []):
        conv_facts = conv.get("facts", [])
        sensitive_facts = [
            f for f in conv_facts
            if f.get("sensitivity_level") in ("personal", "relationship")
        ]

        if sensitive_facts:
            sensitive_conversations.append({
                "conv_id": conv["id"],
                "raw_text": conv["raw_text"],
                "sensitive_facts": sensitive_facts,
            })

    if not sensitive_conversations:
        return CheckResult(
            name="sensitivity",
            passed=True,  # No sensitive data to block = vacuous pass
            metrics={"block_rate": 1.0, "sensitive_facts_tested": 0},
            details="No personal/relationship facts in golden dataset to test",
        )

    # Ingest sensitive conversations (local storage must always accept them —
    # the gate blocks external dispatch, never local capture).
    base_url = settings.get("base_url", "http://localhost:8000")
    ingest_ok = 0

    for conv_info in sensitive_conversations:
        payload = {
            "mode": "text",
            "content": conv_info["raw_text"],
            "source_name": f"eval-sensitivity-{conv_info['conv_id']}",
        }
        try:
            response = await client.post(
                f"{base_url}/api/ingest", json=payload, timeout=5.0,
            )
            if response.status_code in (200, 202) and response.json().get("archive_ids"):
                ingest_ok += 1
        except Exception:
            pass

    # HONEST LIMITATION: the gate's block decision is only written to server
    # logs (dispatcher logs "Sensitivity gate: ... blocked=True"); it is not
    # exposed via job status, audit events, or any API. Without that surface —
    # and without a per-source facts filter — no external eval can verify that
    # sensitive content was withheld from external providers. Reporting a pass
    # here would be false confidence on the product's worst failure mode, so
    # this check is SKIPPED until the gate decision is observable.
    # See docs/recommendations.md (sensitivity-gate observability).
    return CheckResult(
        name="sensitivity",
        passed=False,
        metrics={
            "sensitive_conversations_ingested": ingest_ok,
            "sensitive_conversations_total": len(sensitive_conversations),
        },
        details=(
            f"Ingested {ingest_ok}/{len(sensitive_conversations)} sensitive conversations "
            f"(local capture works). Gate verification NOT POSSIBLE via public API: "
            f"the block decision is logged but not exposed through job status or audit events."
        ),
        skipped=True,
        skip_reason=(
            "Sensitivity gate decision is not observable via API — needs an audit event "
            "or job field exposing gate category/blocked (see docs/recommendations.md)"
        ),
    )
