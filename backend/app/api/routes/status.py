"""Status routes — onboarding check."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select as sa_select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.archive.models import RawArchiveItem
from app.domain.settings.service import get_settings_state
from app.infrastructure.db import get_session

router = APIRouter(prefix="/api/status")


class OnboardingStatusResponse(BaseModel):
    should_show_wizard: bool
    has_archive_items: bool
    has_configured_key: bool


@router.get("/onboarding", response_model=OnboardingStatusResponse)
async def onboarding_status(
    session: AsyncSession = Depends(get_session),
) -> OnboardingStatusResponse:
    """GET /api/status/onboarding — check if first-run wizard should be shown.

    BYOK-01: Wizard shown when archive is empty and no key configured.
    Returns:
      should_show_wizard: True if archive empty AND no key configured
      has_archive_items: True if any archive items exist
      has_configured_key: True if any provider key is configured
    """
    # Count non-deleted archive items (idiomatic single-level query)
    count_result = await session.execute(
        sa_select(func.count())
        .select_from(RawArchiveItem)
        .where(RawArchiveItem.deleted_at.is_(None))
    )
    archive_count = count_result.scalar_one()
    has_archive_items = archive_count > 0

    # Use public get_settings_state which syncs configured flags from .env
    settings_state = await get_settings_state(session)
    has_configured_key = bool(
        settings_state.openai.configured
        or settings_state.anthropic.configured
        or settings_state.ollama.configured
    )

    should_show_wizard = not has_archive_items and not has_configured_key

    return OnboardingStatusResponse(
        should_show_wizard=should_show_wizard,
        has_archive_items=has_archive_items,
        has_configured_key=has_configured_key,
    )
