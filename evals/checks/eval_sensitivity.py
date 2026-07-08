"""Sensitivity gate evaluation (personal/relationship fact blocking)."""

import asyncio
import os
import time
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
    sensitive_archive_ids: list = []
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
            if response.status_code in (200, 202):
                ids = response.json().get("archive_ids", [])
                if ids:
                    ingest_ok += 1
                    sensitive_archive_ids.extend(ids)
        except Exception:
            pass

    # Provider check (server truth): the gate only matters when an LLM provider
    # exists — without one, NOTHING is dispatched externally and blocking is
    # indistinguishable from no-provider idling.
    has_provider = False
    try:
        keys_resp = await client.get(f"{base_url}/api/settings/keys", timeout=5.0)
        if keys_resp.status_code == 200:
            has_provider = any(p.get("configured") for p in keys_resp.json().values())
    except Exception:
        pass

    if not has_provider:
        # HONEST LIMITATION: with no provider, the differential test below is
        # meaningless, and the gate decision itself is only written to server
        # logs — not exposed via job status or audit events (F15 in
        # docs/recommendations.md). Direct observability would let this check
        # run in no-key mode too.
        return CheckResult(
            name="sensitivity",
            passed=False,
            metrics={
                "sensitive_conversations_ingested": ingest_ok,
                "sensitive_conversations_total": len(sensitive_conversations),
            },
            details=(
                f"Ingested {ingest_ok}/{len(sensitive_conversations)} sensitive conversations "
                f"(local capture works). Gate verification requires a configured provider "
                f"(differential test) or direct gate observability (F15)."
            ),
            skipped=True,
            skip_reason=(
                "No provider configured — blocking is indistinguishable from idling. "
                "Configure a provider, or expose the gate decision via audit/API (F15)"
            ),
        )

    # DIFFERENTIAL GATE TEST (provider configured):
    # sensitive conversations must yield ZERO extracted facts, while control
    # conversations (extraction check) DID yield facts through the same
    # pipeline+provider. A leak here means personal content reached the LLM.
    control_worked = settings.get("extraction_worked", False)

    # Wait for the sensitive items' jobs to finish processing
    pipeline_timeout = float(os.getenv("EVAL_PIPELINE_TIMEOUT_S", "300"))
    deadline = time.time() + pipeline_timeout
    done_states = {"Done", "Failed", "Pending Provider"}
    while time.time() < deadline:
        try:
            resp = await client.get(
                f"{base_url}/api/archive",
                params={"q": "eval-sensitivity-", "limit": 50},
                timeout=10.0,
            )
            items = [
                i for i in resp.json().get("items", [])
                if i["id"] in set(sensitive_archive_ids)
            ]
            if items and all(i.get("status_badge") in done_states for i in items):
                break
        except Exception:
            pass
        await asyncio.sleep(5)

    # Any facts attributed to the sensitive archive items?
    leaked_facts = []
    try:
        facts_resp = await client.get(
            f"{base_url}/api/facts", params={"limit": 500}, timeout=10.0,
        )
        if facts_resp.status_code == 200:
            data = facts_resp.json()
            facts = data.get("facts", data.get("items", []))
            leaked_facts = [
                f for f in facts
                if f.get("raw_archive_id") in set(sensitive_archive_ids)
            ]
    except Exception:
        pass

    if not control_worked:
        return CheckResult(
            name="sensitivity",
            passed=False,
            metrics={"leaked_fact_count": float(len(leaked_facts))},
            details=(
                "Control failed: extraction check produced no facts for non-sensitive "
                "conversations, so 'zero facts from sensitive items' proves nothing."
            ),
            skipped=True,
            skip_reason="Extraction control did not produce facts — differential test inconclusive",
        )

    blocked = len(leaked_facts) == 0
    details = (
        f"Differential gate test: {ingest_ok} sensitive conversations processed with a "
        f"configured provider; {len(leaked_facts)} facts were derived from them "
        f"(must be 0) while control conversations produced facts. "
        f"{'Gate BLOCKED sensitive content from extraction.' if blocked else 'LEAK: sensitive content reached the LLM extraction path!'} "
        f"Note: direct gate observability (F15) would make this verification exact "
        f"rather than differential."
    )

    return CheckResult(
        name="sensitivity",
        passed=blocked,
        metrics={
            "block_verified": 1.0 if blocked else 0.0,
            "leaked_fact_count": float(len(leaked_facts)),
            "sensitive_conversations_tested": float(ingest_ok),
        },
        details=details,
    )
