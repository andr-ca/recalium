"""Fixtures for live-stack E2E integration tests.

Prerequisites: `docker compose up` (or `make up`) must be running.
Set BASE_URL env var to override target (default: http://localhost:8000).
"""
from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncGenerator, Callable

import httpx
import pytest
import pytest_asyncio


@pytest.fixture(scope="session")
def base_url() -> str:
    """Base URL of the live stack. Reads BASE_URL env var, defaults to localhost:8000."""
    return os.environ.get("BASE_URL", "http://localhost:8000")


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def stack_health(base_url: str) -> None:
    """Session-scoped fixture that skips all tests if the stack is unreachable.

    Calls GET /api/health. Skips with a clear message if the stack is not up.
    """
    async with httpx.AsyncClient(base_url=base_url, timeout=5.0) as client:
        try:
            resp = await client.get("/api/health")
            if resp.status_code != 200:
                pytest.skip(
                    f"Stack at {base_url} returned HTTP {resp.status_code} — "
                    "start it with `docker compose up` before running E2E tests."
                )
        except httpx.ConnectError:
            pytest.skip(
                f"Stack at {base_url} is unreachable — "
                "start it with `docker compose up` before running E2E tests."
            )


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def cleanup_registry(base_url: str, stack_health: None) -> AsyncGenerator[list[str], None]:
    """Session-scoped list of archive item IDs to delete after all tests finish.

    Acts as a safety net — individual tests also clean up inline where needed.
    Session teardown sweeps the full list via DELETE /api/archive/{id}.
    """
    registry: list[str] = []
    yield registry
    # Sweep: delete all registered IDs
    async with httpx.AsyncClient(base_url=base_url, timeout=10.0) as client:
        for item_id in registry:
            try:
                await client.delete(f"/api/archive/{item_id}")
            except Exception:
                pass  # Best-effort cleanup; don't fail teardown


@pytest_asyncio.fixture
async def live_client(
    base_url: str,
    cleanup_registry: list[str],
    stack_health: None,
) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Function-scoped httpx.AsyncClient pointed at the live stack.

    Adds a `register(item_id)` method to the client for tracking created items.
    """
    async with httpx.AsyncClient(base_url=base_url, timeout=15.0) as client:
        def register(item_id: str) -> None:
            cleanup_registry.append(item_id)
        client.register = register  # type: ignore[attr-defined]
        yield client


async def wait_for(
    async_fn: Callable,
    timeout: float = 15.0,
    interval: float = 0.5,
):
    """Poll async_fn until it returns a truthy value or timeout is reached.

    On timeout, calls pytest.fail with a descriptive message.
    """
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while True:
        result = await async_fn()
        if result:
            return result
        if loop.time() > deadline:
            pytest.fail(f"Timed out after {timeout}s waiting for condition")
        await asyncio.sleep(interval)
