"""Eval harness diagnostics — classify pipeline failures vs gate blocks."""

from __future__ import annotations

import asyncio
import os
import time
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple


PIPELINE_FAILURE_MARKERS = (
    "404",
    "not found",
    "HTTPStatusError",
    "Cannot reach",
    "timed out",
    "Connection refused",
    "model",
)


def classify_zero_extraction(
    control_archive_ids: Sequence[str],
    gate_events: Mapping[str, Mapping[str, Any]],
    archive_rows: Sequence[Mapping[str, Any]],
) -> Tuple[str, str]:
    """
    Classify why control conversations produced zero extracted facts.

    Returns (category, detail_message).
    Categories: provider_pipeline_failure | gate_blocked | inconclusive
    """
    control_set: Set[str] = set(control_archive_ids)
    control_gate = [
        gate_events[aid]
        for aid in control_archive_ids
        if aid in gate_events
    ]

    if control_gate and all(m.get("blocked") is True for m in control_gate):
        return (
            "gate_blocked",
            "Sensitivity gate blocked all control conversations (audit events show blocked=True).",
        )

    if control_gate and any(m.get("blocked") is False for m in control_gate):
        pipeline_detail = _pipeline_errors_for_archives(archive_rows, control_set)
        if pipeline_detail:
            return ("provider_pipeline_failure", pipeline_detail)
        return (
            "provider_pipeline_failure",
            "Gate allowed control conversations (blocked=False) but no facts were extracted — "
            "check extraction provider, model availability, and pipeline job errors.",
        )

    pipeline_detail = _pipeline_errors_for_archives(archive_rows, control_set)
    if pipeline_detail:
        return ("provider_pipeline_failure", pipeline_detail)

    return (
        "inconclusive",
        "No gate audit events and no facts extracted — cannot distinguish gate vs pipeline failure.",
    )


def _pipeline_errors_for_archives(
    archive_rows: Sequence[Mapping[str, Any]],
    archive_ids: Set[str],
) -> Optional[str]:
    errors: List[str] = []
    for row in archive_rows:
        aid = row.get("id")
        if aid not in archive_ids:
            continue
        badge = row.get("status_badge") or row.get("job_status")
        err = row.get("job_error") or row.get("error_message") or ""
        if badge == "Failed" and err:
            errors.append(err)
        elif err and any(m in err.lower() for m in ("404", "not found", "model")):
            errors.append(err)

    for err in errors:
        lower = err.lower()
        if any(marker.lower() in lower for marker in PIPELINE_FAILURE_MARKERS):
            return f"Pipeline job failure: {err[:200]}"

    if errors:
        return f"Pipeline job failure: {errors[0][:200]}"
    return None


async def fetch_gate_events(
    client: Any,
    base_url: str,
) -> Dict[str, Dict[str, Any]]:
    """Map raw_archive_id → sensitivity_gate operation_metadata."""
    gate_events: Dict[str, Dict[str, Any]] = {}
    try:
        audit_resp = await client.get(
            f"{base_url}/api/audit/events",
            params={"event_type": "sensitivity_gate", "limit": 200},
            timeout=10.0,
        )
        if audit_resp.status_code == 200:
            for ev in audit_resp.json().get("items", []):
                aid = ev.get("raw_archive_id")
                if aid:
                    gate_events[aid] = ev.get("operation_metadata") or {}
    except Exception:
        pass
    return gate_events


async def count_facts_for_archives(
    client: Any,
    base_url: str,
    archive_ids: Sequence[str],
) -> int:
    if not archive_ids:
        return 0
    wanted = set(archive_ids)
    try:
        facts_resp = await client.get(
            f"{base_url}/api/facts",
            params={"limit": 500},
            timeout=10.0,
        )
        if facts_resp.status_code != 200:
            return 0
        data = facts_resp.json()
        facts = data.get("facts", data.get("items", []))
        return sum(1 for f in facts if f.get("raw_archive_id") in wanted)
    except Exception:
        return 0


async def fetch_archive_rows_for_ids(
    client: Any,
    base_url: str,
    archive_ids: Sequence[str],
) -> List[Dict[str, Any]]:
    """Fetch archive list rows matching the given IDs (best-effort)."""
    if not archive_ids:
        return []
    wanted = set(archive_ids)
    rows: List[Dict[str, Any]] = []

    async def _collect_from_list(params: Dict[str, Any]) -> None:
        try:
            resp = await client.get(
                f"{base_url}/api/archive",
                params=params,
                timeout=10.0,
            )
            if resp.status_code == 200:
                for item in resp.json().get("items", []):
                    item_id = item.get("id")
                    if item_id in wanted and item_id not in {r.get("id") for r in rows}:
                        rows.append(item)
        except Exception:
            pass

    # Eval archives are tagged eval-*; scoped query avoids missing IDs in a long archive list.
    await _collect_from_list({"q": "eval-", "limit": 200})
    if not wanted.issubset({row.get("id") for row in rows}):
        await _collect_from_list({"limit": 500})
    return rows


async def wait_for_archive_pipeline_drain(
    client: Any,
    base_url: str,
    archive_ids: Sequence[str],
    *,
    timeout_s: float,
    poll_interval_s: float = 2.0,
) -> Tuple[bool, List[Dict[str, Any]]]:
    """
    Poll until every archive ID has left the Processing state (Done or Failed).

    Returns (drained, archive_rows_for_ids). drained is False when timeout expires
    while any target archive is still Processing.
    """
    if not archive_ids:
        return True, []

    wanted = set(archive_ids)
    deadline = time.monotonic() + timeout_s
    rows: List[Dict[str, Any]] = []

    while time.monotonic() < deadline:
        rows = await fetch_archive_rows_for_ids(client, base_url, archive_ids)
        by_id = {row.get("id"): row for row in rows}
        if wanted.issubset(by_id.keys()):
            badges = [by_id[aid].get("status_badge") for aid in archive_ids]
            if all(b != "Processing" for b in badges):
                return True, rows
        await asyncio.sleep(poll_interval_s)

    rows = await fetch_archive_rows_for_ids(client, base_url, archive_ids)
    return False, rows


async def resolve_pipeline_timeout_s(
    client: Any,
    base_url: str,
    *,
    default_s: float = 300.0,
) -> float:
    """
    Pipeline drain timeout. Honors EVAL_PIPELINE_TIMEOUT_S when set; otherwise
    uses default_s, with a longer profile when only Ollama is configured (local
    extraction is slower under queued jobs).
    """
    if "EVAL_PIPELINE_TIMEOUT_S" in os.environ:
        return float(os.environ["EVAL_PIPELINE_TIMEOUT_S"])

    try:
        keys_resp = await client.get(f"{base_url}/api/settings/keys", timeout=5.0)
        if keys_resp.status_code == 200:
            providers = keys_resp.json()
            ollama = providers.get("ollama", {}).get("configured")
            openai = providers.get("openai", {}).get("configured")
            anthropic = providers.get("anthropic", {}).get("configured")
            if ollama and not openai and not anthropic:
                return max(default_s, 600.0)
    except Exception:
        pass
    return default_s
