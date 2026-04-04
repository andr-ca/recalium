"""Add telemetry table and verbose_audit column to settings.

- telemetry: daily usage counters (PORT-02)
- settings.verbose_audit: configurable audit verbosity (WEBUI-06)

IMPORTANT:
- pgvector extension already created in 0001 — NOT re-created here.
- source_status ENUM already created in 0001 — NOT re-created here.

Revision ID: 0004
Revises: 0003
Create Date: 2026-03-23
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── telemetry table ─────────────────────────────────────────────────────
    # Daily usage counters. Never exported (PORT-02).
    op.create_table(
        "telemetry",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("date", sa.Date, nullable=False, unique=True),
        sa.Column("searches", sa.Integer, nullable=False, server_default="0"),
        sa.Column("retrievals", sa.Integer, nullable=False, server_default="0"),
        sa.Column("facts_reviewed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("canonical_created", sa.Integer, nullable=False, server_default="0"),
        sa.Column("mcp_retrievals", sa.Integer, nullable=False, server_default="0"),
        sa.Column("ui_retrievals", sa.Integer, nullable=False, server_default="0"),
    )
    op.create_index("ix_telemetry_date", "telemetry", ["date"])

    # ── settings.verbose_audit ──────────────────────────────────────────────
    # Configurable audit verbosity toggle (WEBUI-06).
    op.add_column(
        "settings",
        sa.Column("verbose_audit", sa.Boolean, nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("settings", "verbose_audit")
    op.drop_index("ix_telemetry_date", table_name="telemetry")
    op.drop_table("telemetry")
