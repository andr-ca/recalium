"""Tests for PRIV-06 authentication middleware.

When APP_BIND_HOST != '127.0.0.1', /api/* endpoints require Authorization: Bearer token.
Run: cd backend && uv run python3 -m pytest tests/api/test_auth_middleware.py -v
"""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch


@pytest.mark.asyncio
async def test_priv06_no_auth_required_for_localhost(client: AsyncClient):
    """PRIV-06: no auth required when bind_host is 127.0.0.1 (default)."""
    resp = await client.get("/api/archive")
    # Should not return 401 (may return 200 or other error)
    assert resp.status_code != 401


@pytest.mark.asyncio
async def test_priv06_auth_required_when_non_localhost():
    """PRIV-06: 401 returned when bind_host != 127.0.0.1 and no Authorization header."""
    import os
    from app.main import create_app
    from app.infrastructure import settings as settings_module

    # Create a test settings object with non-localhost bind host
    original = settings_module._settings
    try:
        # Temporarily override settings
        from app.infrastructure.settings import Settings
        settings_module._settings = Settings(
            database_url=os.environ.get("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x"),
            app_bind_host="0.0.0.0",
            app_auth_bearer="supersecrettoken",
        )
        test_app = create_app()
        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://testserver",
        ) as c:
            resp = await c.get("/api/archive")
            assert resp.status_code == 401
            assert "Authentication required" in resp.json().get("detail", "")
    finally:
        settings_module._settings = original


@pytest.mark.asyncio
async def test_priv06_auth_succeeds_with_correct_token():
    """PRIV-06: 200 returned with correct Bearer token when non-localhost."""
    import os
    from app.main import create_app
    from app.infrastructure import settings as settings_module

    original = settings_module._settings
    try:
        from app.infrastructure.settings import Settings
        settings_module._settings = Settings(
            database_url=os.environ.get("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x"),
            app_bind_host="0.0.0.0",
            app_auth_bearer="supersecrettoken",
        )
        test_app = create_app()
        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://testserver",
        ) as c:
            resp = await c.get(
                "/api/archive",
                headers={"Authorization": "Bearer supersecrettoken"},
            )
            # Should not be 401 (might be 200 or 500 due to DB not available)
            assert resp.status_code != 401
    finally:
        settings_module._settings = original


@pytest.mark.asyncio
async def test_priv06_health_exempt_from_auth():
    """PRIV-06: /health endpoint is always accessible without auth."""
    import os
    from app.main import create_app
    from app.infrastructure import settings as settings_module

    original = settings_module._settings
    try:
        from app.infrastructure.settings import Settings
        settings_module._settings = Settings(
            database_url=os.environ.get("DATABASE_URL", "postgresql+asyncpg://x:x@localhost/x"),
            app_bind_host="0.0.0.0",
            app_auth_bearer="supersecrettoken",
        )
        test_app = create_app()
        async with AsyncClient(
            transport=ASGITransport(app=test_app),
            base_url="http://testserver",
        ) as c:
            resp = await c.get("/health")
            # Health check should never return 401
            assert resp.status_code != 401
    finally:
        settings_module._settings = original
