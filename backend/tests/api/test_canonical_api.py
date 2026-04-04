"""Canonical memory API route tests — Phase 3.

Covers: CANM-01 (CRUD via API), CANM-03 (no auto-promote), CANM-04 (confirm required).

RED until plan 03-06 implements canonical routes.
"""
import pytest
pytest.importorskip("app.domain.canonical_memory.service")

import uuid

from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_canonical_returns_200(client: AsyncClient):
    """CANM-01: GET /api/canonical returns list."""
    resp = await client.get("/api/canonical")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data


@pytest.mark.asyncio
async def test_create_canonical_manual(client: AsyncClient):
    """CANM-01: POST /api/canonical creates a manual canonical item."""
    resp = await client.post("/api/canonical", json={
        "content": "I use Python for all data tasks.",
        "promoted_from": "manual",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "active"
    assert data["promoted_from"] == "manual"
    assert "id" in data


@pytest.mark.asyncio
async def test_update_canonical_item(client: AsyncClient):
    """CANM-01: PATCH /api/canonical/{id} updates content."""
    create_resp = await client.post("/api/canonical", json={
        "content": "Original content.",
        "promoted_from": "manual",
    })
    assert create_resp.status_code == 201
    item_id = create_resp.json()["id"]

    patch_resp = await client.patch(f"/api/canonical/{item_id}", json={
        "content": "Updated content.",
    })
    assert patch_resp.status_code == 200
    assert patch_resp.json()["content"] == "Updated content."


@pytest.mark.asyncio
async def test_delete_canonical_item(client: AsyncClient):
    """CANM-01: DELETE /api/canonical/{id} removes item from active list."""
    create_resp = await client.post("/api/canonical", json={
        "content": "to delete",
        "promoted_from": "manual",
    })
    item_id = create_resp.json()["id"]
    del_resp = await client.delete(f"/api/canonical/{item_id}")
    assert del_resp.status_code == 204

    list_resp = await client.get("/api/canonical")
    ids = [i["id"] for i in list_resp.json()["items"]]
    assert item_id not in ids


@pytest.mark.asyncio
async def test_mark_canonical_disputed(client: AsyncClient):
    """CANM-01: POST /api/canonical/{id}/dispute marks item as disputed."""
    create_resp = await client.post("/api/canonical", json={
        "content": "disputed fact",
        "promoted_from": "manual",
    })
    item_id = create_resp.json()["id"]
    dispute_resp = await client.post(f"/api/canonical/{item_id}/dispute")
    assert dispute_resp.status_code == 200
    assert dispute_resp.json()["status"] == "disputed"


@pytest.mark.asyncio
async def test_promote_fact_no_source_span_requires_confirmed(client: AsyncClient):
    """CANM-04: promote without source_span requires confirmed=true."""
    resp = await client.post("/api/canonical/promote", json={
        "fact_id": str(uuid.uuid4()),
        "raw_archive_id": str(uuid.uuid4()),
        "content": "fact without span",
        "has_source_span": False,
        "confirmed": False,
    })
    assert resp.status_code == 409  # Conflict — requires explicit confirmation
