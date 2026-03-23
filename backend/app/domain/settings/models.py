"""Settings domain ORM model.

SECURITY CONTRACT (D-12, Pitfall 5):
- This table stores ONLY key fingerprints (last 4 chars) and booleans.
- NEVER add columns named *_key, *_secret, *_token that hold full credentials.
- The startup assertion in app/main.py enforces this contract at runtime.
- Real API keys live ONLY in .env / environment variables.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, Integer, String, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db import Base


class Settings(Base):
    """Singleton settings row (id=1 always).

    All key_fingerprint columns: last 4 characters of the API key, or None.
    All key_configured columns: True if key is set in environment, False otherwise.
    Validation status: "valid" | "invalid" | "insufficient_permissions" | "unchecked" | None
    """
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Always id=1 (singleton)

    # OpenAI
    openai_key_fingerprint: Mapped[str | None] = mapped_column(String(4), nullable=True)
    openai_key_configured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    openai_validation_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    openai_validated_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    # Anthropic
    anthropic_key_fingerprint: Mapped[str | None] = mapped_column(String(4), nullable=True)
    anthropic_key_configured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    anthropic_validation_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    anthropic_validated_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    # Ollama
    ollama_base_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    ollama_key_fingerprint: Mapped[str | None] = mapped_column(String(4), nullable=True)
    ollama_key_configured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ollama_validation_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ollama_validated_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
