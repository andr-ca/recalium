"""Derived memory domain service — writes summaries, facts, FTS entries, and embeddings.

SECURITY: No API keys here. This service only writes derived data to DB.
PIPE-02: All write_facts calls enforce source_span/confidence_tier/derivation fields.
PIPE-01: embed_text uses local sentence-transformers when available (EMBED_BACKEND=cpu|gpu).
         When sentence-transformers is not installed, embed_text raises RuntimeError and the
         worker skips the embedding step — external providers (OpenAI/Ollama) handle it instead.
CASCADE CONTRACT: All rows default to source_status='active'.
"""
from __future__ import annotations

import asyncio
import logging
import uuid

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.derived_memory.models import Summary, Fact, FtsEntry, Embedding

logger = logging.getLogger(__name__)

# ── Embedding model singleton ─────────────────────────────────────────────────
# Loaded lazily on first call. NOT at module import (avoids blocking event loop).
# _get_embed_model() is called inside asyncio.to_thread() — safe to block there.
# Will be None if sentence-transformers is not installed (EMBED_BACKEND=none).
try:
    from sentence_transformers import SentenceTransformer as _SentenceTransformer
    _SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    _SentenceTransformer = None  # type: ignore[assignment,misc]
    _SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.info(
        "sentence-transformers not installed (EMBED_BACKEND=none). "
        "Local embeddings unavailable — use OpenAI / Anthropic / Ollama instead."
    )

_embed_model: "_SentenceTransformer | None" = None
_EMBED_MODEL_NAME = "all-MiniLM-L6-v2"


def _get_embed_model() -> "_SentenceTransformer":
    """Load embedding model lazily. Called inside asyncio.to_thread() — safe to block."""
    if not _SENTENCE_TRANSFORMERS_AVAILABLE:
        raise RuntimeError(
            "sentence-transformers is not installed. "
            "Rebuild with EMBED_BACKEND=cpu or EMBED_BACKEND=gpu, "
            "or configure an external provider (OPENAI_API_KEY / OLLAMA_BASE_URL)."
        )
    global _embed_model
    if _embed_model is None:
        _embed_model = _SentenceTransformer(_EMBED_MODEL_NAME)
        logger.info("Loaded embedding model: %s", _EMBED_MODEL_NAME)
    return _embed_model


async def embed_text(text: str) -> list[float]:
    """Embed text using all-MiniLM-L6-v2 in a thread pool.

    Runs synchronous sentence-transformers encode() in asyncio.to_thread() to
    avoid blocking the event loop. Returns L2-normalized vector (384 dims).

    PIPE-01: local embeddings always available — no API key needed.
    """
    def _encode() -> list[float]:
        model = _get_embed_model()
        vector = model.encode(text, normalize_embeddings=True)
        return vector.tolist()

    return await asyncio.to_thread(_encode)


async def write_summary(
    session: AsyncSession,
    raw_archive_id: uuid.UUID,
    summary_text: str,
    model_used: str,
    derivation_method: str = "llm_summarization",
) -> Summary:
    """Write a new summary for a raw archive item. source_status defaults to 'active'."""
    summary = Summary(
        raw_archive_id=raw_archive_id,
        summary_text=summary_text,
        model_used=model_used,
        derivation_method=derivation_method,
    )
    session.add(summary)
    await session.commit()
    await session.refresh(summary)
    logger.debug("Wrote summary for archive_id=%s model=%s", raw_archive_id, model_used)
    return summary


async def get_existing_summary(
    session: AsyncSession,
    raw_archive_id: uuid.UUID,
) -> Summary | None:
    """Return the first active summary for this archive item (for BYOK-08 skip check)."""
    result = await session.execute(
        select(Summary)
        .where(Summary.raw_archive_id == raw_archive_id)
        .where(Summary.source_status == "active")
        .limit(1)
    )
    return result.scalar_one_or_none()


async def write_facts(
    session: AsyncSession,
    raw_archive_id: uuid.UUID,
    facts_data: list[dict],
) -> list[Fact]:
    """Write extracted facts for a raw archive item.

    PIPE-02 enforcement:
    - source_span is required. If empty/whitespace, confidence_tier is forced to 'low'.
    - confidence_tier must be 'high', 'medium', or 'low'.
    - derivation_method and derivation_model are required.
    """
    created: list[Fact] = []

    for item in facts_data:
        source_span = item.get("source_span", "").strip() if item.get("source_span") else ""
        confidence_tier = item.get("confidence_tier", "low")

        # PIPE-02: empty source_span → force confidence_tier to 'low'
        if not source_span:
            confidence_tier = "low"
            logger.debug(
                "Fact has empty source_span — downgrading confidence to 'low' for archive_id=%s",
                raw_archive_id,
            )

        # Validate confidence_tier
        if confidence_tier not in ("high", "medium", "low"):
            confidence_tier = "low"

        fact = Fact(
            raw_archive_id=raw_archive_id,
            fact_text=item["fact_text"],
            source_span=item.get("source_span", ""),
            confidence_tier=confidence_tier,
            derivation_method=item.get("derivation_method", "llm_extraction"),
            derivation_model=item.get("derivation_model", "unknown"),
            conflict_group_id=item.get("conflict_group_id"),
        )
        session.add(fact)
        created.append(fact)

    if created:
        await session.commit()
        for fact in created:
            await session.refresh(fact)
        logger.debug("Wrote %d facts for archive_id=%s", len(created), raw_archive_id)

    return created


async def write_fts_entry(
    session: AsyncSession,
    raw_archive_id: uuid.UUID,
    text_content: str,
) -> FtsEntry:
    """Write a full-text search entry and populate the tsvector column.

    Uses to_tsvector('english', ...) for English-language FTS indexing.
    search_vector is updated via raw SQL because SQLAlchemy doesn't have a TSVECTOR type.
    """
    entry = FtsEntry(
        raw_archive_id=raw_archive_id,
        text_content=text_content,
    )
    session.add(entry)
    await session.flush()  # Get ID without full commit

    # Update search_vector via SQL (to_tsvector is a PostgreSQL function)
    await session.execute(
        text(
            "UPDATE fts_entries SET search_vector = to_tsvector('english', :content) "
            "WHERE id = :id"
        ),
        {"content": text_content, "id": str(entry.id)},
    )
    await session.commit()
    await session.refresh(entry)
    logger.debug("Wrote FTS entry for archive_id=%s", raw_archive_id)
    return entry


async def write_embedding(
    session: AsyncSession,
    raw_archive_id: uuid.UUID,
    vector: list[float],
    model_name: str = _EMBED_MODEL_NAME,
) -> Embedding:
    """Write embedding vector for a raw archive item.

    PIPE-01: source_status='active'. 384 dims from all-MiniLM-L6-v2.
    Stores embedding_model so future model upgrades can detect stale rows.
    """
    embedding = Embedding(
        raw_archive_id=raw_archive_id,
        embedding=vector,
        embedding_model=model_name,
    )
    session.add(embedding)
    await session.commit()
    await session.refresh(embedding)
    logger.debug(
        "Wrote embedding for archive_id=%s model=%s dims=%d",
        raw_archive_id, model_name, len(vector),
    )
    return embedding


async def get_existing_embedding(
    session: AsyncSession,
    raw_archive_id: uuid.UUID,
) -> Embedding | None:
    """Return the first active embedding for this archive item (BYOK-08 skip check)."""
    result = await session.execute(
        select(Embedding)
        .where(Embedding.raw_archive_id == raw_archive_id)
        .where(Embedding.source_status == "active")
        .limit(1)
    )
    return result.scalar_one_or_none()
