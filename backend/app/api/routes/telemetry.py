"""Telemetry API routes.

PORT-02: Local usage telemetry visible in Settings.
Data never leaves the local system.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.telemetry.service import get_telemetry_summary
from app.infrastructure.db import get_session

router = APIRouter(prefix="/api/telemetry", tags=["telemetry"])


@router.get("/summary")
async def get_summary(
    days: int = Query(default=30, ge=1, le=365, description="Number of days to include"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """GET /api/telemetry/summary — local usage telemetry.

    Returns daily counters for the last N days (newest first).
    PORT-02: This data is local-only and never exported.
    """
    summary = await get_telemetry_summary(session, days=days)
    return {"days": days, "summary": summary}
