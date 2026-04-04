"""Initial schema: pgvector extension, raw archive, settings (BYOK fingerprints),
jobs stub, and audit events.

SECURITY CONTRACT:
- settings table stores ONLY key fingerprints (last 4 chars) and booleans.
- No column in any table is named *_key, *_secret, or *_token that holds
  a real credential. A startup assertion in app/infrastructure/db.py enforces this.

CASCADE CONTRACT:
- Every future derived table MUST include source_status ENUM('active','source_removed').
- raw_archive uses soft-delete (deleted_at TIMESTAMP NULL).
- All queries must filter deleted_at IS NULL.

Revision ID: 0001
Revises: None
Create Date: 2026-03-22
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── pgvector extension ──────────────────────────────────────────────────
    # Enable pgvector. The extension is pre-installed in pgvector/pgvector:pg16.
    # Embedding columns are added in Phase 2; the extension must exist now.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ── source_status ENUM ─────────────────────────────────────────────────
    # Used on ALL tables with derived data. Created once here, referenced by
    # all derived tables in future migrations.
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE source_status AS ENUM ('active', 'source_removed');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)

    # ── raw_archive table ──────────────────────────────────────────────────
    # Stores every ingested conversation in its raw form.
    # soft-delete: deleted_at IS NULL means active; IS NOT NULL means soft-deleted.
    # All read queries MUST filter WHERE deleted_at IS NULL.
    op.create_table(
        "raw_archive",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("source_type", sa.String(64), nullable=False),
        # "chatgpt_json", "claude_json", "generic_json", "paste_text", "paste_markdown"
        sa.Column("source_name", sa.String(255), nullable=True),
        # Human-readable name (e.g. "ChatGPT export 2026-01-15")
        sa.Column("source_uri", sa.Text, nullable=True),
        # Optional: original filename or URL hint
        sa.Column("raw_content", sa.Text, nullable=False),
        # The verbatim ingested text / JSON
        sa.Column("content_hash", sa.String(64), nullable=False),
        # SHA-256 of raw_content for dedup detection (added Phase 2)
        sa.Column("conversation_count", sa.Integer, nullable=False, server_default="1"),
        # Number of conversations/turns in this raw item
        sa.Column("ingested_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        # Soft-delete: NULL = active; NOT NULL = deleted; filter in ALL queries
        sa.Column("metadata_json", sa.JSON, nullable=True),
        # Extra structured metadata from the source (e.g. ChatGPT conversation ID)
    )
    op.create_index("ix_raw_archive_ingested_at", "raw_archive", ["ingested_at"])
    op.create_index("ix_raw_archive_deleted_at", "raw_archive", ["deleted_at"],
                    postgresql_where=sa.text("deleted_at IS NOT NULL"))
    op.create_index("ix_raw_archive_content_hash", "raw_archive", ["content_hash"])

    # ── settings table (BYOK fingerprints — NO plaintext keys) ────────────
    # SECURITY: This table MUST NEVER hold plaintext API keys.
    # Columns ending in _fingerprint store the last 4 characters of a key.
    # Columns ending in _configured store a boolean: key is set in .env.
    # The actual keys live ONLY in .env / environment variables.
    op.create_table(
        "settings",
        sa.Column("id", sa.Integer, primary_key=True),
        # Single-row table (singleton pattern); id is always 1.

        # OpenAI
        sa.Column("openai_key_fingerprint", sa.String(4), nullable=True),
        sa.Column("openai_key_configured", sa.Boolean, nullable=False, server_default="false"),

        # Anthropic
        sa.Column("anthropic_key_fingerprint", sa.String(4), nullable=True),
        sa.Column("anthropic_key_configured", sa.Boolean, nullable=False, server_default="false"),

        # Ollama
        sa.Column("ollama_base_url", sa.String(512), nullable=True),
        # Ollama URL is not sensitive — storing it is fine
        sa.Column("ollama_key_fingerprint", sa.String(4), nullable=True),
        sa.Column("ollama_key_configured", sa.Boolean, nullable=False, server_default="false"),

        # Validation results (last check)
        sa.Column("openai_validation_status", sa.String(32), nullable=True),
        # "valid", "invalid", "insufficient_permissions", "unchecked"
        sa.Column("anthropic_validation_status", sa.String(32), nullable=True),
        sa.Column("ollama_validation_status", sa.String(32), nullable=True),
        sa.Column("openai_validated_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("anthropic_validated_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("ollama_validated_at", sa.TIMESTAMP(timezone=True), nullable=True),

        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    # Insert the singleton row so reads never return NULL
    op.execute("INSERT INTO settings (id) VALUES (1) ON CONFLICT DO NOTHING")

    # ── jobs table (stub for Phase 2 worker) ──────────────────────────────
    # Phase 1 stub: enqueue jobs at ingest time; worker processes them in Phase 2.
    # index on (status, created_at) per Pitfall 9 (full table scan prevention).
    op.create_table(
        "jobs",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_type", sa.String(64), nullable=False),
        # Phase 2 job types: "summarize", "extract_facts", "embed", "index_fts", "dedup"
        sa.Column("raw_archive_id", sa.UUID(as_uuid=True), sa.ForeignKey("raw_archive.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="'pending'"),
        # "pending", "claimed", "completed", "failed", "retryable_failed"
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer, nullable=False, server_default="3"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("claimed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    # Composite index for SKIP LOCKED polling (Pitfall 9 prevention)
    op.create_index("ix_jobs_status_created_at", "jobs", ["status", "created_at"])
    op.create_index("ix_jobs_raw_archive_id", "jobs", ["raw_archive_id"])

    # ── audit_events table ─────────────────────────────────────────────────
    # Append-only event log. Must be persisted to DB from day one (see PITFALLS.md
    # technical debt patterns: "Store audit events in application memory" — NEVER).
    op.create_table(
        "audit_events",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("event_type", sa.String(64), nullable=False),
        # "ingest", "archive_read", "settings_update", "key_validation", "delete"
        sa.Column("raw_archive_id", sa.UUID(as_uuid=True), nullable=True),
        # FK to raw_archive (nullable for non-archive events like settings_update)
        sa.Column("actor", sa.String(64), nullable=False, server_default="'user_ui'"),
        # "user_ui", "mcp_client", "worker", "system"
        sa.Column("operation_metadata", sa.JSON, nullable=True),
        # Structured details: source_type, conversation_count, etc.
        sa.Column("occurred_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_audit_events_occurred_at", "audit_events", ["occurred_at"])
    op.create_index("ix_audit_events_event_type", "audit_events", ["event_type"])
    op.create_index("ix_audit_events_raw_archive_id", "audit_events", ["raw_archive_id"],
                    postgresql_where=sa.text("raw_archive_id IS NOT NULL"))


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("jobs")
    op.drop_table("settings")
    op.drop_table("raw_archive")
    op.execute("DROP TYPE IF EXISTS source_status")
    op.execute("DROP EXTENSION IF EXISTS vector")
