"""Add tombstones table (deletion ledger).

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-11 00:00:00.000000

GPT5.6 #2: durable append-only deletion ledger. Records every source removal so
deleted content cannot silently reappear after a restore, reindex, or import.
Mirrored to an external NDJSON ledger file (outside the DB dump) for cross-restore
safety; this table is the in-database, backup-included record.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tombstones",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("source_id", UUID(as_uuid=True), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("removal_type", sa.String(length=16), nullable=False, server_default="delete"),
        sa.Column("removed_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("actor", sa.String(length=128), nullable=False, server_default="user_ui"),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "suppression_scope",
            sa.String(length=32),
            nullable=False,
            server_default="source_item",
        ),
    )
    op.create_index("ix_tombstones_source_id", "tombstones", ["source_id"])
    op.create_index("ix_tombstones_content_hash", "tombstones", ["content_hash"])


def downgrade() -> None:
    op.drop_index("ix_tombstones_content_hash", table_name="tombstones")
    op.drop_index("ix_tombstones_source_id", table_name="tombstones")
    op.drop_table("tombstones")
