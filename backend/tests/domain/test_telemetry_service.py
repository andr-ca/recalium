"""Tests for local telemetry service.

PORT-02: Local usage telemetry visible in Settings, never leaves local system.
Run: cd backend && uv run python3 -m pytest tests/domain/test_telemetry_service.py -v
"""
from __future__ import annotations

import pytest
pytest.importorskip("app.domain.telemetry.service")

from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.telemetry.service import increment_telemetry, get_telemetry_summary


@pytest.mark.asyncio
async def test_port02_increment_searches(db_session_phase4: AsyncSession):
    """PORT-02: increment_telemetry creates a row for today if absent."""
    await increment_telemetry(db_session_phase4, "search")
    summary = await get_telemetry_summary(db_session_phase4, days=1)
    assert len(summary) >= 1
    today_row = next((r for r in summary if r["date"] == date.today().isoformat()), None)
    assert today_row is not None
    assert today_row["searches"] >= 1


@pytest.mark.asyncio
async def test_port02_increment_idempotent_upsert(db_session_phase4: AsyncSession):
    """PORT-02: multiple increments accumulate correctly."""
    for _ in range(3):
        await increment_telemetry(db_session_phase4, "search")
    summary = await get_telemetry_summary(db_session_phase4, days=1)
    today_row = next((r for r in summary if r["date"] == date.today().isoformat()), None)
    assert today_row is not None
    assert today_row["searches"] >= 3


@pytest.mark.asyncio
async def test_port02_all_event_types(db_session_phase4: AsyncSession):
    """PORT-02: all telemetry event types are accepted."""
    for event_type in ("search", "retrieval", "mcp_retrieval", "ui_retrieval",
                        "fact_reviewed", "canonical_created"):
        await increment_telemetry(db_session_phase4, event_type)
    # Should not raise


@pytest.mark.asyncio
async def test_port02_summary_returns_last_n_days(db_session_phase4: AsyncSession):
    """PORT-02: get_telemetry_summary returns rows for specified day range."""
    await increment_telemetry(db_session_phase4, "search")
    summary = await get_telemetry_summary(db_session_phase4, days=30)
    assert isinstance(summary, list)
    for row in summary:
        assert "date" in row
        assert "searches" in row
        assert "retrievals" in row
