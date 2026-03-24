"""Audit event API routes.

MCP-03: Access event audit trail — readable from UI.
MCP-04: Includes client identity (actor field).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.audit.service import list_audit_events
from app.infrastructure.db import get_session

router = APIRouter(prefix="/api/audit", tags=["audit"])


@router.get("/events")
async def list_events(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    event_type: str | None = Query(None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Return paginated audit events, newest first."""
    events = await list_audit_events(session, limit=limit, offset=offset, event_type=event_type)
    return {
        "items": [
            {
                "id": str(e.id),
                "event_type": e.event_type,
                "actor": e.actor,
                "operation_metadata": e.operation_metadata,
                "occurred_at": e.occurred_at.isoformat() if e.occurred_at else None,
            }
            for e in events
        ],
        "count": len(events),
    }
