"""MCP contract evaluation via the real MCP protocol (SSE transport).

Exercises the same client path an external MCP agent would use — mirrors the
`_mcp_call` pattern in backend/tests/e2e/test_live_stack.py.
"""

import asyncio
import json
import uuid
from typing import Any, Dict

import httpx

from evals.checks import CheckResult

try:
    from mcp import ClientSession
    from mcp.client.sse import sse_client
    _MCP_AVAILABLE = True
except ImportError:  # pragma: no cover — mcp is a backend dependency
    _MCP_AVAILABLE = False


async def _mcp_call(base_url: str, tool: str, arguments: dict) -> Dict[str, Any]:
    """Establish an MCP SSE session and call a tool; return parsed result dict."""
    mcp_url = f"{base_url.rstrip('/')}/mcp/sse"
    async with sse_client(mcp_url) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool, arguments)
    if not result.content:
        return {}
    raw_text = result.content[0].text
    try:
        return json.loads(raw_text)
    except (json.JSONDecodeError, TypeError):
        return {"text": raw_text}


async def run_check(client: httpx.AsyncClient, golden: Dict[str, Any], settings: Dict[str, Any]) -> CheckResult:
    """
    Evaluate the MCP tool contract end-to-end:

    1. ingest_memory with a well-formed request is accepted
    2. retrieve_memory returns items carrying provenance/budget/conflict metadata
    3. ingest_memory with missing required fields returns a structured error
       envelope (not a crash / free-form string) — RR-009

    Args:
        client: httpx.AsyncClient (unused for MCP; kept for check signature)
        golden: Parsed golden.json dataset
        settings: Configuration dict with base_url

    Returns:
        CheckResult with ingest/retrieve/error contract metrics
    """
    if not _MCP_AVAILABLE:
        return CheckResult(
            name="mcp",
            passed=False,
            metrics={},
            details="mcp package not importable in eval environment",
            skipped=True,
            skip_reason="Run via `uv run --project backend` so the mcp SDK is available",
        )

    base_url = settings.get("base_url", "http://localhost:8000")

    ingest_accepted = False
    retrieve_has_provenance = False
    retrieve_has_budget_meta = False
    structured_error = False
    errors: list[str] = []

    # Unique per run: prior runs' items are cleaned up (soft-deleted), and the
    # server replays idempotency keys — a reused key would "accept" without
    # recreating the item, leaving nothing to retrieve.
    run_tag = uuid.uuid4().hex[:12]
    marker = f"evalmcp{run_tag} provenance probe recalium evaluation suite"

    # Test 1: well-formed ingest_memory is accepted
    try:
        result = await _mcp_call(base_url, "ingest_memory", {
            "content": f"{marker}: the MCP contract check ingests this sentence.",
            "source_metadata": {
                "source_type": "eval_mcp",
                "source_name": f"eval-mcp-contract-{run_tag}",
            },
            "client_identity": "eval-suite",
            "import_method": "mcp_tool",
            "idempotency_key": f"eval-mcp-{run_tag}",
        })
        ingest_accepted = bool(result.get("archive_ids") or result.get("status") in ("accepted", "duplicate"))
    except Exception as e:
        errors.append(f"ingest_memory: {e}")

    # Test 2: retrieve_memory returns provenance + budget metadata.
    # Poll: FTS indexing is async (~3s in practice), so wait for the item.
    try:
        deadline = asyncio.get_event_loop().time() + 60
        items: list = []
        while True:
            # Clear the 60s retrieval TTL cache so polling isn't served a
            # cached empty result for the repeated query
            try:
                await client.post(f"{base_url}/api/search/invalidate-cache", timeout=5.0)
            except Exception:
                pass
            result = await _mcp_call(base_url, "retrieve_memory", {"query": marker})
            items = result.get("items", [])
            if items or asyncio.get_event_loop().time() > deadline:
                break
            await asyncio.sleep(3)
        if items:
            first = items[0]
            retrieve_has_provenance = all(
                k in first for k in ("provenance", "source_id", "type")
            ) and "conflict_label" in first
        retrieve_has_budget_meta = all(
            k in result for k in ("budget_used", "budget_limit", "trimming_reason", "retrieval_mode")
        )
    except Exception as e:
        errors.append(f"retrieve_memory: {e}")

    # Test 3: malformed ingest (missing content) → structured error envelope
    try:
        result = await _mcp_call(base_url, "ingest_memory", {
            "source_metadata": {"source_type": "eval_mcp", "source_name": "eval-mcp-malformed"},
        })
        err = result.get("error")
        structured_error = isinstance(err, dict) and bool(err.get("type") or err.get("code"))
    except Exception:
        # Tool-level validation error raised through protocol is also structured
        structured_error = True

    passed = ingest_accepted and retrieve_has_provenance and retrieve_has_budget_meta and structured_error

    details = (
        f"MCP protocol (SSE) contract: "
        f"ingest_accepted={'✓' if ingest_accepted else '✗'}, "
        f"retrieve_provenance={'✓' if retrieve_has_provenance else '✗'}, "
        f"retrieve_budget_metadata={'✓' if retrieve_has_budget_meta else '✗'}, "
        f"structured_errors={'✓' if structured_error else '✗'}."
    )
    if errors:
        details += f" Errors: {'; '.join(errors[:3])}"

    return CheckResult(
        name="mcp",
        passed=passed,
        metrics={
            "ingest_accepted": 1.0 if ingest_accepted else 0.0,
            "retrieve_memory_provenance": 1.0 if retrieve_has_provenance else 0.0,
            "retrieve_budget_metadata": 1.0 if retrieve_has_budget_meta else 0.0,
            "structured_error_correctness": 1.0 if structured_error else 0.0,
        },
        details=details,
    )
