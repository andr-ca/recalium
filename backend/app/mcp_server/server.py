"""MCP server for Recalium.

Exposes a single `retrieve_memory` tool for MCP clients (AI agents).
All access events are recorded in the audit_events table (MCP-03, MCP-04).

SECURITY: Server must be bound to 127.0.0.1 only (locked architectural decision —
DNS rebinding attack prevention). This is enforced at the uvicorn/Docker level.

MCP-01: retrieve_memory tool
MCP-03: access event audit (event_type='mcp_retrieve')
MCP-04: client identity recorded in actor field
"""
from __future__ import annotations

import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from app.domain.retrieval.service import (
    RetrievalFilters,
    RetrievalRequest,
    retrieve,
)
from app.infrastructure.db import get_session_factory

logger = logging.getLogger(__name__)

# MCP app instance — exported so main.py can mount it
mcp_app = FastMCP("recalium")


@mcp_app.tool()
async def retrieve_memory(
    query: str,
    mode: str = "hybrid",
    budget: int = 2000,
    category: str | None = None,
    source_system: str | None = None,
    time_range_start: str | None = None,
    time_range_end: str | None = None,
    canonical_only: bool = False,
    actor: str = "mcp_client",
) -> dict[str, Any]:
    """Retrieve relevant memory items from the Recalium archive.

    Args:
        query: The search query string.
        mode: Retrieval mode — "keyword", "semantic", or "hybrid" (default: "hybrid").
        budget: Maximum character budget for returned content (default: 2000).
        category: Optional category filter.
        source_system: Optional source system filter (e.g. "chatgpt", "claude").
        time_range_start: Optional ISO 8601 datetime lower bound for captured_at.
        time_range_end: Optional ISO 8601 datetime upper bound for captured_at.
        canonical_only: If true, return only canonical memory items.
        actor: MCP client identity string (for audit trail — MCP-04).

    Returns:
        Retrieval envelope with items, scores, provenance, and context budget metadata.
    """
    filters = RetrievalFilters(
        category=category,
        source_system=source_system,
        time_range_start=time_range_start,
        time_range_end=time_range_end,
        canonical_only=canonical_only,
    )
    req = RetrievalRequest(
        query=query,
        mode=mode,
        budget=budget,
        filters=filters,
        actor=actor,
    )

    factory = get_session_factory()
    async with factory() as session:
        response = await retrieve(session, req)

    return {
        "query": response.query,
        "retrieval_mode": response.retrieval_mode,
        "budget_used": response.budget_used,
        "budget_limit": response.budget_limit,
        "trimming_reason": response.trimming_reason,
        "degraded_mode": response.degraded_mode,
        "items": [
            {
                "id": item.id,
                "type": item.type,
                "content": item.content,
                "score": item.score,
                "source_id": item.source_id,
                "source_system": item.source_system,
                "captured_at": item.captured_at,
                "conflict_label": item.conflict_label,
                "provenance": item.provenance,
            }
            for item in response.items
        ],
    }


@mcp_app.tool()
async def ingest_memory(
    content: str = "",
    source_name: str | None = None,
    source_type: str = "mcp_ingest",
    actor: str = "mcp_client",
) -> dict[str, Any]:
    """Ingest raw content into the Recalium memory archive via MCP.

    Args:
        content: The raw text content to ingest (required, minimum 10 characters).
        source_name: Optional label for the source (e.g. "claude-session-2026-03-24").
        source_type: Source type label (default: "mcp_ingest").
        actor: MCP client identity string for audit trail (default: "mcp_client").

    Returns:
        On success: {"status": "accepted", "item_count": N, "archive_ids": [...]}
        On error: {"error": "<descriptive message>"}
    """
    # MCP-02: validate required fields and return descriptive errors
    if not content or not content.strip():
        return {"error": "content is required and must be non-empty"}
    if len(content.strip()) < 10:
        return {"error": "content too short (minimum 10 characters)"}

    from app.domain.ingest.service import ingest_text_content  # noqa: PLC0415

    factory = get_session_factory()
    async with factory() as session:
        try:
            result = await ingest_text_content(
                session=session,
                content=content,
                source_name=source_name,
                actor=actor,
            )
            await session.commit()
        except ValueError as exc:
            return {"error": str(exc)}
        except Exception as exc:
            logger.error("MCP ingest_memory failed: %s", exc)
            return {"error": f"Ingest failed: {exc}"}

    return {
        "status": "accepted",
        "item_count": result.item_count,
        "archive_ids": [str(aid) for aid in result.archive_ids],
    }


def create_mcp_server() -> FastMCP:
    """Return the configured MCP app instance.

    Used by main.py lifespan and by tests.
    SECURITY: Caller must bind to 127.0.0.1 only when using HTTP transport.
    """
    return mcp_app
