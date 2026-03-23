"""Shared pytest fixtures for backend integration tests.

Strategy: use a test PostgreSQL database for integration tests that require
pg-specific features (pgvector, ENUM types, tsvector).

Phase 1 integration tests use httpx.AsyncClient against a real app instance
backed by a test database (DATABASE_URL from environment, defaulting to a
test-specific DB name to avoid clobbering the dev database).

All async fixtures use function scope to avoid asyncio event-loop mismatch
issues with asyncpg (asyncpg connections are bound to the loop in which they
were created; sharing them across loops causes "Future attached to a different
loop" errors).
"""
from __future__ import annotations

import os
from typing import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# ── Test DB URL ──────────────────────────────────────────────────────────────
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://recalium:change_me_in_production@localhost:5435/recalium_test",
)

# Override DATABASE_URL before importing app so Settings loads the test DB
os.environ.setdefault("DATABASE_URL", TEST_DATABASE_URL)

from app.main import app  # noqa: E402 — must be after env override
from app.infrastructure.db import Base  # noqa: E402


# ── Schema bootstrap: run once per session using a sync approach ─────────────
# We use a module-level flag so we only drop/create tables once per process,
# even though the engine fixture is function-scoped.
_schema_created = False


@pytest_asyncio.fixture
async def test_engine():
    """Create a fresh async engine for each test, sharing the current event loop.

    Tables are created only on the first call (session-level schema bootstrap
    using the per-test loop, preventing asyncio loop mismatch).
    """
    global _schema_created
    test_url = os.environ["DATABASE_URL"]
    eng = create_async_engine(test_url, echo=False, pool_size=2, max_overflow=0)

    if not _schema_created:
        async with eng.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        _schema_created = True

    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Per-test async session with automatic rollback after each test."""
    factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client sharing the test DB session for proper rollback isolation."""
    from app.infrastructure.db import get_session

    async def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac
    app.dependency_overrides.clear()
