"""Archive domain ORM models."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, String, Text, Integer, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db import Base


class RawArchiveItem(Base):
    """Raw ingested conversation. Soft-deleted via deleted_at.

    ALL read queries MUST filter: WHERE deleted_at IS NULL
    """
    __tablename__ = "raw_archive"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    conversation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    ingested_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True, default=None
    )
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class Tombstone(Base):
    """Append-only deletion/redaction ledger (deletion-and-tombstones.md; GPT5.6 #2).

    Records every source removal so deleted content cannot silently reappear after
    a restore, reindex, or import. ``content_hash`` lets a restore reapply
    suppression to a restored pre-deletion copy of the same content. This table is
    included in backups; it is *mirrored* to an append-only ledger file that lives
    outside the database dump (see ``archive.tombstones``) so it also survives the
    restore of a backup that was taken *before* the deletion.

    No FK to ``raw_archive`` on purpose: a tombstone must outlive the raw row and
    remain valid across restore boundaries where ids may not yet exist.
    """
    __tablename__ = "tombstones"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    removal_type: Mapped[str] = mapped_column(String(16), nullable=False, default="delete")
    removed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    actor: Mapped[str] = mapped_column(String(128), nullable=False, default="user_ui")
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    suppression_scope: Mapped[str] = mapped_column(
        String(32), nullable=False, default="source_item"
    )
