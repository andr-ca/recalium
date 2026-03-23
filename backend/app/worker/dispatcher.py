"""Job dispatcher — routes jobs through the processing pipeline.

PIPELINE ORDER (mandatory — gate fires first, ALWAYS):
  1. Sensitivity gate (classify_async) — BLOCKS if personal/relationship/unclassified
  2. Summarize + extract facts (LLM, if provider configured and not already done)
  3. Embed (local sentence-transformers — plan 05 wires this)
  4. FTS index
  5. Conflict detection (plan 06 wires this)

SECURITY:
  - Gate runs BEFORE any external provider call — no exceptions
  - Keys read from get_settings() at dispatch time — never from job record or DB
  - Provider keys never appear in job error_message or logs

BYOK-07: Invalid/rate-limited key → retryable_failed with error captured (not silent drop)
BYOK-08: Already-completed sub-jobs (summary exists) → skip without reprocessing
"""
from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.jobs.models import Job
from app.domain.jobs.service import (
    complete_job,
    fail_job,
    set_pending_provider,
)
from app.domain.policy.gate import SensitivityGate
from app.infrastructure.settings import get_settings

logger = logging.getLogger(__name__)

# Sensitivity gate instance (shared; stateless after model load)
_gate = SensitivityGate()

# ── LLM prompts ───────────────────────────────────────────────────────────────

SUMMARIZATION_SYSTEM_PROMPT = """You are a conversation summarizer. Write a concise summary (2-4 sentences) of the key topics and outcomes in this conversation. Focus on information that would be useful to recall in a future session."""

FACT_EXTRACTION_SYSTEM_PROMPT = """You are a fact extraction engine. Extract factual statements from the conversation.

For each fact:
1. Write the fact as a single declarative sentence (fact_text)
2. Copy the EXACT quote from the source that supports this fact (source_span)
3. Assign confidence: "high" (explicit statement), "medium" (implied), "low" (uncertain)

Return JSON object with "facts" array:
{"facts": [
  {
    "fact_text": "User's name is Alice.",
    "source_span": "My name is Alice",
    "confidence_tier": "high"
  }
]}

Return {"facts": []} if no facts can be extracted with a source span."""


# ── Provider routing ──────────────────────────────────────────────────────────

async def _run_summarize_job(text: str) -> str | None:
    """Run LLM summarization. Returns summary text or None if no provider configured.

    Reads API keys from settings at call time (never from DB or job record).
    Raises exception on API error (caller converts to retryable_failed).
    """
    settings = get_settings()

    if settings.openai_api_key:
        from openai import AsyncOpenAI  # noqa: PLC0415
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SUMMARIZATION_SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            temperature=0,
            max_tokens=512,
        )
        return response.choices[0].message.content

    if settings.anthropic_api_key:
        from anthropic import AsyncAnthropic  # noqa: PLC0415
        client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        response = await client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=512,
            messages=[{"role": "user", "content": text}],
            system=SUMMARIZATION_SYSTEM_PROMPT,
        )
        return response.content[0].text

    if settings.ollama_base_url:
        from openai import AsyncOpenAI  # noqa: PLC0415
        client = AsyncOpenAI(
            api_key=settings.ollama_api_key or "ollama",
            base_url=f"{settings.ollama_base_url.rstrip('/')}/v1",
        )
        response = await client.chat.completions.create(
            model=settings.ollama_model,
            messages=[
                {"role": "system", "content": SUMMARIZATION_SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            temperature=0,
        )
        return response.choices[0].message.content

    return None  # No provider configured — caller marks as pending_provider


async def _run_extract_job(text: str) -> list[dict[str, Any]]:
    """Run LLM fact extraction. Returns list of fact dicts or [] if no provider configured.

    Returns [] (not None) when no provider is configured — FTS still runs.
    Raises exception on API error (caller converts to retryable_failed).
    """
    settings = get_settings()

    if settings.openai_api_key:
        from openai import AsyncOpenAI  # noqa: PLC0415
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": FACT_EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        data = json.loads(response.choices[0].message.content or "{}")
        return data.get("facts", [])

    if settings.anthropic_api_key:
        from anthropic import AsyncAnthropic  # noqa: PLC0415
        client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        response = await client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=2048,
            messages=[{"role": "user", "content": text}],
            system=FACT_EXTRACTION_SYSTEM_PROMPT,
        )
        raw = response.content[0].text
        try:
            data = json.loads(raw)
            return data.get("facts", [])
        except json.JSONDecodeError:
            logger.warning("Anthropic returned non-JSON facts response: %s", raw[:200])
            return []

    if settings.ollama_base_url:
        from openai import AsyncOpenAI  # noqa: PLC0415
        client = AsyncOpenAI(
            api_key=settings.ollama_api_key or "ollama",
            base_url=f"{settings.ollama_base_url.rstrip('/')}/v1",
        )
        response = await client.chat.completions.create(
            model=settings.ollama_model,
            messages=[
                {"role": "system", "content": FACT_EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            temperature=0,
        )
        raw = response.choices[0].message.content or "{}"
        try:
            data = json.loads(raw)
            return data.get("facts", [])
        except json.JSONDecodeError:
            return []

    return []  # No provider configured


def _provider_name() -> str:
    """Return name of configured LLM provider (for derivation_model field)."""
    settings = get_settings()
    if settings.openai_api_key:
        return "gpt-4o-mini"
    if settings.anthropic_api_key:
        return "claude-3-haiku-20240307"
    if settings.ollama_base_url:
        return settings.ollama_model
    return "none"


def _has_llm_provider() -> bool:
    """True if any LLM provider key is configured."""
    settings = get_settings()
    return bool(settings.openai_api_key or settings.anthropic_api_key or settings.ollama_base_url)


# ── Main dispatcher ───────────────────────────────────────────────────────────

async def dispatch_job(session: AsyncSession, job: Job) -> None:
    """Route a claimed job through the full pipeline.

    Pipeline order (enforced — gate MUST fire before any external call):
      1. Load raw archive content
      2. Sensitivity gate (blocks personal/relationship/unclassified)
      3. LLM summarize + extract (skipped if blocked or no provider)
      4. FTS indexing (always runs — local, no external call)
      5. Embeddings and conflict detection wired in plan 05–06

    On any provider error: job → retryable_failed with error captured (BYOK-07).
    On missing provider: job → pending_provider (amber badge, not failure).
    On blocked content: job → completed (no LLM output, FTS still runs).
    """
    from sqlalchemy import select  # noqa: PLC0415
    from app.domain.archive.models import RawArchiveItem  # noqa: PLC0415
    from app.domain.derived_memory.service import (  # noqa: PLC0415
        write_summary,
        write_facts,
        write_fts_entry,
        get_existing_summary,
    )

    # ── Step 1: Load raw archive content ────────────────────────────────────
    result = await session.execute(
        select(RawArchiveItem)
        .where(RawArchiveItem.id == job.raw_archive_id)
        .where(RawArchiveItem.deleted_at.is_(None))
    )
    archive_item = result.scalar_one_or_none()

    if archive_item is None:
        await fail_job(
            session, job,
            error=f"Raw archive item {job.raw_archive_id} not found or deleted",
            retryable=False,
        )
        return

    raw_text = archive_item.raw_content

    # ── Step 2: Sensitivity gate — MUST run before any external call ────────
    try:
        sensitivity_decision = await _gate.classify_async(raw_text)
    except Exception as e:
        # Gate failure → treat as unclassified (blocked) — fail-safe
        logger.error("Sensitivity gate failed for job %s: %s — treating as blocked", job.id, e)
        await fail_job(
            session, job,
            error=f"Sensitivity gate error: {e}",
            retryable=True,
        )
        return

    logger.info(
        "Sensitivity gate: job=%s category=%s confidence=%.2f blocked=%s",
        job.id, sensitivity_decision.category, sensitivity_decision.confidence,
        sensitivity_decision.blocked,
    )

    # ── Step 3: LLM summarize + extract (only if gate allows AND provider configured) ──
    if not sensitivity_decision.blocked:
        if not _has_llm_provider():
            # No provider — mark pending_provider and skip LLM steps
            await set_pending_provider(
                session, job,
                reason="No LLM provider configured. Add an OpenAI, Anthropic, or Ollama key in Settings.",
            )
            # Note: FTS still runs even when pending_provider (local, no external call)
            # But we return here — job status is pending_provider, not completed
            # FTS is a bonus once provider is configured and job is retried
            return

        # BYOK-08: Check if summary already exists — skip if present
        existing_summary = await get_existing_summary(session, job.raw_archive_id)

        if existing_summary is None:
            try:
                summary_text = await _run_summarize_job(raw_text)
                if summary_text:
                    await write_summary(
                        session,
                        raw_archive_id=job.raw_archive_id,
                        summary_text=summary_text,
                        model_used=_provider_name(),
                        derivation_method="llm_summarization",
                    )
                    logger.debug("Wrote summary for job %s", job.id)
            except Exception as e:
                error_type = type(e).__name__
                await fail_job(
                    session, job,
                    error=f"{error_type}: {str(e)[:500]}",
                    retryable=True,
                )
                return

        # Extract facts
        try:
            facts_data = await _run_extract_job(raw_text)
            enriched_facts = [
                {**f, "derivation_method": "llm_extraction", "derivation_model": _provider_name()}
                for f in facts_data
            ]
            if enriched_facts:
                await write_facts(
                    session,
                    raw_archive_id=job.raw_archive_id,
                    facts_data=enriched_facts,
                )
                logger.debug("Wrote %d facts for job %s", len(enriched_facts), job.id)
        except Exception as e:
            error_type = type(e).__name__
            await fail_job(
                session, job,
                error=f"{error_type}: {str(e)[:500]}",
                retryable=True,
            )
            return

    # ── Step 4: FTS indexing (always runs — local, no external call) ─────────
    # Use summary text if available, otherwise raw content
    try:
        existing_summary = await get_existing_summary(session, job.raw_archive_id)
        fts_text = existing_summary.summary_text if existing_summary else raw_text[:10000]
        await write_fts_entry(
            session,
            raw_archive_id=job.raw_archive_id,
            text_content=fts_text,
        )
        logger.debug("Wrote FTS entry for job %s", job.id)
    except Exception as e:
        logger.warning("FTS indexing failed for job %s (non-fatal): %s", job.id, e)
        # FTS failure is non-fatal — job still completes

    # ── Step 5: Embeddings + conflict detection (wired in plan 05–06) ────────
    # Stub: embedding and conflict detection are added in 02-05 and 02-06
    # dispatch_job is called here from loop.py; plans 05–06 patch this function

    # ── Complete ──────────────────────────────────────────────────────────────
    await complete_job(session, job)
    logger.info("Completed job %s", job.id)
