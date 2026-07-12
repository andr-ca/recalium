"""Add facts FTS generated column + GIN index (direct fact retrieval).

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-11 00:00:00.000000

GPT5.6 #4: facts were only reachable via link traversal. This adds a DB-generated
tsvector over fact_text and a GIN index so a query can match a fact directly.
"""
from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE facts ADD COLUMN search_vector TSVECTOR "
        "GENERATED ALWAYS AS (to_tsvector('english', fact_text)) STORED"
    )
    op.execute("CREATE INDEX ix_facts_fts ON facts USING GIN (search_vector)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_facts_fts")
    op.execute("ALTER TABLE facts DROP COLUMN IF EXISTS search_vector")
