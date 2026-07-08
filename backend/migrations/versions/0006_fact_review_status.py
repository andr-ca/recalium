"""Add review_status column to facts.

Revision ID: 0006
Revises: 0005
Create Date: 2026-04-27 00:00:00.000000

Fact review status tracks user curation state independently from source
removal state. source_status remains the raw-source cascade contract.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "facts",
        sa.Column(
            "review_status",
            sa.String(length=32),
            nullable=False,
            server_default="active",
        ),
    )
    op.create_index("ix_facts_review_status", "facts", ["review_status"])


def downgrade() -> None:
    op.drop_index("ix_facts_review_status", table_name="facts")
    op.drop_column("facts", "review_status")
