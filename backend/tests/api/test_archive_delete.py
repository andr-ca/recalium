"""Tests for DELETE /api/archive/{id} route.

PRIV-01: API-level tests for the deletion cascade endpoint.
Run: cd backend && uv run python3 -m pytest tests/api/test_archive_delete.py -v
"""
from __future__ import annotations

import hashlib
import uuid

import pytest
pytest.importorskip("app.domain.archive.service")

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.archive.models import RawArchiveItem


def _make_archive_payload(content: str = "Test conversation content") -> dict:
    return {
        "id": str(uuid.uuid4()),
        "source_type": "test",
        "raw_content": content,
        "content_hash": hashlib.sha256(content.encode()).hexdigest(),
    }


@pytest.mark.asyncio
async def test_delete_archive_returns_204(client: AsyncClient, db_session_phase4: AsyncSession):
    """DELETE /api/archive/{id} returns 204 for existing item."""
    # Create archive item directly
    item = RawArchiveItem(
        id=uuid.uuid4(),
        source_type="test",
        raw_content="test content",
        content_hash=hashlib.sha256(b"test content").hexdigest(),
    )
    db_session_phase4.add(item)
    await db_session_phase4.flush()
    await db_session_phase4.commit()

    resp = await client.delete(f"/api/archive/{item.id}")
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_delete_archive_not_found_returns_404(client: AsyncClient):
    """DELETE /api/archive/{id} returns 404 for non-existent item."""
    fake_id = str(uuid.uuid4())
    resp = await client.delete(f"/api/archive/{fake_id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_archive_invalid_id_returns_422(client: AsyncClient):
    """DELETE /api/archive/{id} returns 422 for malformed UUID."""
    resp = await client.delete("/api/archive/not-a-uuid")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_deleted_item_excluded_from_list(client: AsyncClient, db_session_phase4: AsyncSession):
    """PRIV-01: deleted item no longer appears in GET /api/archive."""
    item = RawArchiveItem(
        id=uuid.uuid4(),
        source_type="test",
        raw_content="content to delete",
        content_hash=hashlib.sha256(b"content to delete").hexdigest(),
    )
    db_session_phase4.add(item)
    await db_session_phase4.flush()
    await db_session_phase4.commit()

    # Delete it
    await client.delete(f"/api/archive/{item.id}")

    # Should not appear in default list
    resp = await client.get("/api/archive")
    assert resp.status_code == 200
    ids = [i["id"] for i in resp.json()["items"]]
    assert str(item.id) not in ids


@pytest.mark.asyncio
async def test_deleted_item_visible_with_include_deleted(client: AsyncClient, db_session_phase4: AsyncSession):
    """PRIV-01: deleted item appears in GET /api/archive?include_deleted=true."""
    item = RawArchiveItem(
        id=uuid.uuid4(),
        source_type="test",
        raw_content="content to soft-delete",
        content_hash=hashlib.sha256(b"content to soft-delete").hexdigest(),
    )
    db_session_phase4.add(item)
    await db_session_phase4.flush()
    await db_session_phase4.commit()

    await client.delete(f"/api/archive/{item.id}")

    resp = await client.get("/api/archive?include_deleted=true")
    assert resp.status_code == 200
    ids = [i["id"] for i in resp.json()["items"]]
    assert str(item.id) in ids
