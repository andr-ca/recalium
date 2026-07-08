"""Add tags, fact_tags, and memory_links tables.

Revision ID: 0005
Revises: 0004
Create Date: 2026-01-01 00:00:00.000000

Tags: canonical label strings (unique name).
FactTags: many-to-many association between facts and tags.
MemoryLinks: directed typed links between two facts.

CASCADE CONTRACT: implicit cleanup via join on facts.source_status='active'.
No source_status column needed on these tables — they are derived data.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── tags ─────────────────────────────────────────────────────────────────
    op.create_table(
        "tags",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("name", name="uq_tags_name"),
    )
    op.create_index("ix_tags_name", "tags", ["name"], unique=True)

    # ── fact_tags ─────────────────────────────────────────────────────────────
    op.create_table(
        "fact_tags",
        sa.Column("fact_id", UUID(as_uuid=True), nullable=False),
        sa.Column("tag_id", UUID(as_uuid=True), nullable=False),
        sa.Column("assigned_by", sa.String(32), nullable=False, server_default="pipeline"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("fact_id", "tag_id", name="pk_fact_tags"),
        sa.ForeignKeyConstraint(
            ["fact_id"], ["facts.id"], ondelete="CASCADE", name="fk_fact_tags_fact"
        ),
        sa.ForeignKeyConstraint(
            ["tag_id"], ["tags.id"], ondelete="CASCADE", name="fk_fact_tags_tag"
        ),
    )
    op.create_index("ix_fact_tags_fact_id", "fact_tags", ["fact_id"])
    op.create_index("ix_fact_tags_tag_id", "fact_tags", ["tag_id"])

    # ── memory_links ──────────────────────────────────────────────────────────
    op.create_table(
        "memory_links",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("source_fact_id", UUID(as_uuid=True), nullable=False),
        sa.Column("target_fact_id", UUID(as_uuid=True), nullable=False),
        sa.Column("link_type", sa.String(32), nullable=False),
        sa.Column("entity_name", sa.Text, nullable=True),
        sa.Column("confidence", sa.Float, nullable=False, server_default="1.0"),
        sa.Column("created_by", sa.String(32), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["source_fact_id"],
            ["facts.id"],
            ondelete="CASCADE",
            name="fk_memory_links_source",
        ),
        sa.ForeignKeyConstraint(
            ["target_fact_id"],
            ["facts.id"],
            ondelete="CASCADE",
            name="fk_memory_links_target",
        ),
        sa.UniqueConstraint(
            "source_fact_id",
            "target_fact_id",
            "link_type",
            name="uq_memory_links_triplet",
        ),
        sa.CheckConstraint(
            "source_fact_id != target_fact_id",
            name="chk_memory_links_no_self",
        ),
    )
    op.create_index("ix_memory_links_source", "memory_links", ["source_fact_id"])
    op.create_index("ix_memory_links_target", "memory_links", ["target_fact_id"])
    op.create_index("ix_memory_links_type", "memory_links", ["link_type"])


def downgrade() -> None:
    op.drop_index("ix_memory_links_type", table_name="memory_links")
    op.drop_index("ix_memory_links_target", table_name="memory_links")
    op.drop_index("ix_memory_links_source", table_name="memory_links")
    op.drop_table("memory_links")

    op.drop_index("ix_fact_tags_tag_id", table_name="fact_tags")
    op.drop_index("ix_fact_tags_fact_id", table_name="fact_tags")
    op.drop_table("fact_tags")

    op.drop_index("ix_tags_name", table_name="tags")
    op.drop_table("tags")
