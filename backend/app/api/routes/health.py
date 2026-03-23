"""Health check endpoint."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db import get_session

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
async def health_check(session: AsyncSession = Depends(get_session)) -> dict:
    """Health check: verifies app is running and DB is reachable.

    Returns:
        {"status": "ok", "db": "ok"} on success
        {"status": "...", "db": "error", "detail": "..."} if DB unreachable
    """
    try:
        await session.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        logger.error("DB health check failed: %s", e)
        return {"status": "degraded", "db": "error", "detail": "database unreachable"}
    return {"status": "ok", "db": db_status}
