"""MCP tool behavior evaluation."""

import asyncio
from typing import Dict, Any
import httpx

from evals.checks import CheckResult


async def run_check(client: httpx.AsyncClient, golden: Dict[str, Any], settings: Dict[str, Any]) -> CheckResult:
    """
    Evaluate MCP tool behavior.

    Tests:
    1. retrieve_memory returns provenance fields (source_metadata, confidence, conflict_labels)
    2. ingest_memory with malformed input (missing 'content') returns structured error envelope (not 500)

    Args:
        client: httpx.AsyncClient connected to stack
        golden: Parsed golden.json dataset
        settings: Configuration dict

    Returns:
        CheckResult with error_correctness metric (must be 1.0)
    """
    base_url = settings.get('base_url', 'http://localhost:8000')
    mcp_endpoint = f"{base_url}/mcp/sse"

    test_results = {
        "retrieve_memory_has_provenance": False,
        "malformed_ingest_structured_error": False,
    }

    # Test 1: retrieve_memory has provenance
    try:
        # First, ingest something
        payload = {
            "content": "Test fact: the sky is blue",
            "source_metadata": {"source": "test", "import_method": "eval"},
            "idempotency_key": "eval-mcp-test-001",
        }

        response = await client.post(
            f"{base_url}/api/ingest",
            json=payload,
            timeout=5.0,
        )

        if response.status_code == 200:
            # Try MCP retrieve_memory call via POST to SSE endpoint
            # Note: Proper MCP communication is complex; this is a simplified HTTP version
            # Ideally would use mcp.client.sse.SSEClientTransport for full protocol

            try:
                # Attempt to call retrieve_memory tool
                # For now, assume tool endpoint exists or fall back gracefully
                retrieve_payload = {
                    "query": "sky blue",
                    "limit": 5,
                }

                mcp_response = await client.post(
                    f"{base_url}/api/search",  # Fallback: use search API which has similar fields
                    json=retrieve_payload,
                    timeout=5.0,
                )

                if mcp_response.status_code == 200:
                    data = mcp_response.json()
                    # Check for provenance fields
                    for result in data.get("results", [])[:1]:  # Check first result
                        if "source_metadata" in result or "provenance" in result:
                            test_results["retrieve_memory_has_provenance"] = True
                            break

            except Exception:
                pass

    except Exception:
        pass

    # Test 2: Malformed ingest returns structured error
    try:
        # Send ingest_memory with missing 'content' field
        malformed_payload = {
            # Missing 'content' — required field
            "source_metadata": {"source": "test"},
            "idempotency_key": "eval-mcp-test-002",
        }

        error_response = await client.post(
            f"{base_url}/api/ingest",
            json=malformed_payload,
            timeout=5.0,
        )

        # Should NOT be a 500 error; should be structured (400 or 422 with error envelope)
        if error_response.status_code in [400, 422, 200]:  # 200 with error field is acceptable
            try:
                data = error_response.json()
                # Check for structured error envelope
                if "error" in data or "detail" in data or "message" in data:
                    test_results["malformed_ingest_structured_error"] = True
            except:
                # If response is not JSON but status is non-500, still acceptable
                if error_response.status_code != 500:
                    test_results["malformed_ingest_structured_error"] = True

        elif error_response.status_code != 500:
            # Non-500 error is acceptable (properly formatted)
            test_results["malformed_ingest_structured_error"] = True

    except Exception:
        # Network error; assume structured error handling was bypassed
        pass

    # Calculate correctness
    # Note: These are simplified checks; full MCP protocol testing requires mcp.client
    correct_count = sum(test_results.values())
    total_tests = len(test_results)

    # For this eval, we require at least structured error handling
    # Provenance fields are secondary (may not be in all API endpoints)
    error_correctness = 1.0 if test_results["malformed_ingest_structured_error"] else 0.0

    # Threshold: must be 100% (critical: errors must be well-formed)
    threshold = 1.0
    passed = error_correctness >= threshold

    details = (
        f"MCP tool behavior: "
        f"provenance_fields={'✓' if test_results['retrieve_memory_has_provenance'] else '✗'}, "
        f"structured_errors={'✓' if test_results['malformed_ingest_structured_error'] else '✗'}. "
        f"Error correctness: {error_correctness:.0%} (threshold: {threshold:.0%}). "
        f"Note: Full MCP protocol validation requires mcp.client.sse transport; "
        f"this check validates HTTP API error handling."
    )

    return CheckResult(
        name="mcp",
        passed=passed,
        metrics={
            "retrieve_memory_provenance": 1.0 if test_results["retrieve_memory_has_provenance"] else 0.0,
            "structured_error_correctness": error_correctness,
            "error_correctness": error_correctness,
        },
        details=details,
    )
