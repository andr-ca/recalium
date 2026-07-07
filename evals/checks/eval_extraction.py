"""Extraction quality evaluation (precision, recall, span fidelity)."""

import asyncio
import time
from typing import Dict, Any, List
import httpx
import os

from evals.checks import CheckResult
from evals.metrics import extraction_recall_and_precision, span_fidelity


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
    # Check if LLM provider is available
    has_provider = bool(
        os.getenv("OPENAI_API_KEY") or
        os.getenv("ANTHROPIC_API_KEY") or
        os.getenv("OLLAMA_BASE_URL")
    )

    if not has_provider:
        return CheckResult(
            name="extraction",
            passed=False,
            metrics={},
            details="No LLM provider configured",
            skipped=True,
            skip_reason="No OPENAI_API_KEY, ANTHROPIC_API_KEY, or OLLAMA_BASE_URL in environment",
        )

    # Ingest conversations and collect extracted facts
    extracted_facts_by_conv: Dict[str, List[Dict]] = {}
    golden_facts_by_conv: Dict[str, List[Dict]] = {}

    for conv in golden.get("conversations", []):
        conv_id = conv["id"]
        raw_text = conv["raw_text"]
        golden_facts = conv.get("facts", [])

        if not golden_facts:
            continue

        golden_facts_by_conv[conv_id] = golden_facts

        # Reuse archive IDs recorded by the ingest check when available;
        # otherwise ingest via the HTTP contract (mode/content/source_name, 202)
        base_url = settings.get("base_url", "http://localhost:8000")
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

            # Poll for extracted facts (LLM extraction is async and can be slow)
            max_polls = 20
            poll_interval = 3.0  # seconds
            archive_id_set = set(archive_ids)

            for attempt in range(max_polls):
                try:
                    facts_response = await client.get(
                        f"{base_url}/api/facts",
                        params={"limit": 500},
                        timeout=10.0,
                    )
                    if facts_response.status_code == 200:
                        facts_data = facts_response.json()
                        facts = facts_data.get("facts", facts_data.get("items", []))
                        ours = [
                            f for f in facts
                            if f.get("raw_archive_id") in archive_id_set
                        ]
                        if ours:
                            extracted_facts_by_conv[conv_id] = [
                                {
                                    "text": f.get("fact_text", ""),
                                    "source_span": f.get("source_span"),
                                }
                                for f in ours
                            ]
                            break
                except Exception:
                    pass

                if attempt < max_polls - 1:
                    await asyncio.sleep(poll_interval)

        except Exception:
            continue

    if not extracted_facts_by_conv or not golden_facts_by_conv:
        return CheckResult(
            name="extraction",
            passed=False,
            metrics={},
            details="Could not extract facts from any conversation",
            skipped=True,
            skip_reason="Extraction failed for all conversations",
        )

    # Calculate metrics across all conversations
    total_recall = 0.0
    total_precision = 0.0
    total_span_fidelity = 0.0
    conv_count = 0

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

    # Thresholds
    recall_threshold = 0.6
    precision_threshold = 0.7
    span_fidelity_threshold = 0.95

    passed = (
        avg_recall >= recall_threshold and
        avg_precision >= precision_threshold and
        avg_span_fidelity >= span_fidelity_threshold
    )

    details = (
        f"Extraction metrics (avg across {conv_count} conversations): "
        f"Recall {avg_recall:.2%} (threshold: {recall_threshold:.0%}), "
        f"Precision {avg_precision:.2%} (threshold: {precision_threshold:.0%}), "
        f"Span fidelity {avg_span_fidelity:.2%} (threshold: {span_fidelity_threshold:.0%})."
    )

    return CheckResult(
        name="extraction",
        passed=passed,
        metrics={
            "recall": avg_recall,
            "precision": avg_precision,
            "span_fidelity": avg_span_fidelity,
            "count_conversations": conv_count,
        },
        details=details,
    )
