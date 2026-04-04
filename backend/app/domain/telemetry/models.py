"""Telemetry ORM model — local usage counters.

PORT-02: Telemetry visible in Settings, never exported.
SECURITY: No API keys or sensitive data here.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Integer, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db import Base


class TelemetryDay(Base):
    """Daily usage counter row. One row per calendar day."""
    __tablename__ = "telemetry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, unique=True)
    searches: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    retrievals: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    facts_reviewed: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    canonical_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    mcp_retrievals: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
    ui_retrievals: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default=text("0"))
