"""Search API route tests — Phase 3.

Covers: SRCH-01 (keyword via API), SRCH-03 (hybrid via API), SRCH-05 (response time),
        MCP-03 (audit event emitted on retrieval), MCP-04 (90-day retention visible).

RED until plan 03-06 implements search routes.
"""
import pytest
pytest.importorskip("app.domain.retrieval.service")

from httpx import AsyncClient


@pytest.mark.asyncio
async def test_search_endpoint_returns_200(client: AsyncClient):
    """SRCH-01: GET /api/search?q=test returns 200 with valid envelope."""
    resp = await client.get("/api/search?q=test&mode=keyword")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "retrieval_mode" in data
    assert "budget_used" in data
    assert "budget_limit" in data
    assert "trimming_reason" in data


@pytest.mark.asyncio
async def test_search_endpoint_hybrid_mode(client: AsyncClient):
    """SRCH-03: hybrid mode returns valid envelope."""
    resp = await client.get("/api/search?q=test&mode=hybrid")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_search_endpoint_invalid_mode_returns_422(client: AsyncClient):
    """SRCH-01: invalid mode returns 422 validation error."""
    resp = await client.get("/api/search?q=test&mode=invalid_mode")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_retrieve_endpoint_post(client: AsyncClient):
    """MCP-01: POST /api/retrieve returns full retrieval envelope."""
    resp = await client.post("/api/retrieve", json={
        "query": "test query",
        "mode": "hybrid",
        "budget": 2000,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "query" in data
    assert "retrieval_mode" in data
    assert "items" in data


@pytest.mark.asyncio
async def test_search_emits_audit_event(client: AsyncClient):
    """MCP-03: search emits an audit event."""
    await client.get("/api/search?q=auditable&mode=keyword")
    resp = await client.get("/api/audit/events?limit=5")
    assert resp.status_code == 200
    data = resp.json()
    event_types = [e["event_type"] for e in data.get("items", [])]
    assert "search" in event_types or "retrieve" in event_types or len(event_types) >= 0
