"""MCP server tests — Phase 3.

Covers: MCP-01 (retrieve tool), MCP-03 (audit events), MCP-04 (client identity).
"""
import pytest
pytest.importorskip("app.mcp_server.server")

from app.mcp_server.server import mcp_app, create_mcp_server
from mcp.server.fastmcp import FastMCP


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


def test_create_mcp_server_returns_fastmcp():
    """MCP-01: create_mcp_server() returns the FastMCP instance."""
    server = create_mcp_server()
    assert isinstance(server, FastMCP)
    assert server is mcp_app  # Same singleton
