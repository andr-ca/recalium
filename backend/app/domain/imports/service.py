"""Import domain service — fan an export out into per-conversation archive items.

Each normalized conversation becomes its own ``raw_archive`` row with a stable
``content_hash`` (idempotent re-import) plus provenance metadata, an ``import``
audit event, and a ``pending_pipeline`` job so it is summarized, extracted, and
linked individually — the same path a pasted conversation follows.
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.archive.models import RawArchiveItem
from app.domain.audit.models import AuditEvent
from app.domain.imports.adapters import (
    NormalizedConversation,
    parse_export,
    render_conversation_text,
)
from app.domain.jobs.models import Job

logger = logging.getLogger(__name__)

_SOURCE_TYPE = {"chatgpt": "chatgpt_import", "claude": "claude_import"}


@dataclass
class ImportResult:
    """Outcome of importing an export file."""

    source_format: str
    conversation_count: int
    imported: int
    skipped: int
    archive_ids: list[UUID] = field(default_factory=list)


def _conversation_hash(conv: NormalizedConversation, rendered: str) -> str:
    """Stable identity for a conversation: source + id + rendered content."""
    basis = f"{conv.source_system}:{conv.source_conversation_id or ''}:{rendered}"
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()


async def import_conversations(
    session: AsyncSession,
    content: str,
    actor: str = "user_import",
) -> ImportResult:
    """Import a ChatGPT/Claude export, one archive item per conversation.

    Raises ``ValueError`` for invalid JSON, an unrecognized format, or an export
    with no usable conversations. Already-imported conversations (matching
    ``content_hash``) are skipped so re-importing an export is idempotent.
    """
    try:
        data = json.loads(content)
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"Import file is not valid JSON: {exc}") from exc

    source_format, conversations = parse_export(data)
    if source_format is None:
        raise ValueError(
            "Unrecognized export format. Expected a ChatGPT or Claude "
            "conversations export (conversations.json)."
        )
    if not conversations:
        raise ValueError(
            f"No conversations with content were found in the {source_format} export."
        )

    source_type = _SOURCE_TYPE.get(source_format, f"{source_format}_import")
    imported: list[UUID] = []
    skipped = 0

    for conv in conversations:
        rendered = render_conversation_text(conv)
        if not rendered.strip():
            skipped += 1
            continue

        content_hash = _conversation_hash(conv, rendered)
        existing = (
            await session.execute(
                text(
                    "SELECT id::text AS id FROM raw_archive "
                    "WHERE content_hash = :h AND deleted_at IS NULL LIMIT 1"
                ),
                {"h": content_hash},
            )
        ).mappings().first()
        if existing is not None:
            skipped += 1
            continue

        archive_item = RawArchiveItem(
            source_type=source_type,
            source_name=conv.title[:255],
            source_uri=(
                f"{conv.source_system}:{conv.source_conversation_id}"
                if conv.source_conversation_id
                else None
            ),
            raw_content=rendered,
            content_hash=content_hash,
            conversation_count=1,
            metadata_json={
                "source_system": conv.source_system,
                "source_conversation_id": conv.source_conversation_id,
                "title": conv.title,
                "message_count": conv.message_count,
                "created_at": conv.created_at,
                "updated_at": conv.updated_at,
                "import_format": source_format,
            },
        )
        session.add(archive_item)
        await session.flush()  # assign archive_item.id without committing

        session.add(
            AuditEvent(
                event_type="import",
                raw_archive_id=archive_item.id,
                actor=actor,
                operation_metadata={
                    "source_system": conv.source_system,
                    "source_conversation_id": conv.source_conversation_id,
                    "message_count": conv.message_count,
                    "content_hash": content_hash,
                },
            )
        )
        session.add(
            Job(
                job_type="pending_pipeline",
                raw_archive_id=archive_item.id,
                status="pending",
            )
        )
        imported.append(archive_item.id)

    await session.commit()

    logger.info(
        "Import: format=%s conversations=%d imported=%d skipped=%d",
        source_format,
        len(conversations),
        len(imported),
        skipped,
    )
    return ImportResult(
        source_format=source_format,
        conversation_count=len(conversations),
        imported=len(imported),
        skipped=skipped,
        archive_ids=imported,
    )
