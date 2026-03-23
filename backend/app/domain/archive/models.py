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
