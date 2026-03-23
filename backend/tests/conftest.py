"""Shared pytest fixtures for backend integration tests.

Strategy: spin up an in-memory SQLite async engine for unit-level tests OR
use a separate test PostgreSQL database for integration tests that require
pg-specific features (pgvector, ENUM types, tsvector).

Phase 1 integration tests use httpx.AsyncClient against a real app instance
backed by a test database (DATABASE_URL from environment, defaulting to a
test-specific DB name to avoid clobbering the dev database).
"""
from __future__ import annotations

import asyncio
import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# ── App import ──────────────────────────────────────────────────────────────
# Must happen AFTER any env overrides so pydantic-settings picks up the test DB
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://recalium:changeme@localhost:5432/recalium_test",
)

# Override DATABASE_URL before importing app so Settings loads the test DB
os.environ.setdefault("DATABASE_URL", TEST_DATABASE_URL)

from app.main import app  # noqa: E402 — must be after env override
from app.infrastructure.db import Base  # noqa: E402


# ── Engine for test DB ───────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop():
    """Single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create all tables in the test database once per session."""
    test_url = os.environ["DATABASE_URL"]
    eng = create_async_engine(test_url, echo=False)
    async with eng.begin() as conn:
        # pgvector extension must exist in the test DB (created by migration)
        await conn.execute(
            __import__("sqlalchemy").text("CREATE EXTENSION IF NOT EXISTS vector")
        )
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
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
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client for testing FastAPI endpoints via ASGI transport."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac
