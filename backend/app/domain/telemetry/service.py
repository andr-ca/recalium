"""Telemetry service — increment daily usage counters.

PORT-02: All telemetry stays local. Upsert pattern prevents N+1 selects.

Event type → column mapping:
  "search"            → searches
  "retrieval"         → retrievals
  "mcp_retrieval"     → mcp_retrievals
  "ui_retrieval"      → ui_retrievals
  "fact_reviewed"     → facts_reviewed
  "canonical_created" → canonical_created
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Safety: col is always from this allowlist; f-string interpolation is intentional.
_EVENT_TO_COLUMN: dict[str, str] = {
    "search": "searches",
    "retrieval": "retrievals",
    "mcp_retrieval": "mcp_retrievals",
    "ui_retrieval": "ui_retrievals",
    "fact_reviewed": "facts_reviewed",
    "canonical_created": "canonical_created",
}


async def increment_telemetry(
    session: AsyncSession,
    event_type: str,
    today: date | None = None,
) -> None:
    """Increment a daily usage counter using PostgreSQL upsert.

    Uses INSERT ... ON CONFLICT DO UPDATE — no SELECT first, no ORM object.
    Best-effort: logs a warning and returns on unknown event_type.
    """
    col = _EVENT_TO_COLUMN.get(event_type)
    if col is None:
        logger.warning("Unknown telemetry event_type: %s — skipping", event_type)
        return

    day = today or date.today()

    await session.execute(
        text(
            f'INSERT INTO telemetry ("date", {col}) VALUES (:date, 1) '
            f'ON CONFLICT ("date") DO UPDATE SET {col} = telemetry.{col} + 1'
        ),
        {"date": day},
    )
    # Note: caller is responsible for commit


async def get_telemetry_summary(
    session: AsyncSession,
    days: int = 30,
) -> list[dict]:
    """Return daily telemetry for the last N days, newest first.

    Returns list of dicts with keys: date, searches, retrievals,
    facts_reviewed, canonical_created, mcp_retrievals, ui_retrievals.
    Missing days (no data) are not included.
    """
    cutoff = date.today() - timedelta(days=days - 1)
    result = await session.execute(
        text(
            "SELECT date, searches, retrievals, facts_reviewed, "
            "canonical_created, mcp_retrievals, ui_retrievals "
            'FROM telemetry WHERE "date" >= :cutoff ORDER BY "date" DESC'
        ),
        {"cutoff": cutoff},
    )
    rows = result.fetchall()
    return [
        {
            "date": str(row.date),
            "searches": row.searches,
            "retrievals": row.retrievals,
            "facts_reviewed": row.facts_reviewed,
            "canonical_created": row.canonical_created,
            "mcp_retrievals": row.mcp_retrievals,
            "ui_retrievals": row.ui_retrievals,
        }
        for row in rows
    ]
