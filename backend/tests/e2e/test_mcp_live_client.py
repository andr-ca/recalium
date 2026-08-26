"""RR-010: Live MCP client evidence — schemas, invalid inputs, audit, concurrent SSE.

Prerequisites: docker compose up. Run:
  cd backend && uv run pytest tests/e2e/test_mcp_live_client.py -v
"""
from __future__ import annotations

import asyncio
import json as _json
from uuid import uuid4

import httpx
import pytest
from mcp import ClientSession
from mcp.client.sse import sse_client

from tests.e2e.conftest import wait_for

EXPECTED_TOOLS = frozenset({"retrieve_memory", "ingest_memory", "get_fact_links", "list_tags"})


async def _mcp_call(client: httpx.AsyncClient, tool: str, arguments: dict) -> dict:
    base_url = str(client.base_url).rstrip("/")
    mcp_url = f"{base_url}/mcp/sse"
    async with sse_client(mcp_url) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool, arguments)
    assert result.content, f"MCP tool {tool!r} returned empty content"
    raw_text = result.content[0].text
    try:
        return _json.loads(raw_text)
    except (_json.JSONDecodeError, TypeError):
        return {"text": raw_text}


async def _mcp_list_tool_names(client: httpx.AsyncClient) -> set[str]:
    base_url = str(client.base_url).rstrip("/")
    mcp_url = f"{base_url}/mcp/sse"
    async with sse_client(mcp_url) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listed = await session.list_tools()
    return {tool.name for tool in listed.tools}


async def test_mcp_live_tool_catalog(live_client: httpx.AsyncClient) -> None:
    """RR-010: live SSE session exposes all four v1 MCP tools."""
    names = await _mcp_list_tool_names(live_client)
    assert EXPECTED_TOOLS <= names


async def test_mcp_live_retrieve_invalid_mode(live_client: httpx.AsyncClient) -> None:
    """RR-010: invalid retrieve mode returns validation_error envelope (not 500)."""
    result = await _mcp_call(live_client, "retrieve_memory", {"query": "test", "mode": "turbo"})
    assert result["status"] == "error"
    assert result["error"]["code"] == "validation_error"
    assert result["error"]["details"]["field"] == "mode"


async def test_mcp_live_get_fact_links_invalid_uuid(live_client: httpx.AsyncClient) -> None:
    """RR-010: invalid fact_id returns validation_error envelope."""
    result = await _mcp_call(live_client, "get_fact_links", {"fact_id": "not-a-uuid"})
    assert result["status"] == "error"
    assert result["error"]["code"] == "validation_error"
    assert result["error"]["details"]["field"] == "fact_id"


async def test_mcp_live_get_fact_links_invalid_direction(live_client: httpx.AsyncClient) -> None:
    """RR-010: invalid direction returns validation_error envelope."""
    result = await _mcp_call(
        live_client,
        "get_fact_links",
        {"fact_id": str(uuid4()), "direction": "sideways"},
    )
    assert result["status"] == "error"
    assert result["error"]["code"] == "validation_error"
    assert result["error"]["details"]["field"] == "direction"


async def test_mcp_live_retrieve_records_audit_actor(live_client: httpx.AsyncClient) -> None:
    """RR-010: retrieve_memory with custom actor appears in /api/audit/events (MCP-03/04)."""
    actor = f"e2e-rr010-retrieve-{uuid4()}"
    await _mcp_call(
        live_client,
        "retrieve_memory",
        {"query": "recalium memory integration", "mode": "keyword", "actor": actor},
    )

    async def _audit_contains_actor() -> bool:
        resp = await live_client.get(
            "/api/audit/events",
            params={"event_type": "mcp_retrieve", "limit": 100},
        )
        assert resp.status_code == 200
        return any(item.get("actor") == actor for item in resp.json()["items"])

    await wait_for(_audit_contains_actor, timeout=10.0)


async def test_mcp_live_ingest_records_audit_actor(live_client: httpx.AsyncClient) -> None:
    """RR-010: ingest_memory client_identity appears in ingest audit events."""
    tag = uuid4()
    actor = f"e2e-rr010-ingest-{tag}"
    content = f"E2E-{tag} RR010 MCP ingest audit recalium integration"
    result = await _mcp_call(
        live_client,
        "ingest_memory",
        {
            "content": content,
            "source_metadata": {"source_type": "e2e_mcp", "source_name": f"rr010-{tag}"},
            "client_identity": actor,
            "import_method": "mcp_tool",
            "idempotency_key": f"rr010-{tag}",
        },
    )
    assert result.get("status") == "accepted"
    if "archive_ids" in result:
        for aid in result["archive_ids"]:
            live_client.register(aid)

    async def _audit_contains_actor() -> bool:
        resp = await live_client.get(
            "/api/audit/events",
            params={"event_type": "ingest", "limit": 100},
        )
        assert resp.status_code == 200
        return any(item.get("actor") == actor for item in resp.json()["items"])

    await wait_for(_audit_contains_actor, timeout=15.0)


async def test_mcp_live_concurrent_sse_sessions(live_client: httpx.AsyncClient) -> None:
    """RR-010: two concurrent MCP SSE sessions both complete retrieve calls."""

    async def _retrieve(tag: str) -> dict:
        return await _mcp_call(
            live_client,
            "retrieve_memory",
            {"query": f"E2E concurrent {tag} recalium", "mode": "keyword"},
        )

    results = await asyncio.gather(_retrieve("a"), _retrieve("b"))
    assert len(results) == 2
    for result in results:
        assert "items" in result
        assert isinstance(result["items"], list)
