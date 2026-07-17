"""SPA fallback contract (GPT5.6 #7 remainder).

The static mount serves index.html for client-side UI deep links, but unknown
backend routes (``/api/*`` and ``/mcp/*``) must return an honest JSON 404 instead
of a 200 HTML SPA shell.
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.main import SPAStaticFiles


@pytest.fixture
def spa_app(tmp_path):
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    (static_dir / "index.html").write_text("<!doctype html><title>SPA</title>")
    (static_dir / "asset.js").write_text("console.log('ok')")

    app = FastAPI()

    @app.get("/api/real")
    async def _real():  # pragma: no cover - trivial
        return {"ok": True}

    app.mount("/", SPAStaticFiles(directory=str(static_dir), html=True), name="static")
    return app


@pytest.mark.asyncio
async def test_ui_deep_link_returns_spa_shell(spa_app):
    async with AsyncClient(
        transport=ASGITransport(app=spa_app), base_url="http://testserver"
    ) as ac:
        resp = await ac.get("/facts")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "SPA" in resp.text


@pytest.mark.asyncio
async def test_static_asset_is_served(spa_app):
    async with AsyncClient(
        transport=ASGITransport(app=spa_app), base_url="http://testserver"
    ) as ac:
        resp = await ac.get("/asset.js")
    assert resp.status_code == 200
    assert "console.log" in resp.text


@pytest.mark.asyncio
async def test_registered_api_route_still_works(spa_app):
    async with AsyncClient(
        transport=ASGITransport(app=spa_app), base_url="http://testserver"
    ) as ac:
        resp = await ac.get("/api/real")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


@pytest.mark.asyncio
async def test_unknown_api_route_returns_json_404(spa_app):
    async with AsyncClient(
        transport=ASGITransport(app=spa_app), base_url="http://testserver"
    ) as ac:
        resp = await ac.get("/api/definitely-missing")
    assert resp.status_code == 404
    assert resp.headers["content-type"].startswith("application/json")
    assert resp.json()["detail"] == "Not Found"


@pytest.mark.asyncio
async def test_unknown_mcp_route_returns_json_404(spa_app):
    async with AsyncClient(
        transport=ASGITransport(app=spa_app), base_url="http://testserver"
    ) as ac:
        resp = await ac.get("/mcp/bogus-endpoint")
    assert resp.status_code == 404
    assert resp.headers["content-type"].startswith("application/json")
