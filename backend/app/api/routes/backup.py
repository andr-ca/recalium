"""Backup API routes.

BKUP-01: Scheduled daily backups with 30-day retention.
BKUP-02: Restore within 15 minutes.
BKUP-03: Restore recovers all data.
PRIV-03: UI flags backups predating deletion events.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.backup.service import (
    create_backup,
    delete_old_backups,
    list_backups,
    restore_backup,
    backup_predates_deletion,
    DEFAULT_BACKUP_DIR,
)
from app.infrastructure.db import get_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/backup", tags=["backup"])


class RestoreRequest(BaseModel):
    filename: str


@router.get("/list")
async def list_backups_route(
    session: AsyncSession = Depends(get_session),
) -> dict:
    """GET /api/backup/list — list available backups.

    Each backup is enriched with has_post_deletion_events flag (PRIV-03).
    """
    backups = await list_backups(backup_dir=DEFAULT_BACKUP_DIR)

    enriched = []
    for b in backups:
        created_at_str = b["created_at"]
        try:
            backup_ts = datetime.fromisoformat(created_at_str)
            if backup_ts.tzinfo is None:
                backup_ts = backup_ts.replace(tzinfo=timezone.utc)
            has_post = await backup_predates_deletion(session, backup_ts)
        except Exception:
            has_post = False
        enriched.append({**b, "has_post_deletion_events": has_post})

    return {"backups": enriched, "count": len(enriched)}


@router.post("/trigger")
async def trigger_backup() -> dict:
    """POST /api/backup/trigger — create a backup now and clean old ones.

    BKUP-01: Backup includes all data with 30-day retention.
    """
    try:
        result = await create_backup(backup_dir=DEFAULT_BACKUP_DIR)
    except Exception as exc:
        logger.error("Backup failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Backup failed: {exc}") from exc

    deleted = await delete_old_backups(backup_dir=DEFAULT_BACKUP_DIR, retention_days=30)
    return {**result, "old_backups_deleted": deleted}


@router.post("/restore")
async def restore_backup_route(body: RestoreRequest) -> dict:
    """POST /api/backup/restore — restore from a named backup file.

    BKUP-02: Restore completes within 15 minutes.
    BKUP-03: Recovers all data including audit events and configuration.
    """
    try:
        result = await restore_backup(
            filename=body.filename,
            backup_dir=DEFAULT_BACKUP_DIR,
        )
    except ValueError as exc:
        # Path traversal / containment violation (GPT5.6 #2).
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("Restore failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Restore failed: {exc}") from exc

    return result
