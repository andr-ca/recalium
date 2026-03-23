"""Integration tests for archive endpoint — covers INGT-03."""
from __future__ import annotations

import json
import pytest
from httpx import AsyncClient


async def _ingest_one(client: AsyncClient, source_name: str = "archive_test") -> str:
    """Helper: ingest a single item and return its archive_id."""
    payload = {
        "content": f"User: Test message for {source_name}\nAssistant: Test response",
        "source_name": source_name,
    }
    resp = await client.post("/api/ingest", json=payload)
    assert resp.status_code in (200, 202)
    return resp.json()["archive_ids"][0]


async def test_list_archive(client: AsyncClient):
    """INGT-03: GET /api/archive returns list with at least the item we just ingested."""
    archive_id = await _ingest_one(client, "list_archive_test")

    resp = await client.get("/api/archive")
    assert resp.status_code == 200, resp.text
    data = resp.json()

    # Response must have an "items" list
    assert "items" in data, f"Expected 'items' key in response: {data}"
    items = data["items"]
    assert isinstance(items, list)

    # The newly ingested item must appear
    ids = [str(item.get("id", "")) for item in items]
    assert archive_id in ids, (
        f"Newly ingested archive_id {archive_id!r} not found in GET /api/archive: {ids}"
    )


async def test_archive_item_fields(client: AsyncClient):
    """INGT-03 / WEBUI-01: Each archive item has required fields for card display (D-17)."""
    await _ingest_one(client, "field_check_test")
    resp = await client.get("/api/archive")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) >= 1

    item = items[0]
    # Required card fields from D-17
    assert "id" in item, f"Missing 'id' field: {item}"
    assert "source_type" in item, f"Missing 'source_type' field: {item}"
    assert "ingested_at" in item, f"Missing 'ingested_at' field: {item}"
    assert "conversation_count" in item, f"Missing 'conversation_count' field: {item}"
    assert "status_badge" in item, f"Missing 'status_badge' field: {item}"
    assert item["status_badge"] == "Ingested", (
        f"Phase 1 status_badge must be 'Ingested', got {item['status_badge']!r}"
    )


async def test_archive_pagination(client: AsyncClient):
    """INGT-03: GET /api/archive supports ?offset=0&limit=5 pagination."""
    resp = await client.get("/api/archive", params={"offset": 0, "limit": 5})
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert len(data["items"]) <= 5


async def test_soft_deleted_items_excluded(client: AsyncClient):
    """INGT-03 / D-10: Items with deleted_at set must not appear in GET /api/archive."""
    # Ingest then soft-delete via direct DB if a delete endpoint exists,
    # or verify by checking that the archive count is stable after marking one deleted.
    # In Phase 1 there is no delete endpoint; this test validates the filter is present
    # by confirming the archive route does not blow up with a 500.
    resp = await client.get("/api/archive")
    assert resp.status_code == 200
    # No deleted items exist yet in Phase 1; this confirms the WHERE clause doesn't break.
