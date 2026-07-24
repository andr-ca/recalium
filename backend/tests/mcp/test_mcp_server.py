"""MCP server tests — Phase 3.

Covers: MCP-01 (retrieve tool), MCP-03 (audit events), MCP-04 (client identity).
"""
from __future__ import annotations

import uuid

import pytest
pytest.importorskip("app.mcp_server.server")

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.archive.models import RawArchiveItem
from app.mcp_server import server as mcp_server_module
from app.mcp_server.server import (
    get_fact_links,
    ingest_memory,
    list_tags,
    mcp_app,
    create_mcp_server,
    retrieve_memory,
)
from mcp.server.fastmcp import FastMCP


class _BrokenSession:
    """Fake async-context-manager session whose execute() always raises,
    for exercising the internal_error envelope path on an unexpected DB
    failure (as opposed to the expected ValueError/validation paths)."""

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def execute(self, *args, **kwargs):
        raise RuntimeError("db exploded")

    async def commit(self):
        pass

    async def rollback(self):
        pass


def _broken_session_factory():
    return _BrokenSession()


def test_mcp_app_is_fastmcp_instance():
    """MCP-01: mcp_app is a FastMCP instance."""
    assert isinstance(mcp_app, FastMCP)


def test_retrieve_memory_tool_registered():
    """MCP-01: retrieve_memory tool is registered on mcp_app."""
    tools = mcp_app._tool_manager.list_tools()
    tool_names = [t.name for t in tools]
    assert "retrieve_memory" in tool_names


def test_retrieve_memory_tool_has_required_params():
    """MCP-01: retrieve_memory tool has required parameter schema."""
    tools = mcp_app._tool_manager.list_tools()
    tool = next((t for t in tools if t.name == "retrieve_memory"), None)
    assert tool is not None
    # Parameters should include query, mode, budget
    schema = tool.parameters
    props = schema.get("properties", {})
    assert "query" in props
    assert "mode" in props
    assert "budget" in props


def test_ingest_memory_tool_has_v1_metadata_params():
    """MCP-02/MCP-24: ingest_memory exposes the v1 metadata contract fields."""
    tools = mcp_app._tool_manager.list_tools()
    tool = next((t for t in tools if t.name == "ingest_memory"), None)
    assert tool is not None
    props = tool.parameters.get("properties", {})
    for field in [
        "content",
        "source_metadata",
        "client_identity",
        "import_method",
        "idempotency_key",
        "sensitivity_hint",
        "project_hint",
        "processing_mode",
    ]:
        assert field in props


def test_create_mcp_server_returns_fastmcp():
    """MCP-01: create_mcp_server() returns the FastMCP instance."""
    server = create_mcp_server()
    assert isinstance(server, FastMCP)
    assert server is mcp_app  # Same singleton


@pytest.mark.asyncio
async def test_ingest_memory_requires_source_metadata() -> None:
    """MCP-24a: missing source metadata returns a stable validation error envelope."""
    result = await ingest_memory(content="This is long enough to pass content validation.")

    assert result["status"] == "error"
    assert result["error"]["code"] == "validation_error"
    assert result["error"]["details"]["field"] == "source_metadata"
    assert result["error"]["retryable"] is False


@pytest.mark.asyncio
async def test_ingest_memory_requires_content() -> None:
    """MCP-24a: missing content returns a stable validation error envelope."""
    result = await ingest_memory(source_metadata={"source_type": "copilot_chat"})

    assert result["status"] == "error"
    assert result["error"]["code"] == "validation_error"
    assert result["error"]["details"]["field"] == "content"


@pytest.mark.asyncio
async def test_ingest_memory_rejects_invalid_processing_mode() -> None:
    """GPT5.6 #6: an invalid processing_mode is rejected at the boundary."""
    result = await ingest_memory(
        content="This is long enough to pass content validation.",
        source_metadata={"source_type": "copilot_chat"},
        processing_mode="turbo",
    )

    assert result["status"] == "error"
    assert result["error"]["code"] == "validation_error"
    assert result["error"]["details"]["field"] == "processing_mode"


@pytest.mark.asyncio
async def test_ingest_memory_rejects_invalid_sensitivity_hint() -> None:
    """GPT5.6 #6: an invalid sensitivity_hint is rejected at the boundary."""
    result = await ingest_memory(
        content="This is long enough to pass content validation.",
        source_metadata={"source_type": "copilot_chat"},
        sensitivity_hint="ultra",
    )

    assert result["status"] == "error"
    assert result["error"]["code"] == "validation_error"
    assert result["error"]["details"]["field"] == "sensitivity_hint"


@pytest.mark.asyncio
async def test_ingest_memory_accepts_metadata_and_replays_idempotency(
    test_engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """MCP-24: valid metadata is stored and idempotency returns the same archive id."""
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    monkeypatch.setattr(mcp_server_module, "get_session_factory", lambda: factory)
    key = f"test-idempotency-{uuid.uuid4()}"

    first = await ingest_memory(
        content="MCP clients can ingest source-backed memories with metadata.",
        source_metadata={
            "source_type": "copilot_chat",
            "source_name": "copilot-session",
            "conversation_id": "conv-123",
        },
        client_identity="copilot-test-client",
        import_method="mcp_tool",
        idempotency_key=key,
        sensitivity_hint="normal",
        project_hint="recalium",
        processing_mode="deferred",
    )
    replay = await ingest_memory(
        content="MCP clients can ingest source-backed memories with metadata.",
        source_metadata={"source_type": "copilot_chat", "source_name": "copilot-session"},
        client_identity="copilot-test-client",
        import_method="mcp_tool",
        idempotency_key=key,
        sensitivity_hint="normal",
        project_hint="recalium",
        processing_mode="deferred",
    )

    assert first["status"] == "accepted"
    assert replay["status"] == "accepted"
    assert replay["idempotent_replay"] is True
    assert replay["archive_ids"] == first["archive_ids"]

    async with factory() as session:
        archive_id = uuid.UUID(first["archive_ids"][0])
        item = await session.scalar(select(RawArchiveItem).where(RawArchiveItem.id == archive_id))

    assert item is not None
    assert item.source_type == "copilot_chat"
    assert item.source_name == "copilot-session"
    assert item.metadata_json["idempotency_key"] == key
    assert item.metadata_json["client_identity"] == "copilot-test-client"
    assert item.metadata_json["import_method"] == "mcp_tool"


@pytest.mark.asyncio
async def test_retrieve_memory_wraps_unexpected_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """An unexpected (non-ValueError) failure must return the stable error
    envelope, not propagate a raw exception through the MCP transport."""
    monkeypatch.setattr(mcp_server_module, "get_session_factory", lambda: _broken_session_factory)

    result = await retrieve_memory(query="what did we discuss about deployments")

    assert result["status"] == "error"
    assert result["error"]["code"] == "internal_error"
    assert result["error"]["retryable"] is True


@pytest.mark.asyncio
async def test_get_fact_links_wraps_unexpected_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_fact_links had zero exception handling around its DB queries
    (RR-009) — an unexpected failure must return the error envelope."""
    monkeypatch.setattr(mcp_server_module, "get_session_factory", lambda: _broken_session_factory)

    result = await get_fact_links(fact_id=str(uuid.uuid4()))

    assert result["status"] == "error"
    assert result["error"]["code"] == "internal_error"
    assert result["error"]["retryable"] is True


@pytest.mark.asyncio
async def test_list_tags_wraps_unexpected_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """list_tags had zero exception handling (RR-009) — an unexpected
    failure must return the error envelope, not a raw traceback."""
    monkeypatch.setattr(mcp_server_module, "get_session_factory", lambda: _broken_session_factory)

    result = await list_tags()

    assert result["status"] == "error"
    assert result["error"]["code"] == "internal_error"
    assert result["error"]["retryable"] is True
