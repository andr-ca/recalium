# SERVICE-BOUNDARY: mcp_server — v2 extraction point.
# In a multi-service architecture, the MCP server would become a standalone process
# binding to 127.0.0.1 and proxying to the Ingest and Retrieval services.
# Seam: SSE transport; requires auth token for cross-service calls.

"""MCP server module — exposes the Recalium retrieve tool to MCP clients."""
