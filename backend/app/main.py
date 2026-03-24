"""Recalium FastAPI application.

Entrypoint for the ASGI server. Contains:
- App factory with lifespan (DB engine init, startup assertion, shutdown)
- Static file serving for the React frontend build
- API router registration
"""
from __future__ import annotations

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import router as api_router
from app.api.routes.search import router as search_router
from app.api.routes.canonical import router as canonical_router
from app.api.routes.review_queue import router as review_queue_router
from app.api.routes.audit import router as audit_router
from app.infrastructure.db import get_engine, get_session_factory
from app.infrastructure.settings import get_settings
from app.mcp_server.server import create_mcp_server, mcp_app as _mcp_app

logger = logging.getLogger(__name__)

# Basic logging setup — will be reconfigured in lifespan with proper level from settings
logging.basicConfig(level=logging.INFO, format="%(levelname)s [%(name)s] %(message)s")


def _assert_no_keys_in_schema() -> None:
    """Startup assertion: scan all column names for plaintext key patterns.

    Fails loudly if any ORM model has a column named with a key/secret/token suffix
    that could hold a full API key. This enforces the BYOK contract (D-12, Pitfall 5).

    Allowed exceptions:
    - Columns ending in _fingerprint (stores last 4 chars only)
    - Columns ending in _configured (boolean flag)
    - Columns ending in _validation_status (string status)
    - Columns ending in _validated_at (timestamp)
    """
    from app.infrastructure.db import Base

    # Force all model imports so metadata is populated
    import app.domain.archive.models  # noqa: F401
    import app.domain.settings.models  # noqa: F401
    import app.domain.jobs.models  # noqa: F401
    import app.domain.audit.models  # noqa: F401
    import app.domain.derived_memory.models  # noqa: F401
    import app.domain.canonical_memory.models  # noqa: F401
    import app.domain.review_queue.models  # noqa: F401

    forbidden_suffixes = ("_key", "_secret", "_token", "_password")
    allowed_suffixes = ("_fingerprint", "_configured", "_validation_status", "_validated_at")

    violations: list[str] = []
    for table in Base.metadata.tables.values():
        for column in table.columns:
            col_name = column.name.lower()
            for forbidden in forbidden_suffixes:
                if col_name.endswith(forbidden):
                    # Check if it's an allowed exception
                    if not any(col_name.endswith(allowed) for allowed in allowed_suffixes):
                        violations.append(f"{table.name}.{column.name}")

    if violations:
        raise RuntimeError(
            f"SECURITY VIOLATION: Columns that may store plaintext API keys found in schema: "
            f"{violations}. "
            "Keys must live in .env only. DB stores only fingerprints and booleans."
        )

    logger.info("Startup assertion passed: no plaintext key columns in schema.")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """FastAPI lifespan: initialize DB pool on startup, close on shutdown."""
    settings = get_settings()
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(level=log_level, format="%(levelname)s [%(name)s] %(message)s")

    logger.info(f"Starting Recalium in {settings.app_env} mode")

    # Initialize DB connection pool
    engine = get_engine()
    get_session_factory()  # Warm up session factory

    # Startup assertion: no plaintext key columns in schema
    _assert_no_keys_in_schema()

    # Start pipeline worker task
    import asyncio as _asyncio
    from app.worker.loop import worker_loop
    _worker_task = _asyncio.create_task(worker_loop(), name="pipeline-worker")
    logger.info("Pipeline worker task started")

    logger.info("DB pool initialized. Application ready.")
    logger.info("MCP retrieve_memory tool registered (SSE transport on /mcp/sse)")
    yield

    # Shutdown pipeline worker cleanly
    _worker_task.cancel()
    try:
        await _worker_task
    except _asyncio.CancelledError:
        pass
    logger.info("Pipeline worker task stopped")

    # Shutdown: dispose DB connection pool
    await engine.dispose()
    logger.info("DB pool disposed. Application shutdown complete.")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Recalium API",
        description="Local-first MCP-native personal memory platform",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/api/docs" if settings.is_development else None,
        redoc_url="/api/redoc" if settings.is_development else None,
    )

    # API routes under /api prefix
    app.include_router(api_router, prefix="/api")

    # Phase 3 routes (have their own /api prefix)
    app.include_router(search_router)
    app.include_router(canonical_router)
    app.include_router(review_queue_router)
    app.include_router(audit_router)

    # MCP SSE transport — bound to /mcp prefix.
    # SECURITY: Upstream proxy/uvicorn must bind to 127.0.0.1 only (DNS rebinding prevention).
    app.mount("/mcp", _mcp_app.sse_app())

    # Serve React SPA static files (built frontend)
    # In development, Vite dev server handles static; in production, serve from dist.
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    if os.path.isdir(static_dir):
        # Mount at / so React Router handles client-side routing
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
        logger.info(f"Serving static files from {static_dir}")
    else:
        logger.info("No static/ directory found — assuming Vite dev server in use.")

    return app


# ASGI application instance (used by uvicorn)
app = create_app()
