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
