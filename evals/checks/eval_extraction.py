"""Extraction quality evaluation (precision, recall, span fidelity)."""

from typing import Dict, Any, List
import httpx

from evals.checks import CheckResult
from evals.metrics import extraction_recall_and_precision, span_fidelity
from evals.harness_diagnostics import (
    classify_zero_extraction,
    fetch_archive_rows_for_ids,
    fetch_gate_events,
    resolve_pipeline_timeout_s,
    wait_for_archive_pipeline_drain,
)


async def run_check(client: httpx.AsyncClient, golden: Dict[str, Any], settings: Dict[str, Any]) -> CheckResult:
    """
    Evaluate extraction quality against golden labels.

    Ingests each golden conversation, polls for extracted facts, then compares:
    - Recall: % of golden facts that are extracted (fuzzy match)
    - Precision: % of extracted facts that are correct (fuzzy match)
    - Span fidelity: % of extracted facts where source_span is substring of raw source

    Skips gracefully if no LLM provider is configured (extraction requires LLM).

    Args:
        client: httpx.AsyncClient connected to stack
        golden: Parsed golden.json dataset
        settings: Configuration dict

    Returns:
        CheckResult with recall, precision, span_fidelity metrics
    """
    # Check provider availability on the SERVER (its .env is the truth — the
    # eval process env says nothing about what the app container can reach)
    base_url = settings.get("base_url", "http://localhost:8000")
    has_provider = False
    try:
        keys_resp = await client.get(f"{base_url}/api/settings/keys", timeout=5.0)
        if keys_resp.status_code == 200:
            has_provider = any(
                p.get("configured") for p in keys_resp.json().values()
            )
    except Exception:
        pass

    if not has_provider:
        return CheckResult(
            name="extraction",
            passed=False,
            metrics={},
            details="No LLM provider configured on the server",
            skipped=True,
            skip_reason="Server reports no configured provider (GET /api/settings/keys) — set OPENAI_API_KEY, ANTHROPIC_API_KEY, or OLLAMA_BASE_URL in the app's .env",
        )

    # Map control conversations to archive IDs (ingest check runs first in the suite).
    archive_ids_by_conv: Dict[str, List[str]] = {}
    golden_facts_by_conv: Dict[str, List[Dict]] = {}
    all_control_archive_ids: List[str] = []
    pipeline_timeout = await resolve_pipeline_timeout_s(client, base_url)

    for conv in golden.get("conversations", []):
        conv_id = conv["id"]
        raw_text = conv["raw_text"]
        golden_facts = conv.get("facts", [])

        if not golden_facts:
            continue

        if any(
            f.get("sensitivity_level") in ("personal", "relationship")
            for f in golden_facts
        ):
            continue

        golden_facts_by_conv[conv_id] = golden_facts
        archive_ids = list(settings.get("ingested_archive_ids", {}).get(conv_id, []))

        try:
            if not archive_ids:
                response = await client.post(
                    f"{base_url}/api/ingest",
                    json={
                        "mode": "text",
                        "content": raw_text,
                        "source_name": f"eval-{conv_id}",
                    },
                    timeout=5.0,
                )
                if response.status_code not in (200, 202):
                    continue
                archive_ids = response.json().get("archive_ids", [])
                if not archive_ids:
                    continue

            archive_ids_by_conv[conv_id] = archive_ids
            all_control_archive_ids.extend(archive_ids)

        except Exception:
            continue

    if golden_facts_by_conv and all_control_archive_ids:
        drained, _ = await wait_for_archive_pipeline_drain(
            client,
            base_url,
            all_control_archive_ids,
            timeout_s=pipeline_timeout,
        )
        settings["pipeline_drained"] = drained

    extracted_facts_by_conv: Dict[str, List[Dict]] = {}
    try:
        facts_response = await client.get(
            f"{base_url}/api/facts",
            params={"limit": 500},
            timeout=10.0,
        )
        if facts_response.status_code == 200:
            facts_data = facts_response.json()
            facts = facts_data.get("facts", facts_data.get("items", []))
            for conv_id, archive_ids in archive_ids_by_conv.items():
                archive_id_set = set(archive_ids)
                ours = [f for f in facts if f.get("raw_archive_id") in archive_id_set]
                if ours:
                    extracted_facts_by_conv[conv_id] = [
                        {
                            "text": f.get("fact_text", ""),
                            "source_span": f.get("source_span"),
                            "confidence_tier": f.get("confidence_tier"),
                            "derivation_method": f.get("derivation_method"),
                            "derivation_model": f.get("derivation_model"),
                        }
                        for f in ours
                    ]
    except Exception:
        pass

    if not extracted_facts_by_conv or not golden_facts_by_conv:
        gate_events = await fetch_gate_events(client, base_url)
        archive_rows = await fetch_archive_rows_for_ids(
            client, base_url, all_control_archive_ids,
        )
        category, detail = classify_zero_extraction(
            all_control_archive_ids, gate_events, archive_rows,
        )
        if category == "gate_blocked":
            skip_reason = "Sensitivity gate blocked control conversations (see details)"
        elif category == "provider_pipeline_failure":
            skip_reason = "Extraction pipeline failed — provider/model unreachable (see details)"
        else:
            skip_reason = "No extraction data — inconclusive (see details)"
        return CheckResult(
            name="extraction",
            passed=False,
            metrics={},
            details=detail,
            skipped=True,
            skip_reason=skip_reason,
        )

    settings["extraction_worked"] = bool(extracted_facts_by_conv)

    # Calculate metrics across all conversations
    total_recall = 0.0
    total_precision = 0.0
    total_span_fidelity = 0.0
    conv_count = 0

    # PIPE-02: every fact must carry source span, confidence tier, derivation
    # method, and model version
    all_extracted = [f for facts in extracted_facts_by_conv.values() for f in facts]
    provenance_complete = sum(
        1 for f in all_extracted
        if f.get("source_span") and f.get("confidence_tier")
        and f.get("derivation_method") and f.get("derivation_model")
    )
    provenance_completeness = (
        provenance_complete / len(all_extracted) if all_extracted else 0.0
    )

    for conv_id in golden_facts_by_conv:
        if conv_id not in extracted_facts_by_conv:
            continue

        golden_facts = golden_facts_by_conv[conv_id]
        extracted_facts = extracted_facts_by_conv[conv_id]

        if not golden_facts:
            continue

        # Recall and precision
        recall, precision = extraction_recall_and_precision(extracted_facts, golden_facts)
        total_recall += recall
        total_precision += precision

        # Span fidelity
        conv = next((c for c in golden.get("conversations", []) if c["id"] == conv_id), None)
        if conv:
            raw_text = conv["raw_text"]
            facts_with_source = [
                {
                    "source_span": f.get("source_span"),
                    "raw_source": raw_text,
                }
                for f in extracted_facts
            ]
            fidelity = span_fidelity(facts_with_source)
            total_span_fidelity += fidelity

        conv_count += 1

    if conv_count == 0:
        return CheckResult(
            name="extraction",
            passed=False,
            metrics={},
            details="No conversations with both golden and extracted facts",
            skipped=True,
            skip_reason="No extraction data available for comparison",
        )

    # Average metrics
    avg_recall = total_recall / conv_count
    avg_precision = total_precision / conv_count
    avg_span_fidelity = total_span_fidelity / conv_count

    expected_conv_count = len(golden_facts_by_conv)
    missing_conversations = sorted(
        set(golden_facts_by_conv.keys()) - set(extracted_facts_by_conv.keys())
    )
    coverage_complete = conv_count == expected_conv_count

    # Thresholds
    recall_threshold = 0.6
    precision_threshold = 0.7
    span_fidelity_threshold = 0.95
    provenance_threshold = 1.0  # PIPE-02 is absolute: every fact carries provenance

    passed = (
        coverage_complete and
        avg_recall >= recall_threshold and
        avg_precision >= precision_threshold and
        avg_span_fidelity >= span_fidelity_threshold and
        provenance_completeness >= provenance_threshold
    )

    details = (
        f"Extraction metrics (avg across {conv_count} conversations, "
        f"{len(all_extracted)} facts): "
        f"Recall {avg_recall:.2%} (threshold: {recall_threshold:.0%}), "
        f"Precision {avg_precision:.2%} (threshold: {precision_threshold:.0%}), "
        f"Span fidelity {avg_span_fidelity:.2%} (threshold: {span_fidelity_threshold:.0%}), "
        f"Provenance completeness {provenance_completeness:.2%} "
        f"(threshold: {provenance_threshold:.0%}; PIPE-02: span+confidence+method+model)."
    )
    if missing_conversations:
        drain_note = (
            "pipeline still Processing"
            if not settings.get("pipeline_drained", True)
            else "no facts after pipeline drain"
        )
        details += (
            f" INCOMPLETE COVERAGE: {conv_count}/{expected_conv_count} conversations "
            f"produced facts within {pipeline_timeout:.0f}s drain "
            f"({drain_note}; missing: {', '.join(missing_conversations)})."
        )

    return CheckResult(
        name="extraction",
        passed=passed,
        metrics={
            "recall": avg_recall,
            "precision": avg_precision,
            "span_fidelity": avg_span_fidelity,
            "provenance_completeness": provenance_completeness,
            "count_facts": len(all_extracted),
            "count_conversations": conv_count,
            "count_conversations_expected": expected_conv_count,
        },
        details=details,
    )
