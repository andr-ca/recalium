"""Derived memory ORM models.

CASCADE CONTRACT: Every table here includes source_status (source_status ENUM).
ALL read queries MUST filter WHERE source_status = 'active'.

SECURITY: No column here ends with _key, _secret, _token, or _password.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import String, Text, TIMESTAMP, ForeignKey, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from app.infrastructure.db import Base

# source_status ENUM was created in migration 0001; reference it without re-creating.
_source_status = SAEnum("active", "source_removed", name="source_status", create_type=False)


class ConflictGroup(Base):
    """Groups of facts that are duplicates, overlaps, or contradictions.

    Facts reference this table via conflict_group_id FK.
    Created before Fact so Fact FK can reference it.
    """
    __tablename__ = "conflict_groups"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    group_type: Mapped[str] = mapped_column(
        String(32), nullable=False
    )
    # "duplicate" | "contradiction" | "overlap"
    source_status: Mapped[str] = mapped_column(
        _source_status, nullable=False, default="active"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )


class Summary(Base):
    """LLM-generated summary of a raw archive item."""
    __tablename__ = "summaries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    raw_archive_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("raw_archive.id", ondelete="CASCADE"),
        nullable=False,
    )
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    model_used: Mapped[str] = mapped_column(String(128), nullable=False)
    # e.g. "gpt-4o-mini", "claude-3-haiku-20240307", "llama3.2"
    derivation_method: Mapped[str] = mapped_column(String(64), nullable=False)
    # "llm_summarization"
    source_status: Mapped[str] = mapped_column(
        _source_status, nullable=False, default="active"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class Fact(Base):
    """A single extracted fact with source span and provenance.

    PIPE-02: source_span, confidence_tier, derivation_method, derivation_model are REQUIRED.
    A fact without source_span must be stored with confidence_tier = 'low'.
    """
    __tablename__ = "facts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    raw_archive_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("raw_archive.id", ondelete="CASCADE"),
        nullable=False,
    )
    fact_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_span: Mapped[str] = mapped_column(Text, nullable=False)
    # REQUIRED — verbatim quote from source. Empty string is invalid at service layer.
    confidence_tier: Mapped[str] = mapped_column(String(16), nullable=False)
    # "high" | "medium" | "low"
    derivation_method: Mapped[str] = mapped_column(String(64), nullable=False)
    # "llm_extraction" | "rule_based"
    derivation_model: Mapped[str] = mapped_column(String(128), nullable=False)
    # e.g. "gpt-4o-mini", "claude-3-haiku-20240307", "local_rules_v1"
    conflict_group_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conflict_groups.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_status: Mapped[str] = mapped_column(
        _source_status, nullable=False, default="active"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class Embedding(Base):
    """Vector embedding for a raw archive item (all-MiniLM-L6-v2, 384 dims)."""
    __tablename__ = "embeddings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    raw_archive_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("raw_archive.id", ondelete="CASCADE"),
        nullable=False,
    )
    embedding: Mapped[list[float]] = mapped_column(Vector(384), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(128), nullable=False)
    # "all-MiniLM-L6-v2" — record model name to detect stale embeddings on switch
    source_status: Mapped[str] = mapped_column(
        _source_status, nullable=False, default="active"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )


class FtsEntry(Base):
    """Full-text search index entry for a raw archive item."""
    __tablename__ = "fts_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    raw_archive_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("raw_archive.id", ondelete="CASCADE"),
        nullable=False,
    )
    text_content: Mapped[str] = mapped_column(Text, nullable=False)
    # Combined text: summary + facts for richer FTS recall
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR, nullable=True)
    # Populated by worker via to_tsvector('english', text_content)
    source_status: Mapped[str] = mapped_column(
        _source_status, nullable=False, default="active"
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
