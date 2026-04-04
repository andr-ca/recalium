"""Review queue ORM models.

CANM-05: Groups duplicate/overlapping facts for manageable cleanup.

CASCADE CONTRACT: source_status column present.
SECURITY: No column ends with _key, _secret, _token, _password.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, TIMESTAMP, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db import Base

_source_status = SAEnum("active", "source_removed", name="source_status", create_type=False)


class ReviewQueueItem(Base):
    """An actionable review task for a duplicate/overlap/contradiction conflict group."""
    __tablename__ = "review_queue_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    conflict_group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conflict_groups.id", ondelete="CASCADE"),
        nullable=False,
    )
    item_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    source_status: Mapped[str] = mapped_column(
        _source_status, nullable=False, default="active"
    )
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
