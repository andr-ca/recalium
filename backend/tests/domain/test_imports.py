"""Import domain tests — ChatGPT/Claude export adapters and fan-out service.

Covers GPT5.6 #1: an export must be decomposed into one archive item per
conversation (with provenance), not stored as a single multi-conversation blob.
"""
from __future__ import annotations

from sqlalchemy import text

from app.domain.imports.adapters import (
    NormalizedConversation,
    NormalizedMessage,
    detect_export_format,
    parse_claude_export,
    parse_chatgpt_export,
    parse_export,
    render_conversation_text,
)
from app.domain.imports.service import import_conversations

# ── Fixtures: representative export payloads ────────────────────────────────

CHATGPT_EXPORT = [
    {
        "title": "Trip planning",
        "conversation_id": "c-1",
        "create_time": 1_700_000_000,
        "update_time": 1_700_000_500,
        "mapping": {
            "n2": {
                "message": {
                    "author": {"role": "assistant"},
                    "create_time": 1_700_000_200,
                    "content": {"content_type": "text", "parts": ["Book the flight first."]},
                }
            },
            "n1": {
                "message": {
                    "author": {"role": "user"},
                    "create_time": 1_700_000_100,
                    "content": {"content_type": "text", "parts": ["Help me plan a trip."]},
                }
            },
            "root": {"message": None},
        },
    },
    {
        "title": "Empty one",
        "conversation_id": "c-2",
        "mapping": {"x": {"message": None}},
    },
]

CLAUDE_EXPORT = [
    {
        "uuid": "u-1",
        "name": "Budget questions",
        "created_at": "2024-01-01T00:00:00Z",
        "chat_messages": [
            {"sender": "human", "text": "What is a good savings rate?", "created_at": "2024-01-01T00:00:01Z"},
            {"sender": "assistant", "text": "Aim for 20% of income.", "created_at": "2024-01-01T00:00:02Z"},
        ],
    }
]


# ── Adapter unit tests (no DB) ──────────────────────────────────────────────

def test_detect_chatgpt_format():
    assert detect_export_format(CHATGPT_EXPORT) == "chatgpt"
    assert detect_export_format({"conversations": CHATGPT_EXPORT}) == "chatgpt"


def test_detect_claude_format():
    assert detect_export_format(CLAUDE_EXPORT) == "claude"


def test_detect_unknown_format():
    assert detect_export_format({"foo": "bar"}) is None
    assert detect_export_format([{"unrelated": 1}]) is None


def test_parse_chatgpt_orders_messages_and_maps_roles():
    convs = parse_chatgpt_export(CHATGPT_EXPORT)
    # The empty conversation is dropped.
    assert len(convs) == 1
    conv = convs[0]
    assert conv.source_system == "chatgpt"
    assert conv.source_conversation_id == "c-1"
    assert conv.title == "Trip planning"
    # Ordered by create_time even though the mapping listed n2 before n1.
    assert [m.role for m in conv.messages] == ["user", "assistant"]
    assert conv.messages[0].text == "Help me plan a trip."


def test_parse_claude_maps_sender_to_role():
    convs = parse_claude_export(CLAUDE_EXPORT)
    assert len(convs) == 1
    conv = convs[0]
    assert conv.source_system == "claude"
    assert conv.source_conversation_id == "u-1"
    assert [m.role for m in conv.messages] == ["user", "assistant"]


def test_parse_export_dispatches_by_format():
    fmt, convs = parse_export(CLAUDE_EXPORT)
    assert fmt == "claude"
    assert len(convs) == 1

    fmt, convs = parse_export({"nope": True})
    assert fmt is None
    assert convs == []


def test_render_conversation_text_is_readable_transcript():
    conv = NormalizedConversation(
        source_system="claude",
        title="Budget questions",
        messages=[
            NormalizedMessage(role="user", text="What is a good savings rate?"),
            NormalizedMessage(role="assistant", text="Aim for 20% of income."),
        ],
    )
    rendered = render_conversation_text(conv)
    assert "# Budget questions" in rendered
    assert "## User" in rendered
    assert "## Assistant" in rendered
    assert "Aim for 20% of income." in rendered


# ── Service / integration tests (DB) ────────────────────────────────────────

async def _count_archive(session, source_type: str) -> int:
    row = await session.execute(
        text("SELECT count(*) AS n FROM raw_archive WHERE source_type = :t AND deleted_at IS NULL"),
        {"t": source_type},
    )
    return int(row.scalar_one())


async def test_import_creates_one_item_per_conversation(db_session):
    import json

    result = await import_conversations(db_session, json.dumps(CHATGPT_EXPORT))

    assert result.source_format == "chatgpt"
    assert result.imported == 1  # empty conversation skipped
    assert len(result.archive_ids) == 1
    assert await _count_archive(db_session, "chatgpt_import") == 1

    # Provenance is recorded on the archive item.
    row = await db_session.execute(
        text(
            "SELECT source_uri, metadata_json ->> 'source_system' AS sys, "
            "metadata_json ->> 'message_count' AS mc "
            "FROM raw_archive WHERE source_type = 'chatgpt_import' LIMIT 1"
        )
    )
    rec = row.mappings().one()
    assert rec["sys"] == "chatgpt"
    assert rec["source_uri"] == "chatgpt:c-1"
    assert rec["mc"] == "2"

    # A pending_pipeline job was enqueued for the imported conversation.
    jobs = await db_session.execute(
        text(
            "SELECT count(*) FROM jobs WHERE raw_archive_id = :rid "
            "AND job_type = 'pending_pipeline'"
        ),
        {"rid": result.archive_ids[0]},
    )
    assert int(jobs.scalar_one()) == 1


async def test_import_is_idempotent(db_session):
    import json

    payload = json.dumps(CLAUDE_EXPORT)
    first = await import_conversations(db_session, payload)
    assert first.imported == 1

    second = await import_conversations(db_session, payload)
    assert second.imported == 0
    assert second.skipped == 1
    assert await _count_archive(db_session, "claude_import") == 1


async def test_import_rejects_unknown_format(db_session):
    import json
    import pytest

    with pytest.raises(ValueError, match="Unrecognized export format"):
        await import_conversations(db_session, json.dumps({"foo": "bar"}))


async def test_import_rejects_invalid_json(db_session):
    import pytest

    with pytest.raises(ValueError, match="not valid JSON"):
        await import_conversations(db_session, "{not json")
