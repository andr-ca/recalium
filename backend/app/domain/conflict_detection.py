"""Conflict and duplicate detection for derived memory facts.

CANM-06: Flags contradictory or duplicate facts across sources by comparing
embedding vectors using pgvector cosine distance.

SECURITY: All queries filter source_status = 'active' — suppressed data is excluded.
"""
from __future__ import annotations

import logging
import uuid
from typing import Sequence

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.derived_memory.models import ConflictGroup

logger = logging.getLogger(__name__)

DUPLICATE_DISTANCE_THRESHOLD = 0.15
_MAX_CANDIDATES = 10


async def find_duplicate_candidates(
    session: AsyncSession,
    embedding: list[float],
    exclude_id: uuid.UUID,
) -> list[uuid.UUID]:
    """Find embeddings that are near-duplicates of the given vector.

    Uses pgvector cosine distance (<=>). Only considers rows with
    source_status = 'active' (CASCADE CONTRACT).

    Args:
        session: Async DB session.
        embedding: The query vector (384-dim list of floats).
        exclude_id: UUID of the embedding row to exclude (the source itself).

    Returns:
        List of embedding UUIDs within DUPLICATE_DISTANCE_THRESHOLD.
    """
    result = await session.execute(
        text("""
            SELECT id
            FROM embeddings
            WHERE id != :exclude_id
              AND source_status = 'active'
              AND embedding <=> :vec < :threshold
            ORDER BY embedding <=> :vec
            LIMIT :max_candidates
        """),
        {
            # Rows read back through pgvector are numpy arrays, whose str() is
            # space-separated and NOT valid pgvector input — coerce to list first
            "vec": str(embedding.tolist() if hasattr(embedding, "tolist") else list(embedding)),
            "exclude_id": str(exclude_id),
            "threshold": DUPLICATE_DISTANCE_THRESHOLD,
            "max_candidates": _MAX_CANDIDATES,
        },
    )
    rows = result.fetchall()
    logger.debug("Conflict scan: found %d candidates near embedding %s", len(rows), exclude_id)
    return [uuid.UUID(str(row.id)) for row in rows]


async def create_conflict_group(
    session: AsyncSession,
    group_type: str = "duplicate",
    fact_ids: Sequence[uuid.UUID] | None = None,  # accepted for API compat; stored when schema supports it
) -> ConflictGroup:
    """Create a ConflictGroup row and return it.

    CANM-06: group_type is one of "duplicate" | "contradiction" | "overlap".

    Args:
        session: Async DB session.
        group_type: Type of conflict ("duplicate" by default).
        fact_ids: Optional list of fact UUIDs involved (for future linking table).

    Returns:
        The persisted ConflictGroup instance.
    """
    group = ConflictGroup(group_type=group_type)
    session.add(group)
    await session.commit()
    await session.refresh(group)
    logger.info("Created conflict group id=%s type=%s", group.id, group_type)
    return group
