"""Archive domain service — deletion cascade.

PRIV-01: Deletion cascade immediately suppresses all derived data.
PRIV-02: Canonical memory is marked source_removed + required_review, NOT deleted.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.archive.models import RawArchiveItem
from app.domain.audit.models import AuditEvent

logger = logging.getLogger(__name__)


class ArchiveItemNotFoundError(Exception):
    """Raised when the archive item does not exist or is already deleted."""


async def cascade_delete_archive_item(
    session: AsyncSession,
    archive_id: uuid.UUID,
    actor: str = "user_ui",
) -> None:
    """Soft-delete a raw archive item and cascade source_removed to all derived data.

    Atomic: all updates committed together or none committed.
    PRIV-01: Derived data marked source_removed.
    PRIV-02: Canonical memory marked source_removed + required_review (NOT deleted).
    """
    result = await session.execute(
        select(RawArchiveItem).where(
            RawArchiveItem.id == archive_id,
            RawArchiveItem.deleted_at.is_(None),
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise ArchiveItemNotFoundError(
            f"Archive item {archive_id} not found or already deleted"
        )

    now = datetime.now(timezone.utc)
    archive_id_str = str(archive_id)

    item.deleted_at = now

    for table in ("summaries", "facts", "embeddings", "fts_entries"):
        await session.execute(
            text(
                f"UPDATE {table} SET source_status = 'source_removed' "
                "WHERE raw_archive_id = :archive_id AND source_status = 'active'"
            ),
            {"archive_id": archive_id_str},
        )

    await session.execute(
        text(
            "UPDATE conflict_groups SET source_status = 'source_removed' "
            "WHERE id IN ("
            "  SELECT DISTINCT conflict_group_id FROM facts "
            "  WHERE raw_archive_id = :archive_id AND conflict_group_id IS NOT NULL"
            ") AND source_status = 'active'"
        ),
        {"archive_id": archive_id_str},
    )

    await session.execute(
        text(
            "UPDATE review_queue_items SET source_status = 'source_removed' "
            "WHERE conflict_group_id IN ("
            "  SELECT id FROM conflict_groups WHERE source_status = 'source_removed'"
            ") AND source_status = 'active'"
        ),
    )

    await session.execute(
        text(
            "UPDATE canonical_memory "
            "SET source_status = 'source_removed', status = 'required_review' "
            "WHERE raw_archive_id = :archive_id AND source_status = 'active'"
        ),
        {"archive_id": archive_id_str},
    )

    audit_event = AuditEvent(
        event_type="archive_delete",
        raw_archive_id=archive_id,
        actor=actor,
        operation_metadata={
            "archive_id": archive_id_str,
            "deleted_at": now.isoformat(),
        },
    )
    session.add(audit_event)

    await session.commit()

    try:
        from app.domain.retrieval.service import invalidate_cache  # noqa: PLC0415
        invalidate_cache()
    except Exception as e:
        logger.warning("Could not invalidate retrieval cache after deletion: %s", e)

    logger.info("Cascade delete complete for archive_id=%s actor=%s", archive_id_str, actor)
