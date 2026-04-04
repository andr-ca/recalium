"""Audit domain service — query helpers for the audit event table."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.audit.models import AuditEvent


async def list_audit_events(
    session: AsyncSession,
    limit: int = 50,
    offset: int = 0,
    event_type: str | None = None,
) -> list[AuditEvent]:
    """Return paginated audit events, newest first."""
    stmt = select(AuditEvent)
    if event_type is not None:
        stmt = stmt.where(AuditEvent.event_type == event_type)
    stmt = stmt.order_by(AuditEvent.occurred_at.desc()).limit(limit).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())
