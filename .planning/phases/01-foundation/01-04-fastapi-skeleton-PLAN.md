---
wave: 2
depends_on:
  - 01-01-docker-scaffold-PLAN.md
  - 01-02-postgres-schema-PLAN.md
requirements_addressed: [INGT-03, BYOK-05]
files_modified:
  - backend/app/main.py
  - backend/app/api/__init__.py
  - backend/app/api/routes/__init__.py
  - backend/app/api/routes/health.py
  - backend/app/api/routes/ingest.py
  - backend/app/api/routes/archive.py
  - backend/app/api/routes/settings.py
  - backend/app/infrastructure/settings.py
autonomous: true
---

<objective>
Create the FastAPI application factory with lifespan (DB pool init + shutdown), static file serving, API route structure, a health endpoint, and a pydantic-settings config loader. After this plan, `GET /health` returns `{"status":"ok","db":"ok"}` and the app boots cleanly in Docker with correct DB connectivity.

Purpose: The FastAPI skeleton is the integration point that all feature plans (ingest, archive, settings) plug into. The lifespan pattern and DB session dependency must be established here before any route handlers are written.
Output: backend/app/main.py, backend/app/api/routes/{health,ingest,archive,settings}.py, backend/app/infrastructure/settings.py
</objective>

<tasks>

<task id="1" name="Create pydantic-settings config loader and app factory">
  <read_first>
    - backend/app/infrastructure/db.py (from Plan 01-02 — Base, get_engine)
    - .planning/phases/01-foundation/01-CONTEXT.md (D-05 two containers, D-07 production vs dev)
    - .planning/research/STACK.md (pydantic-settings, FastAPI lifespan pattern)
  </read_first>
  <action>
Create `backend/app/infrastructure/settings.py`:

```python
"""Application settings loaded from environment variables via pydantic-settings.

All configuration comes from .env / environment variables.
API keys are NEVER stored here — they are read from environment at validation time only.
"""
from __future__ import annotations

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. All values from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra env vars (e.g. CI variables)
    )

    # Database
    database_url: str
    postgres_user: str = "recalium"
    postgres_password: str = "recalium"
    postgres_db: str = "recalium"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    # Application
    app_env: str = "production"
    log_level: str = "info"
    app_port: int = 8000

    # BYOK keys (optional — empty string means not configured)
    # These are read at runtime for validation only; never persisted to DB.
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    ollama_base_url: str = ""
    ollama_api_key: str = ""

    @field_validator("app_env")
    @classmethod
    def validate_app_env(cls, v: str) -> str:
        if v not in ("development", "production"):
            raise ValueError(f"app_env must be 'development' or 'production', got: {v!r}")
        return v

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return the singleton Settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
```

Create `backend/app/main.py` (FastAPI app factory with lifespan):

```python
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
from app.infrastructure.db import get_engine, get_session_factory
from app.infrastructure.settings import get_settings

logger = logging.getLogger(__name__)


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
    from sqlalchemy import inspect as sa_inspect
    from app.infrastructure.db import Base

    # Force all model imports so metadata is populated
    import app.domain.archive.models  # noqa: F401
    import app.domain.settings.models  # noqa: F401
    import app.domain.jobs.models  # noqa: F401
    import app.domain.audit.models  # noqa: F401

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

    logger.info("DB pool initialized. Application ready.")
    yield

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
```

Create `backend/app/api/__init__.py`:

```python
"""API layer — thin route handlers, no business logic."""
```

Create `backend/app/api/routes/__init__.py` (aggregate router):

```python
"""All API routes registered here."""
from fastapi import APIRouter
from app.api.routes.health import router as health_router
from app.api.routes.ingest import router as ingest_router
from app.api.routes.archive import router as archive_router
from app.api.routes.settings import router as settings_router

router = APIRouter()
router.include_router(health_router, tags=["health"])
router.include_router(ingest_router, prefix="/ingest", tags=["ingest"])
router.include_router(archive_router, prefix="/archive", tags=["archive"])
router.include_router(settings_router, prefix="/settings", tags=["settings"])
```
  </action>
  <acceptance_criteria>
    - `grep -n "class Settings" backend/app/infrastructure/settings.py` returns 1 line
    - `grep -n "openai_api_key.*str.*= \"\"" backend/app/infrastructure/settings.py` returns 1 line
    - `grep -n "_assert_no_keys_in_schema" backend/app/main.py` returns ≥ 2 lines (def + call)
    - `grep -n "lifespan" backend/app/main.py` returns ≥ 3 lines (import, decorator, param)
    - `grep -n "StaticFiles" backend/app/main.py` returns ≥ 2 lines
    - `grep -n "include_router" backend/app/api/routes/__init__.py | wc -l` returns 4 (health, ingest, archive, settings)
    - `grep -n "SECURITY VIOLATION" backend/app/main.py` returns 1 line
  </acceptance_criteria>
</task>

<task id="2" name="Create health endpoint and route stubs for ingest, archive, settings">
  <read_first>
    - backend/app/infrastructure/db.py (get_session dependency)
    - backend/app/api/routes/__init__.py (from previous task)
  </read_first>
  <action>
Create `backend/app/api/routes/health.py`:

```python
"""Health check endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db import get_session

router = APIRouter()


@router.get("/health")
async def health_check(session: AsyncSession = Depends(get_session)) -> dict:
    """Health check: verifies app is running and DB is reachable.

    Returns:
        {"status": "ok", "db": "ok"} on success
        {"status": "degraded", "db": "error", "detail": "..."} if DB unreachable
    """
    try:
        await session.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        return {"status": "degraded", "db": "error", "detail": str(e)}
    return {"status": "ok", "db": db_status}
```

Create `backend/app/api/routes/ingest.py` (stub — implementation in Plan 01-05):

```python
"""Ingest route stubs — implementation in Plan 01-05."""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.post("")
async def ingest_text() -> dict:
    """POST /api/ingest — accepts text paste or JSON file upload.
    Stub: returns 501 until Plan 01-05 implementation.
    """
    return {"error": "Not yet implemented — see Plan 01-05"}


@router.post("/file")
async def ingest_file() -> dict:
    """POST /api/ingest/file — accepts file upload.
    Stub: returns 501 until Plan 01-05 implementation.
    """
    return {"error": "Not yet implemented — see Plan 01-05"}
```

Create `backend/app/api/routes/archive.py` (stub — implementation in Plan 01-06):

```python
"""Archive route stubs — implementation in Plan 01-06."""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def list_archive() -> dict:
    """GET /api/archive — returns paginated raw archive items.
    Stub: returns empty list until Plan 01-06 implementation.
    """
    return {"items": [], "total": 0, "offset": 0, "limit": 50}
```

Create `backend/app/api/routes/settings.py` (stub — implementation in Plan 01-07):

```python
"""Settings / BYOK route stubs — implementation in Plan 01-07."""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/keys")
async def get_keys() -> dict:
    """GET /api/settings/keys — returns key configuration status (no plaintext keys).
    Stub: returns unconfigured state until Plan 01-07 implementation.
    """
    unconfigured = {"configured": False, "fingerprint": None, "validation_status": "unchecked", "validated_at": None}
    return {
        "openai": unconfigured,
        "anthropic": unconfigured,
        "ollama": {**unconfigured, "base_url": None},
    }


@router.post("/keys/validate")
async def validate_key() -> dict:
    """POST /api/settings/keys/validate — validates a provider API key.
    Stub: returns error until Plan 01-07 implementation.
    """
    return {"error": "Not yet implemented — see Plan 01-07"}
```

Create stub domain module directories (must exist so `_assert_no_keys_in_schema` imports succeed):

For each of these paths, create an empty `__init__.py` and a `models.py` with just the Base import:
- `backend/app/domain/__init__.py`
- `backend/app/domain/archive/__init__.py`
- `backend/app/domain/archive/models.py`
- `backend/app/domain/settings/__init__.py`
- `backend/app/domain/settings/models.py`
- `backend/app/domain/jobs/__init__.py`
- `backend/app/domain/jobs/models.py`
- `backend/app/domain/audit/__init__.py`
- `backend/app/domain/audit/models.py`

Each `models.py` should contain:
```python
"""Domain models — ORM models defined in Plan 01-05/01-06/01-07."""
# Models will be added when the domain plans are implemented.
# This stub ensures the startup assertion import succeeds.
```
  </action>
  <acceptance_criteria>
    - `grep -n "SELECT 1" backend/app/api/routes/health.py` returns 1 line
    - `grep -n "status.*ok.*db.*ok" backend/app/api/routes/health.py` returns 1 line
    - `grep -n "degraded" backend/app/api/routes/health.py` returns 1 line (error case)
    - `grep -n "@router.post" backend/app/api/routes/ingest.py | wc -l` returns 2 (text + file)
    - `grep -n "@router.get" backend/app/api/routes/archive.py` returns 1 line
    - `grep -n "@router.get\|@router.post" backend/app/api/routes/settings.py | wc -l` returns 2
    - All domain model stubs exist: `ls backend/app/domain/archive/models.py backend/app/domain/settings/models.py backend/app/domain/jobs/models.py backend/app/domain/audit/models.py` — all 4 files exist
  </acceptance_criteria>
</task>

</tasks>

<verification>
After all tasks complete:

1. Via Docker (depends on Plan 01-01 + 01-02):
   ```
   docker compose up -d
   curl -s http://localhost:8000/api/health | python3 -m json.tool
   ```
   Expected response: `{"status": "ok", "db": "ok"}`

2. Check startup assertion runs:
   ```
   docker compose logs recalium-app | grep "Startup assertion passed"
   ```
   Must return 1 line.

3. Check API docs (development mode):
   ```
   curl -s http://localhost:8000/api/docs
   ```
   Should return HTML (swagger UI) if APP_ENV=development.

4. Direct Python check (inside container):
   ```
   docker compose exec recalium-app python3 -c "from app.main import create_app; app = create_app(); print('App created OK')"
   ```
   Must print "App created OK" without errors.
</verification>

<must_haves>
1. `GET /api/health` returns `{"status":"ok","db":"ok"}` with a live DB connection. Verified by curl after `docker compose up`.
2. `_assert_no_keys_in_schema()` runs at startup and raises `RuntimeError` if any column named `*_key` (without `_fingerprint`/`_configured` exception) exists in any ORM model. Verified: `grep "SECURITY VIOLATION" backend/app/main.py` returns 1 line.
3. FastAPI app uses `lifespan` context manager (not deprecated `on_event`). Verified: `grep "on_event\|startup_event" backend/app/main.py` returns 0 lines.
</must_haves>
