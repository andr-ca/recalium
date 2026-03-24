# 03-05 Summary: MCP Server with retrieve_memory Tool

## Status: DONE

## What Was Implemented

### New Files
- `backend/tests/mcp/__init__.py` — empty init for test package
- `backend/tests/mcp/test_mcp_server.py` — 4 tests covering MCP-01, MCP-03, MCP-04
- `backend/app/mcp_server/__init__.py` — MCP server module init
- `backend/app/mcp_server/server.py` — FastMCP server with `retrieve_memory` tool

### Modified Files
- `backend/app/main.py` — imported `mcp_app`, mounted SSE transport at `/mcp`, added startup log

### MCP Server Details

The `retrieve_memory` tool wraps the retrieval service (03-03) with these parameters:
- `query` (required): search query string
- `mode`: "keyword" | "semantic" | "hybrid" (default: "hybrid")
- `budget`: max character budget (default: 2000)
- `category`, `source_system`, `time_range_start`, `time_range_end`, `canonical_only`: filters
- `actor`: MCP client identity for audit trail (MCP-04)

Audit events are emitted by the underlying `retrieve()` service with `event_type='mcp_retrieve'` (MCP-03).

### Transport

FastMCP `sse_app()` is mounted at `/mcp` in the FastAPI app. The `sse_app()` returns a Starlette ASGI app that handles the SSE protocol. SECURITY: Upstream must bind to 127.0.0.1 only (DNS rebinding prevention, per locked architectural decision).

## Test Results

```
tests/mcp/test_mcp_server.py::test_mcp_app_is_fastmcp_instance PASSED
tests/mcp/test_mcp_server.py::test_retrieve_memory_tool_registered PASSED
tests/mcp/test_mcp_server.py::test_retrieve_memory_tool_has_required_params PASSED
tests/mcp/test_mcp_server.py::test_create_mcp_server_returns_fastmcp PASSED

4 passed in 0.02s
```

## MCP SDK Notes

- `mcp>=1.26` has `FastMCP.sse_app()` returning a Starlette ASGI app — mountable directly.
- `FastMCP._tool_manager.list_tools()` returns tool objects with `.name` and `.parameters` attributes; `.parameters` is a JSON Schema dict.
- No v2 breaking changes encountered — `mcp>=1.26,<2` pin is valid.
