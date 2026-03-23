"""Derived memory tables: summaries, facts, embeddings, fts_entries, conflict_groups.

IMPORTANT:
- pgvector extension already created in 0001 — NOT re-created here.
- source_status ENUM already created in 0001 — NOT re-created here.
- All five tables include source_status (source_status ENUM, NOT NULL DEFAULT 'active').

CASCADE CONTRACT: Every derived table here has:
  - raw_archive_id FK → raw_archive.id ON DELETE CASCADE
  - source_status source_status NOT NULL DEFAULT 'active'

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-23
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── conflict_groups ────────────────────────────────────────────────────
    # Created first so facts can reference it via FK.
    op.create_table(
        "conflict_groups",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("group_type", sa.String(32), nullable=False),
        # "duplicate" | "contradiction" | "overlap"
        # source_status ENUM created in 0001; reference only, do not create.
        sa.Column(
            "source_status",
            sa.Enum("active", "source_removed", name="source_status", create_type=False),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("resolved_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index("ix_conflict_groups_source_status", "conflict_groups", ["source_status"])

    # ── summaries ──────────────────────────────────────────────────────────
    op.create_table(
        "summaries",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "raw_archive_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("raw_archive.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("summary_text", sa.Text, nullable=False),
        sa.Column("model_used", sa.String(128), nullable=False),
        sa.Column("derivation_method", sa.String(64), nullable=False),
        # source_status ENUM created in 0001; reference only, do not create.
        sa.Column(
            "source_status",
            sa.Enum("active", "source_removed", name="source_status", create_type=False),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_summaries_raw_archive_id", "summaries", ["raw_archive_id"])
    op.create_index("ix_summaries_source_status", "summaries", ["source_status"])

    # ── facts ──────────────────────────────────────────────────────────────
    op.create_table(
        "facts",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "raw_archive_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("raw_archive.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("fact_text", sa.Text, nullable=False),
        sa.Column("source_span", sa.Text, nullable=False),
        # REQUIRED per PIPE-02; empty string rejected at service layer
        sa.Column("confidence_tier", sa.String(16), nullable=False),
        # "high" | "medium" | "low"
        sa.Column("derivation_method", sa.String(64), nullable=False),
        # "llm_extraction" | "rule_based"
        sa.Column("derivation_model", sa.String(128), nullable=False),
        # e.g. "gpt-4o-mini"
        sa.Column(
            "conflict_group_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("conflict_groups.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "source_status",
            sa.Enum("active", "source_removed", name="source_status", create_type=False),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_facts_raw_archive_id", "facts", ["raw_archive_id"])
    op.create_index("ix_facts_source_status", "facts", ["source_status"])
    op.create_index("ix_facts_conflict_group_id", "facts", ["conflict_group_id"],
                    postgresql_where=sa.text("conflict_group_id IS NOT NULL"))

    # ── embeddings ─────────────────────────────────────────────────────────
    op.create_table(
        "embeddings",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "raw_archive_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("raw_archive.id", ondelete="CASCADE"),
            nullable=False,
        ),
        # vector(384) — pgvector extension already enabled in 0001
        sa.Column("embedding_model", sa.String(128), nullable=False),
        # "all-MiniLM-L6-v2"
        sa.Column(
            "source_status",
            sa.Enum("active", "source_removed", name="source_status", create_type=False),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    # Add vector column via raw SQL (pgvector type not available to standard SQLAlchemy ops)
    op.execute("ALTER TABLE embeddings ADD COLUMN embedding vector(384) NOT NULL")
    # HNSW index for cosine similarity ANN search (pgvector 0.5+)
    op.execute("""
        CREATE INDEX ix_embeddings_vector ON embeddings
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)
    op.create_index("ix_embeddings_raw_archive_id", "embeddings", ["raw_archive_id"])
    op.create_index("ix_embeddings_source_status", "embeddings", ["source_status"])

    # ── fts_entries ────────────────────────────────────────────────────────
    op.create_table(
        "fts_entries",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "raw_archive_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("raw_archive.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("text_content", sa.Text, nullable=False),
        sa.Column(
            "source_status",
            sa.Enum("active", "source_removed", name="source_status", create_type=False),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    # Add tsvector column (not a standard SQLAlchemy type; use raw SQL)
    op.execute("ALTER TABLE fts_entries ADD COLUMN search_vector TSVECTOR")
    # GIN index for fast FTS queries
    op.execute("CREATE INDEX ix_fts_search_vector ON fts_entries USING GIN (search_vector)")
    op.create_index("ix_fts_raw_archive_id", "fts_entries", ["raw_archive_id"])
    op.create_index("ix_fts_source_status", "fts_entries", ["source_status"])


def downgrade() -> None:
    op.drop_table("fts_entries")
    op.drop_table("embeddings")
    op.drop_table("facts")
    op.drop_table("summaries")
    op.drop_table("conflict_groups")
