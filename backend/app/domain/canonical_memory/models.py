"""Canonical memory ORM models.

CANM-02: Canonical items have highest retrieval priority.
CANM-03: Promoted only via explicit user action — never auto-promoted.
CANM-04: Facts without source_span require confirmed=True to promote.

CASCADE CONTRACT: source_status column present. ALL read queries filter source_status='active'.
SECURITY: No column ends with _key, _secret, _token, _password.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, TIMESTAMP, ForeignKey, Enum as SAEnum
from sqlalchemy.schema import FetchedValue
from sqlalchemy.dialects.postgresql import UUID, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db import Base

_source_status = SAEnum("active", "source_removed", name="source_status", create_type=False)


class CanonicalMemoryItem(Base):
    """A user-promoted canonical memory entry."""
    __tablename__ = "canonical_memory"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    raw_archive_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("raw_archive.id", ondelete="SET NULL"),
        nullable=True,
    )
    fact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("facts.id", ondelete="SET NULL"),
        nullable=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="active")
    source_status: Mapped[str] = mapped_column(
        _source_status, nullable=False, default="active"
    )
    promoted_from: Mapped[str] = mapped_column(String(32), nullable=False)
    promoted_by: Mapped[str] = mapped_column(String(64), nullable=False, default="user_ui")
    provenance_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    search_vector: Mapped[str | None] = mapped_column(
        TSVECTOR, nullable=True, server_default=FetchedValue()
    )
    # DB-generated: to_tsvector('english', content). Do not set manually.
