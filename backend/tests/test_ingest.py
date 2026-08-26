"""Integration tests for ingest endpoints — covers INGT-01, INGT-02, INGT-03."""
from __future__ import annotations

import json
import time
import pytest
from httpx import AsyncClient


# ── INGT-01: Paste ingest ────────────────────────────────────────────────────

async def test_paste_ingest(client: AsyncClient):
    """INGT-01: POST /api/ingest with plain text returns 202 and at least one archive_id."""
    payload = {
        "content": "User: Hello\nAssistant: Hi there!\n\nUser: How are you?\nAssistant: I'm doing well.",
        "source_name": "test_paste",
    }
    resp = await client.post("/api/ingest", json=payload)
    assert resp.status_code in (200, 202), resp.text
    data = resp.json()
    assert "archive_ids" in data, f"Missing archive_ids in response: {data}"
    assert len(data["archive_ids"]) >= 1
    assert "item_count" in data
    assert data["item_count"] >= 1


async def test_ingest_latency(client: AsyncClient):
    """INGT-01 / INGT-03: Single paste ingest completes within 1 second (P95 proxy)."""
    payload = {
        "content": "User: Quick test\nAssistant: Quick response",
        "source_name": "latency_test",
    }
    start = time.monotonic()
    resp = await client.post("/api/ingest", json=payload)
    elapsed = time.monotonic() - start
    assert resp.status_code in (200, 202)
    assert elapsed < 1.0, f"Ingest took {elapsed:.3f}s — must be < 1.0s"


async def test_paste_ingest_empty_returns_error(client: AsyncClient):
    """INGT-01: POST /api/ingest with empty content returns 422."""
    resp = await client.post("/api/ingest", json={"content": ""})
    assert resp.status_code == 422


async def test_rest_ingest_accepts_mcp_aligned_metadata(client: AsyncClient):
    """Issue #41: REST accepts source_metadata + client fields for daemon clients."""
    payload = {
        "content": "Daemon flush: remember the deploy window is Fridays only.",
        "source_metadata": {
            "source_type": "ntfy_pipeline",
            "source_name": "bobbonson-outbox",
            "conversation_id": "conv-rest-001",
        },
        "client_identity": "outbox-flusher-test",
        "import_method": "rest_api",
        "idempotency_key": "rest-meta-key-001",
        "sensitivity_hint": "normal",
        "project_hint": "recalium",
        "processing_mode": "deferred",
    }
    resp = await client.post("/api/ingest", json=payload)
    assert resp.status_code == 202, resp.text
    data = resp.json()
    assert data["status"] == "accepted"
    assert data["idempotent_replay"] is False
    assert data["idempotency_key"] == "rest-meta-key-001"
    assert len(data["archive_ids"]) >= 1


async def test_rest_ingest_idempotent_replay(client: AsyncClient):
    """Issue #41: same idempotency_key + same content replays without duplicate."""
    key = "rest-idempotency-replay-001"
    payload = {
        "content": "Outbox replay test: durable note about Friday deploys.",
        "source_metadata": {"source_type": "ntfy_pipeline", "source_name": "outbox"},
        "client_identity": "outbox-flusher-test",
        "idempotency_key": key,
    }
    first = await client.post("/api/ingest", json=payload)
    assert first.status_code == 202, first.text
    first_data = first.json()

    replay = await client.post("/api/ingest", json=payload)
    assert replay.status_code == 202, replay.text
    replay_data = replay.json()
    assert replay_data["idempotent_replay"] is True
    assert replay_data["archive_ids"] == first_data["archive_ids"]


async def test_rest_ingest_idempotency_conflict(client: AsyncClient):
    """Issue #41: same key with different content returns 409 conflict."""
    key = "rest-idempotency-conflict-001"
    first = await client.post(
        "/api/ingest",
        json={
            "content": "First payload for conflict test, long enough.",
            "idempotency_key": key,
            "source_metadata": {"source_type": "api", "source_name": "conflict"},
        },
    )
    assert first.status_code == 202, first.text

    conflict = await client.post(
        "/api/ingest",
        json={
            "content": "Different payload for the same idempotency key!!",
            "idempotency_key": key,
            "source_metadata": {"source_type": "api", "source_name": "conflict"},
        },
    )
    assert conflict.status_code == 409, conflict.text
    detail = conflict.json()["detail"]
    assert detail["error"]["code"] == "idempotency_conflict"
    assert detail["error"]["retryable"] is False


async def test_rest_ingest_rejects_invalid_processing_mode(client: AsyncClient):
    """Issue #41: invalid processing_mode is rejected at the REST boundary."""
    resp = await client.post(
        "/api/ingest",
        json={
            "content": "Valid length content for processing mode check.",
            "processing_mode": "not_a_real_mode",
        },
    )
    assert resp.status_code == 422, resp.text


# ── INGT-02: File upload ─────────────────────────────────────────────────────

CHATGPT_EXPORT = {
    "title": "Test Conversation",
    "create_time": 1700000000.0,
    "update_time": 1700000100.0,
    "mapping": {
        "node-1": {
            "id": "node-1",
            "message": {
                "id": "msg-1",
                "author": {"role": "user"},
                "content": {"parts": ["Hello from ChatGPT export"]},
                "create_time": 1700000000.0,
            },
            "parent": None,
            "children": ["node-2"],
        },
        "node-2": {
            "id": "node-2",
            "message": {
                "id": "msg-2",
                "author": {"role": "assistant"},
                "content": {"parts": ["Hello! How can I help?"]},
                "create_time": 1700000010.0,
            },
            "parent": "node-1",
            "children": [],
        },
    },
}

CLAUDE_EXPORT = [
    {
        "uuid": "conv-abc-123",
        "name": "Test Claude Conversation",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:01:00Z",
        "chat_messages": [
            {"uuid": "msg-1", "sender": "human", "text": "Hello from Claude export"},
            {"uuid": "msg-2", "sender": "assistant", "text": "Hello! I am Claude."},
        ],
    }
]

GENERIC_JSON = {
    "conversations": [
        {
            "id": "generic-1",
            "messages": [
                {"role": "user", "content": "Generic user message"},
                {"role": "assistant", "content": "Generic assistant response"},
            ],
        }
    ]
}


async def test_chatgpt_upload(client: AsyncClient):
    """INGT-02: POST /api/ingest/file with ChatGPT JSON export creates at least 1 item."""
    content = json.dumps(CHATGPT_EXPORT).encode()
    resp = await client.post(
        "/api/ingest/file",
        files={"file": ("conversations.json", content, "application/json")},
    )
    assert resp.status_code in (200, 202), resp.text
    data = resp.json()
    assert data["item_count"] >= 1
    assert len(data["archive_ids"]) >= 1


async def test_claude_upload(client: AsyncClient):
    """INGT-02: POST /api/ingest/file with Claude JSON export creates at least 1 item."""
    content = json.dumps(CLAUDE_EXPORT).encode()
    resp = await client.post(
        "/api/ingest/file",
        files={"file": ("claude_conversations.json", content, "application/json")},
    )
    assert resp.status_code in (200, 202), resp.text
    data = resp.json()
    assert data["item_count"] >= 1


async def test_generic_json_upload(client: AsyncClient):
    """INGT-02: POST /api/ingest/file with generic JSON structure is handled gracefully."""
    content = json.dumps(GENERIC_JSON).encode()
    resp = await client.post(
        "/api/ingest/file",
        files={"file": ("export.json", content, "application/json")},
    )
    # Generic JSON should succeed (even if parsed as a single item) or return 422 with
    # a clear error — it must NOT return 500
    assert resp.status_code != 500, f"Server error on generic JSON: {resp.text}"


async def test_txt_upload(client: AsyncClient):
    """INGT-02: POST /api/ingest/file with plain .txt file is accepted."""
    content = b"User: Hello\nAssistant: Hi there\n\nUser: Bye\nAssistant: Goodbye"
    resp = await client.post(
        "/api/ingest/file",
        files={"file": ("chat.txt", content, "text/plain")},
    )
    assert resp.status_code in (200, 202), resp.text


async def test_unsupported_extension_returns_error(client: AsyncClient):
    """INGT-02: POST /api/ingest/file with .pdf extension returns 422."""
    content = b"%PDF-1.4 fake pdf content"
    resp = await client.post(
        "/api/ingest/file",
        files={"file": ("document.pdf", content, "application/pdf")},
    )
    assert resp.status_code == 422, f"Expected 422, got {resp.status_code}"
