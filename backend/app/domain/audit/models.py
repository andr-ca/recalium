"""Audit domain ORM models."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, String, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db import Base


class AuditEvent(Base):
    """Append-only audit event log.

    NEVER update or delete rows in this table.
    Write events synchronously with the operation they record.
    """
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_archive_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    actor: Mapped[str] = mapped_column(String(64), nullable=False, default="user_ui")
    operation_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
