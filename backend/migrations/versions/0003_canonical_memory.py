"""Canonical memory and review queue tables.

IMPORTANT:
- pgvector extension already created in 0001 — NOT re-created here.
- source_status ENUM already created in 0001 — NOT re-created here.

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-23
"""
from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── canonical_memory ───────────────────────────────────────────────────
    op.create_table(
        "canonical_memory",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "raw_archive_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("raw_archive.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "fact_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("facts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("status", sa.String(64), nullable=False, server_default="active"),
        sa.Column(
            "source_status",
            postgresql.ENUM(name="source_status", create_type=False),
            nullable=False,
            server_default="active",
        ),
        sa.Column("promoted_from", sa.String(32), nullable=False),
        sa.Column("promoted_by", sa.String(64), nullable=False, server_default="user_ui"),
        sa.Column("provenance_note", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_canonical_memory_status", "canonical_memory", ["status"])
    op.create_index("ix_canonical_memory_source_status", "canonical_memory", ["source_status"])
    op.create_index("ix_canonical_memory_raw_archive_id", "canonical_memory", ["raw_archive_id"],
                    postgresql_where=sa.text("raw_archive_id IS NOT NULL"))
    op.create_index("ix_canonical_memory_fact_id", "canonical_memory", ["fact_id"],
                    postgresql_where=sa.text("fact_id IS NOT NULL"))
    # FTS index on content for keyword search inclusion
    op.execute(
        "ALTER TABLE canonical_memory ADD COLUMN search_vector TSVECTOR "
        "GENERATED ALWAYS AS (to_tsvector('english', content)) STORED"
    )
    op.execute("CREATE INDEX ix_canonical_memory_fts ON canonical_memory USING GIN (search_vector)")

    # ── review_queue_items ─────────────────────────────────────────────────
    op.create_table(
        "review_queue_items",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "conflict_group_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("conflict_groups.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("item_type", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column(
            "source_status",
            postgresql.ENUM(name="source_status", create_type=False),
            nullable=False,
            server_default="active",
        ),
        sa.Column("resolution_note", sa.Text, nullable=True),
        sa.Column("resolved_by", sa.String(64), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("resolved_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index("ix_review_queue_items_status", "review_queue_items", ["status"])
    op.create_index("ix_review_queue_items_conflict_group_id", "review_queue_items", ["conflict_group_id"])
    op.create_index("ix_review_queue_items_source_status", "review_queue_items", ["source_status"])


def downgrade() -> None:
    # Drop FK constraints explicitly before dropping tables (prevents FK violation errors)
    op.drop_constraint("review_queue_items_conflict_group_id_fkey", "review_queue_items", type_="foreignkey")
    op.drop_table("review_queue_items")
    op.drop_constraint("canonical_memory_raw_archive_id_fkey", "canonical_memory", type_="foreignkey")
    op.drop_constraint("canonical_memory_fact_id_fkey", "canonical_memory", type_="foreignkey")
    op.drop_table("canonical_memory")
