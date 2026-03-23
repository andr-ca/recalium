# Phase 1: Foundation — Research

**Researched:** 2026-03-22
**Domain:** FastAPI + PostgreSQL + React monorepo bootstrap; BYOK key storage; Docker Compose bind mounts; Alembic async migrations
**Confidence:** HIGH (stack versions verified live; architecture patterns from official docs)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01:** Monorepo with `backend/` and `frontend/` at repo root. Docker build context is repo root.

**D-02:** Backend: `backend/app/` with `domain/` (subdirs: `ingest/`, `archive/`, `policy/`, `audit/`, `jobs/`), `api/`, `worker/`, `infrastructure/`. Follows `component-boundaries.md` exactly.

**D-03:** Frontend: `frontend/src/` with `components/`, `pages/`, `hooks/`, `lib/`. Standard Vite + shadcn/ui layout.

**D-04:** `uv` for Python (`pyproject.toml` at `backend/`); `pnpm` for Node (`package.json` at `frontend/`).

**D-05:** Two containers: `recalium-app` and `recalium-postgres`. No additional containers in v1.

**D-06:** Bind-mount paths (not named volumes): `./data/postgres:/var/lib/postgresql/data`, `./backups:/app/backups`, `./import:/app/import`. Paths are `.gitignore`d.

**D-07:** Single `docker-compose.yml` (production base); `docker-compose.override.yml` (dev: hot-reload, exposed DB port). Production uses base only.

**D-08:** Container entrypoint runs `alembic upgrade head` before starting Uvicorn. pgvector extension created in migration `0001_initial.py`.

**D-09:** Every derived table includes `source_status ENUM('active', 'source_removed') NOT NULL DEFAULT 'active'` from day one.

**D-10:** Raw archive soft-delete: `deleted_at TIMESTAMP WITH TIME ZONE NULL`. Hard deletion ships Phase 4.

**D-11:** `pgvector` extension enabled in migration 001; embedding columns added in Phase 2.

**D-12:** API keys in `.env` only. DB stores fingerprint (last 4 chars) and `{provider}_key_configured: boolean`. Plaintext keys never in DB. Startup assertion scans schema.

**D-13:** BYOK Settings UI: one section per provider (OpenAI, Anthropic, Ollama); masked input + Validate button + inline status badge (✓ Valid / ✗ Invalid / ⚠ Insufficient permissions). Validation is lightweight test call before persisting fingerprint.

**D-14:** Ollama takes URL + optional key. OpenAI and Anthropic take only API key.

**D-15:** Single Ingest page, two tabs: "Paste" (textarea) and "File Upload" (drag-and-drop + file browser, accepts `.json`, `.txt`, `.md`). Both submit to same backend endpoint.

**D-16:** On success, toast ("N conversations ingested"), navigate to Archive. No polling in Phase 1.

**D-17:** Archive page: card list with source name, ingested-at timestamp, item count, status badge ("Ingested" only in Phase 1).

**D-18:** Supported formats: plain text/Markdown (paste), ChatGPT JSON export, Claude JSON export, generic JSON.

**D-19:** Left-nav order: Ingest, Archive, Facts (disabled), Canonical (disabled), Search (disabled), Review Queue (disabled), Audit (disabled), Settings. Disabled items visible, grayed, tooltip "Available in a future update."

**D-20:** Chrome/Chromium only in v1. No polyfills.

**D-21:** No authentication in v1.

### Agent's Discretion

- Specific shadcn/ui component choices for left-nav, card list, form elements.
- Loading/empty state designs for Archive and Ingest pages.
- Exact Alembic migration numbering and file naming convention.
- Whether Vite dev server proxies API calls or uses a separate dev port (standard Vite proxy is fine).

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INGT-01 | User can import conversations via text paste (plain text / Markdown) | FastAPI file/form upload patterns; ingest service design |
| INGT-02 | User can import conversations via file upload (ChatGPT JSON, Claude JSON, generic JSON) | ChatGPT/Claude JSON export structure documented below; format detection algorithm |
| INGT-03 | System stores raw archive with source metadata; item in Archive UI within P95 ≤ 1s | SQLAlchemy async session; DB schema; API response pattern |
| BKUP-04 | No acknowledged raw archive item lost after container restart or host reboot | Bind-mount Docker Compose pattern; PostgreSQL data durability |
| WEBUI-01 | Left-nav layout: Ingest, Archive, Facts, Canonical, Search, Review Queue, Audit, Settings | shadcn/ui sidebar component; React Router; disabled nav items |
| WEBUI-04 | Chrome/Chromium only in v1 | No polyfills required; modern CSS/JS features permitted |
| BYOK-02 | User can configure OpenAI, Anthropic, and Ollama endpoint API keys through settings | BYOK settings page design; env-file-only key storage |
| BYOK-03 | Key validation runs at configuration time with lightweight test call | Per-provider validation endpoints documented below |
| BYOK-04 | Provider-backed processing uses only user's configured keys; no Recalium-operated services | env-only key storage; no DB key columns |
| BYOK-05 | System remains usable for ingestion, local storage, browsing, and keyword search without keys | degraded-mode design; no hard dependency on BYOK at startup |
</phase_requirements>

---

## Summary

Phase 1 is a greenfield monorepo bootstrap. Everything is new — no application code exists yet. The primary complexity centres on three areas: (1) correctly wiring FastAPI's async lifecycle with SQLAlchemy 2.x async sessions and an Alembic auto-upgrade-on-startup pattern, (2) the BYOK key storage model that enforces API keys never reach the database, and (3) the Docker Compose bind-mount topology that ensures data survives `docker compose down`.

The React 19 + Vite 8 + Tailwind v4 + shadcn/ui 2.x frontend is a standard shadcn init workflow with one important constraint: Tailwind v4 uses CSS-first configuration (no `tailwind.config.js`). shadcn/ui 2.x CLI handles this automatically when run after Tailwind v4 installation.

**Critical discrepancy to resolve:** `docs/architecture/tech-stack.md` says "React 18" but `STATE.md` (updated later, post-research) and `STACK.md` (live-verified 2026-03-22) both say React 19. The live-verified STACK.md is the authoritative source. React 19 is the correct target. `tech-stack.md` contains a stale reference that can be corrected as part of Phase 1 scaffolding.

**Primary recommendation:** Scaffold backend first (DB + migrations + FastAPI lifespan + health endpoint), verify `alembic upgrade head` runs cleanly in the container, then add ingest domain and frontend in parallel.

---

## Standard Stack

### Core (confirmed live 2026-03-22 via STACK.md)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | `3.12+` | Runtime | Required by sentence-transformers 5.x; 3.13 free-threaded GIL experimental |
| FastAPI | `0.135.1` | ASGI framework + static serving | Async-native, Pydantic v2, auto OpenAPI |
| Uvicorn | `0.42.0` | ASGI server | Standard FastAPI pairing; `uvicorn[standard]` for WS + HTTP/2 |
| PostgreSQL | `16+` | Primary store + FTS + job queue | tsvector/tsquery, pgvector, SKIP LOCKED |
| pgvector | `0.8.2` | Vector extension | HNSW parallel build buffer-overflow fix in 0.8.2 |
| SQLAlchemy | `2.0.48` | Async ORM | 2.x async-native with asyncpg; `mapped_column` declarative |
| asyncpg | `0.31.0` | Async PG driver | Fastest async Python PG driver |
| Alembic | `1.18.4` | DB migrations | Standard SQLAlchemy migration tool |
| Pydantic | `2.12.5` | Validation + settings | v2, 5-50x faster than v1 |
| pydantic-settings | `2.x` | `.env` loading | Typed settings from env files |
| httpx | `0.28.1` | Async HTTP client | BYOK validation calls; FastAPI test client |
| React | `19.2.4` | UI framework | Current stable; shadcn/ui 2.x targets React 19 |
| TypeScript | `5.x` | Type safety | Required by shadcn/ui and React ecosystem |
| Vite | `8.0.1` | Build tool | Requires Node `^20.19.0 \|\| >=22.12.0` |
| Tailwind CSS | `4.x` | Styling | CSS-first config; shadcn/ui 2.x built for Tailwind v4 |
| shadcn/ui | `2.x` | Component library | Copied components; React 19 + Tailwind v4 confirmed |
| uv | `0.10.12` | Python pkg manager | 10-100x faster than pip; production-ready |
| pnpm | `10.32.1` | Node pkg manager | v10 stable; v11 is beta with breaking changes |

### Supporting (Phase 1 only)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | `8.x` | Test runner | All backend tests |
| pytest-asyncio | `1.3.0` | Async test support | FastAPI async endpoint tests |
| Vitest | `3.x` | Frontend unit tests | React component tests |
| React Testing Library | `16.x` | Component test utilities | Behavior-focused tests |

### Node Version Requirement

**⚠ CRITICAL:** Vite 8 requires `Node.js ^20.19.0 || >=22.12.0`. Node 18 and Node 20.0–20.18 are dropped. Verify with `node --version` before scaffolding frontend.

---

## Architecture Patterns

### Recommended Project Structure

```
recalium/                          ← repo root (Docker build context)
├── backend/
│   ├── pyproject.toml             ← uv-managed Python project
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py                 ← async-compatible env
│   │   └── versions/
│   │       └── 0001_initial.py   ← pgvector + core tables
│   ├── app/
│   │   ├── main.py               ← FastAPI app factory + lifespan
│   │   ├── domain/
│   │   │   ├── ingest/           ← validate, normalize, persist, enqueue
│   │   │   ├── archive/          ← raw item storage + fetch
│   │   │   ├── policy/           ← sensitivity gate seams (Phase 1: passthrough)
│   │   │   ├── audit/            ← event emission
│   │   │   └── jobs/             ← job enqueue/dequeue (Phase 1: stub)
│   │   ├── api/
│   │   │   └── routes/
│   │   │       ├── ingest.py     ← POST /api/ingest
│   │   │       ├── archive.py    ← GET /api/archive
│   │   │       └── byok.py       ← GET/POST /api/settings/byok
│   │   ├── worker/               ← asyncio task loop (Phase 1: stub)
│   │   └── infrastructure/
│   │       ├── db.py             ← async engine + session factory
│   │       └── settings.py      ← pydantic-settings + .env loading
│   └── tests/
│       ├── conftest.py
│       ├── test_ingest.py
│       ├── test_archive.py
│       └── test_byok.py
├── frontend/
│   ├── package.json              ← pnpm-managed
│   ├── vite.config.ts
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── ui/               ← shadcn/ui copied components
│   │   │   └── nav/              ← left-nav shell
│   │   ├── pages/
│   │   │   ├── IngestPage.tsx
│   │   │   ├── ArchivePage.tsx
│   │   │   └── SettingsPage.tsx
│   │   ├── hooks/
│   │   └── lib/
│   │       └── api.ts            ← typed fetch client
│   └── tests/
├── docker-compose.yml
├── docker-compose.override.yml
├── Dockerfile
├── entrypoint.sh
├── .env.sample                   ← committed; .env is gitignored
├── data/                         ← gitignored bind-mount targets
├── backups/                      ← gitignored
└── import/                       ← gitignored
```

### Pattern 1: FastAPI Lifespan (Recommended Current Pattern)

**What:** Use `@asynccontextmanager` lifespan function instead of deprecated `@app.on_event` handlers. The lifespan runs pre-yield code on startup and post-yield code on shutdown.

**Why use it:** `on_event` handlers are deprecated in FastAPI 0.93+. Lifespan is the standard since FastAPI 0.93.

**Source:** https://fastapi.tiangolo.com/advanced/events/

```python
# backend/app/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.infrastructure.db import engine, async_session_factory
from app.infrastructure.settings import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──
    # DB pool initializes automatically on first connection via asyncpg
    # (no explicit pool.connect() needed with SQLAlchemy async engine)
    yield
    # ── Shutdown ──
    await engine.dispose()

app = FastAPI(lifespan=lifespan, title="Recalium API")

# Include routers
from app.api.routes import ingest, archive, byok
app.include_router(ingest.router, prefix="/api")
app.include_router(archive.router, prefix="/api")
app.include_router(byok.router, prefix="/api")

# Serve bundled frontend (production: static build)
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="static")
```

**Note:** The Alembic migration (`alembic upgrade head`) runs in `entrypoint.sh` BEFORE Uvicorn starts. It is NOT inside the lifespan. This keeps migration as a one-shot subprocess, not an asyncio concern.

### Pattern 2: SQLAlchemy 2.x Async Session (Dependency Injection)

**What:** Use `AsyncSession` from SQLAlchemy 2.x with `async_sessionmaker`, injected via FastAPI `Depends`.

**Why:** SQLAlchemy 2.x async is production-stable and prevents the `MissingGreenlet` error that occurs when mixing sync session patterns in async routes.

```python
# backend/app/infrastructure/db.py
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from app.infrastructure.settings import settings

engine = create_async_engine(
    settings.database_url,          # postgresql+asyncpg://...
    pool_size=5,                     # Personal scale default
    max_overflow=10,
    pool_pre_ping=True,              # Re-validate connections after idle
    echo=settings.debug,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,          # IMPORTANT: prevents lazy-load on detached instances
)

async def get_db() -> AsyncSession:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

```python
# backend/app/api/routes/archive.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.db import get_db
from app.domain.archive.service import list_archive_items

router = APIRouter()

@router.get("/archive")
async def get_archive(db: AsyncSession = Depends(get_db)):
    items = await list_archive_items(db)
    return {"items": items}
```

**⚠ Critical:** `expire_on_commit=False` is required. Without it, accessing ORM attributes after `commit()` triggers a lazy-load that fails in async context with `MissingGreenlet`.

**⚠ Critical:** Never mix `session.execute()` (sync) with async sessions. Always `await session.execute()`.

### Pattern 3: Alembic Async Setup with env.py

**What:** Alembic's standard `env.py` uses synchronous connections. For an async project, use `asyncio.run()` wrapper with a sync connection via `AsyncEngine.sync_engine`.

**Source:** https://alembic.sqlalchemy.org/en/latest/cookbook.html#using-asyncio-with-alembic

```python
# alembic/env.py (async-compatible)
import asyncio
from logging.config import fileConfig
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy import pool
from alembic import context
from app.infrastructure.settings import settings

# Must import all models so autogenerate sees them
from app.domain.archive.models import Base  # noqa

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()

def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

### Pattern 4: Initial Migration — pgvector + Core Tables

**What:** Migration `0001_initial.py` creates pgvector extension and core Phase 1 tables. Extension creation must use `CREATE EXTENSION IF NOT EXISTS vector` (idempotent).

```python
# alembic/versions/0001_initial.py
"""Initial schema: pgvector extension + raw_archive + source_status enum

Revision ID: 0001
Revises:
Create Date: 2026-03-22
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0001'
down_revision = None

def upgrade() -> None:
    # pgvector extension — idempotent, safe to re-run
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # source_status enum — used across ALL derived tables from day one
    source_status_enum = postgresql.ENUM(
        'active', 'source_removed',
        name='source_status_enum',
        create_type=True,
    )
    source_status_enum.create(op.get_bind())

    # raw_archive table
    op.create_table(
        'raw_archive_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('source_name', sa.String(255), nullable=True),
        sa.Column('raw_content', sa.Text, nullable=False),
        sa.Column('content_hash', sa.String(64), nullable=False),
        sa.Column('item_count', sa.Integer, nullable=False, server_default='1'),
        sa.Column('ingested_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        # source_status for cascade semantics — even before derived tables exist
        sa.Column('source_status',
                  postgresql.ENUM('active', 'source_removed',
                                  name='source_status_enum', create_type=False),
                  nullable=False, server_default='active'),
    )

    # BYOK config table — stores ONLY fingerprints, never actual keys
    op.create_table(
        'byok_config',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('provider', sa.String(50), nullable=False, unique=True),
        sa.Column('key_configured', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('key_fingerprint', sa.String(10), nullable=True),
        sa.Column('endpoint_url', sa.String(500), nullable=True),  # Ollama only
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
    )

    # Indexes
    op.create_index('ix_raw_archive_ingested_at', 'raw_archive_items', ['ingested_at'])
    op.create_index('ix_raw_archive_content_hash', 'raw_archive_items', ['content_hash'])
    op.create_index('ix_raw_archive_deleted_at', 'raw_archive_items', ['deleted_at'])

def downgrade() -> None:
    op.drop_table('byok_config')
    op.drop_table('raw_archive_items')
    op.execute("DROP TYPE IF EXISTS source_status_enum")
    op.execute("DROP EXTENSION IF EXISTS vector")
```

**⚠ Note:** `embedding` columns are NOT added in this migration — they ship in Phase 2. The extension is installed here so Phase 2 can add vector columns without a separate extension migration.

### Pattern 5: Docker Compose Bind-Mount Topology

```yaml
# docker-compose.yml (production base)
services:
  recalium-postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-recalium}
      POSTGRES_USER: ${POSTGRES_USER:-recalium}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}
    volumes:
      # BIND MOUNT — not named volume. Survives docker compose down.
      # WARNING: Never run docker compose down -v
      - ./data/postgres:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-recalium}"]
      interval: 5s
      timeout: 5s
      retries: 10
    restart: unless-stopped

  recalium-app:
    build:
      context: .
      dockerfile: Dockerfile
    depends_on:
      recalium-postgres:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER:-recalium}:${POSTGRES_PASSWORD}@recalium-postgres:5432/${POSTGRES_DB:-recalium}
    volumes:
      - ./backups:/app/backups
      - ./import:/app/import
    ports:
      # Bind to 127.0.0.1 — localhost only, prevents DNS rebinding attack
      - "127.0.0.1:8080:8080"
    restart: unless-stopped
```

```yaml
# docker-compose.override.yml (dev only — hot-reload + direct DB access)
services:
  recalium-app:
    command: ["uvicorn", "app.main:app", "--host", "0.0.0.0",
              "--port", "8080", "--reload"]
    volumes:
      - ./backend:/app/backend  # mount source for hot-reload
    environment:
      DEBUG: "true"

  recalium-postgres:
    ports:
      - "127.0.0.1:5432:5432"  # expose for direct dev access (localhost only)
```

**⚠ CRITICAL:** Use `pgvector/pgvector:pg16` image — this is the official pgvector Docker image with the extension pre-installed. Do NOT use `postgres:16` and attempt to compile pgvector separately.

### Pattern 6: Entrypoint with PG Readiness Retry

```bash
#!/usr/bin/env sh
# entrypoint.sh — runs alembic upgrade head with retry before starting server
set -e

MAX_RETRIES=12   # 12 × 5s = 60s max wait
RETRY_INTERVAL=5

echo "Waiting for PostgreSQL..."
n=0
until python -c "
import asyncio, asyncpg, os, sys
async def check():
    try:
        conn = await asyncpg.connect(os.environ['DATABASE_URL'].replace('postgresql+asyncpg://', 'postgresql://'))
        await conn.close()
    except Exception as e:
        print(f'PG not ready: {e}', file=sys.stderr)
        sys.exit(1)
asyncio.run(check())
" 2>/dev/null; do
  n=$((n+1))
  if [ "$n" -ge "$MAX_RETRIES" ]; then
    echo "ERROR: PostgreSQL did not become ready within 60 seconds." >&2
    exit 1
  fi
  echo "  Retrying in ${RETRY_INTERVAL}s (attempt $n/$MAX_RETRIES)..."
  sleep "$RETRY_INTERVAL"
done

echo "PostgreSQL ready. Running migrations..."
cd /app/backend && alembic upgrade head

echo "Starting Uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8080
```

**Note:** The `depends_on: condition: service_healthy` in docker-compose handles most wait scenarios. The entrypoint retry is belt-and-suspenders for edge cases (e.g., PG accepting connections but not yet ready for queries).

### Pattern 7: React 19 + Vite 8 + shadcn/ui 2.x Setup

```bash
# 1. Verify Node version (MUST be >=20.19.0)
node --version

# 2. Scaffold with Vite
pnpm create vite@8 . --template react-ts

# 3. Install React 19 explicitly (Vite template may default to 18)
pnpm add react@19 react-dom@19

# 4. Install Tailwind v4 with Vite plugin (CSS-first config)
pnpm add tailwindcss @tailwindcss/vite

# 5. Configure vite.config.ts
# plugins: [react(), tailwindcss()]
# No tailwind.config.js needed — Tailwind v4 uses CSS @import

# 6. Add to main CSS:
# @import "tailwindcss";

# 7. Initialize shadcn/ui 2.x (handles Tailwind v4 integration)
pnpm dlx shadcn@latest init

# 8. Add components used in Phase 1
pnpm dlx shadcn@latest add sidebar button input card toast tabs badge
```

**⚠ Tailwind v4 gotcha:** There is NO `tailwind.config.js`. Configuration is entirely via CSS (`@import "tailwindcss"` + CSS variables). shadcn/ui 2.x CLI handles this automatically — do NOT create a `tailwind.config.js` manually.

**⚠ shadcn/ui navigation:** Use the `Sidebar` component (not custom CSS) for the left-nav. shadcn Sidebar is built for exactly this pattern and includes disabled state support via `aria-disabled`.

### Pattern 8: BYOK Key Validation (Per-Provider Test Calls)

**What:** Each provider is validated with the smallest, cheapest possible API call.

```python
# backend/app/domain/policy/byok_validator.py
import httpx
from typing import Literal

ByokResult = Literal["valid", "invalid", "insufficient_permissions", "unreachable"]

async def validate_openai_key(api_key: str) -> ByokResult:
    """Uses models.list — ~1KB response, no cost."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            "https://api.openai.com/v1/models",
            headers={"Authorization": f"Bearer {api_key}"},
        )
    if resp.status_code == 200:
        return "valid"
    if resp.status_code == 401:
        return "invalid"
    if resp.status_code == 403:
        return "insufficient_permissions"
    return "invalid"

async def validate_anthropic_key(api_key: str) -> ByokResult:
    """Uses models.list endpoint — lowest-cost validation."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            "https://api.anthropic.com/v1/models",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
        )
    if resp.status_code == 200:
        return "valid"
    if resp.status_code == 401:
        return "invalid"
    if resp.status_code == 403:
        return "insufficient_permissions"
    return "invalid"

async def validate_ollama_endpoint(base_url: str, api_key: str | None = None) -> ByokResult:
    """GET /api/tags — checks Ollama is reachable and optionally authenticated."""
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{base_url.rstrip('/')}/api/tags", headers=headers)
        if resp.status_code == 200:
            return "valid"
        if resp.status_code in (401, 403):
            return "insufficient_permissions"
        return "invalid"
    except httpx.ConnectError:
        return "unreachable"
```

**Key storage (what goes in DB vs .env):**
```python
# backend/app/infrastructure/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str
    debug: bool = False

    # BYOK keys — live in .env ONLY. Never persisted to DB.
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    ollama_base_url: str | None = None
    ollama_api_key: str | None = None  # optional

settings = Settings()
```

**DB BYOK table stores ONLY (per D-12):**
- `provider`: "openai" | "anthropic" | "ollama"
- `key_configured`: bool
- `key_fingerprint`: last 4 chars of key (for display only)
- `endpoint_url`: Ollama URL only

### Pattern 9: ChatGPT and Claude JSON Export Format Structure

**Purpose:** Ingest parser must auto-detect format and extract individual conversations.

#### ChatGPT Export (`conversations.json`)

```
Root structure: array of conversation objects
[
  {
    "title": "string",
    "create_time": float (unix timestamp),
    "update_time": float (unix timestamp),
    "mapping": {
      "<node_id>": {
        "id": "string",
        "message": {
          "id": "string",
          "author": { "role": "system"|"user"|"assistant"|"tool" },
          "content": {
            "content_type": "text"|"code"|"image_asset_pointer"|...,
            "parts": ["string", ...]  # array of text parts
          },
          "create_time": float | null,
          "status": "finished_successfully"|...,
          "weight": float
        } | null,
        "parent": "<node_id>" | null,
        "children": ["<node_id>", ...]
      }
    },
    "conversation_id": "string",
    "current_node": "<node_id>"
  },
  ...
]
```

**Detection:** Top-level is a JSON array; each item has `"mapping"` key (dict) and `"conversation_id"` key.

**Extraction:** Walk `mapping` depth-first from `current_node` backwards through `parent` links, collecting messages in order.

#### Claude Export (Anthropic export zip → `conversations.json`)

```
Root structure: array of conversation objects
[
  {
    "uuid": "string",
    "name": "string",
    "created_at": "ISO-8601 string",
    "updated_at": "ISO-8601 string",
    "account": { "uuid": "string" },
    "chat_messages": [
      {
        "uuid": "string",
        "text": "string",
        "content": [
          { "type": "text", "text": "string" },
          ...
        ],
        "sender": "human" | "assistant",
        "created_at": "ISO-8601 string",
        "updated_at": "ISO-8601 string",
        "attachments": [...],
        "files": [...]
      },
      ...
    ]
  },
  ...
]
```

**Detection:** Top-level is a JSON array; each item has `"chat_messages"` key (array) and `"uuid"` key; `chat_messages[n].sender` is `"human"` or `"assistant"` (not `"user"` or `"role"`).

#### Generic JSON (fallback)

Accept any JSON that is either:
- An array of objects (treat each as a conversation/message)
- A single object with a recognizable text field

#### Format Detection Algorithm

```python
def detect_format(data: Any) -> Literal["chatgpt", "claude", "generic_json"]:
    if isinstance(data, list) and len(data) > 0:
        first = data[0]
        if isinstance(first, dict):
            if "mapping" in first and "conversation_id" in first:
                return "chatgpt"
            if "chat_messages" in first and "uuid" in first:
                return "claude"
    return "generic_json"
```

### Pattern 10: Vite Dev Server Proxy (Agent's Discretion)

**Recommendation:** Use Vite proxy to forward `/api/*` to the FastAPI backend during development. This avoids CORS configuration and keeps frontend dev server at port 5173 while API runs at 8080.

```typescript
// vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8080',
        changeOrigin: true,
      }
    }
  }
})
```

In production, FastAPI serves the built frontend as `StaticFiles`, so `/api` routes are handled by FastAPI and `/*` falls through to the SPA index.html.

### Anti-Patterns to Avoid

- **`@app.on_event("startup")` deprecated:** Use `@asynccontextmanager lifespan` instead.
- **Named Docker volumes:** Use `./data/postgres:/var/lib/postgresql/data` bind mount. Named volumes are destroyed by `docker compose down -v`.
- **`expire_on_commit=True` (default):** Will cause `MissingGreenlet` on any attribute access after commit in async context. Set `expire_on_commit=False`.
- **Synchronous SQLAlchemy in async route:** All `session.execute()` calls must be `await session.execute()`.
- **API key in any DB column:** Keys in `.env` only. Startup assertion verifies this.
- **`CREATE EXTENSION vector` without IF NOT EXISTS:** Fails if already installed on restart. Use `CREATE EXTENSION IF NOT EXISTS vector`.
- **`tailwind.config.js` with Tailwind v4:** Tailwind v4 uses CSS-first config. `tailwind.config.js` is ignored in v4.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| `.env` file loading | Custom os.getenv wrapper | `pydantic-settings` | Type coercion, validation, nested settings, `.env.sample` alignment |
| PG connection pool | Manual asyncpg pool | `create_async_engine(pool_size=5)` | SQLAlchemy manages pool lifecycle, health checks, recycle |
| DB migration runner | Custom schema DDL at startup | `alembic upgrade head` in entrypoint | Revision history, downgrade support, concurrent-safe |
| API key obfuscation | Custom last-4-chars logic | `key[-4:]` in BYOK service + `key_configured=True` | Already trivial; the critical rule is no key in DB at all |
| JSON format detection | ML classifier | Structural key inspection (`"mapping"` vs `"chat_messages"`) | Deterministic, zero-cost, covers all known formats |
| CORS for dev | Custom dev middleware | Vite proxy (`/api` → localhost:8080) | No CORS config needed in FastAPI dev; proxy is transparent |
| Docker healthcheck | curl | `pg_isready` in PostgreSQL healthcheck | pg-native, available in all PG images |

**Key insight:** Phase 1 is foundational scaffolding. Every custom solution here creates tech debt that must be maintained across 4 more phases. Prefer boring standard patterns.

---

## Common Pitfalls

### Pitfall 1: `docker compose down -v` Data Destruction

**What goes wrong:** Developer runs `docker compose down -v` to "reset" and destroys all PostgreSQL data permanently. Named volumes are in a Docker VM on macOS and are not backed up by Time Machine.

**How to avoid:**
- Use bind mount `./data/postgres:/var/lib/postgresql/data` (D-06, locked).
- Add prominent comment in `docker-compose.yml` above the volume definition.
- Never document or use `docker compose down -v` in any script or README.
- Pre-create `./data/`, `./backups/`, `./import/` directories in a `make init` target.

**Warning signs:** `docker-compose.yml` has `volumes:` at top level with named volumes.

### Pitfall 2: API Keys Written to Database

**What goes wrong:** Convenient "store all settings in PostgreSQL" approach persists actual API key strings. `pg_dump` leaks them. Sharing a debug dump exposes all provider keys.

**How to avoid:**
- Keys in `.env` only (D-12, locked).
- `byok_config` table stores ONLY `key_configured: bool`, `key_fingerprint: str (4 chars)`, `endpoint_url`.
- Startup assertion: scan `byok_config` column types and names; assert no column matches `*_key` with a value length > 10.
- Test: configure a key, take a pg_dump, grep for the key string — assert not found.

### Pitfall 3: MissingGreenlet on Attribute Access After Commit

**What goes wrong:** After `await session.commit()`, accessing any ORM relationship attribute triggers a lazy-load that fails with `MissingGreenlet` in async context.

**How to avoid:**
- Set `expire_on_commit=False` in `async_sessionmaker`.
- Use `selectinload()` or `joinedload()` for any relationship that needs to be accessed post-commit.
- Never access lazy relationships outside the session context.

### Pitfall 4: source_status Missing From Day-One Schema

**What goes wrong:** A derived table added in Phase 2 (summaries, facts) lacks `source_status`. When raw source is deleted in Phase 4, orphaned derived data remains and surfaces in search results. Retro-adding cascade semantics to a live table with data is painful.

**How to avoid (locked in D-09):**
- Add `source_status ENUM('active', 'source_removed') NOT NULL DEFAULT 'active'` to **every** derived table, even if deletion UI ships in Phase 4.
- The `raw_archive_items` table also carries `source_status` as the root of the cascade.
- Phase 1 migration establishes the ENUM type — later migrations reuse it with `create_type=False`.

### Pitfall 5: Node Version Too Low for Vite 8

**What goes wrong:** Vite 8 silently fails or shows cryptic errors on Node 18 or Node 20.0–20.18.

**How to avoid:**
- Assert `node --version` >= 20.19.0 before frontend scaffolding.
- Add node version check to `entrypoint.sh` for any CI that builds the frontend.
- Document in README: "Requires Node >=20.19.0"

### Pitfall 6: Tailwind v4 + tailwind.config.js

**What goes wrong:** Developer creates a `tailwind.config.js` expecting Tailwind v3 behavior. Tailwind v4 ignores it. shadcn/ui components have no theme variables. Styling breaks silently.

**How to avoid:**
- Do NOT create `tailwind.config.js` with Tailwind v4.
- Configuration is entirely in CSS: `@import "tailwindcss"` + CSS custom properties.
- Run `pnpm dlx shadcn@latest init` AFTER Tailwind v4 is installed — the CLI writes the correct CSS config automatically.

### Pitfall 7: Alembic `CREATE EXTENSION vector` Without IF NOT EXISTS

**What goes wrong:** On container restart, migration `0001_initial.py` runs again (already at head, so this won't happen with `upgrade head` — but in fresh environments or if revision tracking is corrupted, re-running `0001` without `IF NOT EXISTS` fails with "extension already exists".

**How to avoid:**
- Always use `CREATE EXTENSION IF NOT EXISTS vector`.
- Same pattern for ENUM type: add `IF NOT EXISTS` guard or check before creation.

### Pitfall 8: Alembic env.py Not Importing Models

**What goes wrong:** `alembic revision --autogenerate` generates empty migrations because `target_metadata = Base.metadata` is imported but no model files were imported first, so Base has no tables registered.

**How to avoid:**
- In `alembic/env.py`, import all domain model modules before referencing `Base.metadata`.
- Add a `# noqa: F401` comment to suppress "unused import" linter warnings.

```python
# alembic/env.py — model imports required for autogenerate
from app.domain.archive.models import *  # noqa: F401, F403
from app.domain.jobs.models import *     # noqa: F401, F403
target_metadata = Base.metadata
```

---

## Code Examples

### Session Dependency with Rollback Safety

```python
# backend/app/infrastructure/db.py
async def get_db() -> AsyncSession:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        # Session closes automatically via async context manager
```

### Pydantic-settings with .env.sample Alignment

```python
# backend/app/infrastructure/settings.py
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str

    # App
    debug: bool = False
    app_host: str = "0.0.0.0"
    app_port: int = 8080

    # BYOK — keys never in DB
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    ollama_base_url: str | None = None
    ollama_api_key: str | None = None  # some Ollama deployments require auth

    @property
    def has_openai(self) -> bool:
        return bool(self.openai_api_key)

    @property
    def has_anthropic(self) -> bool:
        return bool(self.anthropic_api_key)

    @property
    def has_ollama(self) -> bool:
        return bool(self.ollama_base_url)

settings = Settings()
```

```bash
# .env.sample — committed alongside code
# Copy to .env and fill in values before first run

# Database — required
DATABASE_URL=postgresql+asyncpg://recalium:changeme@recalium-postgres:5432/recalium

# PostgreSQL container credentials
POSTGRES_DB=recalium
POSTGRES_USER=recalium
POSTGRES_PASSWORD=changeme   # CHANGE THIS — never use default in production

# App
DEBUG=false
APP_HOST=0.0.0.0
APP_PORT=8080

# BYOK — OPTIONAL — keys live here ONLY, never in the database
# OpenAI (for embeddings + summarization)
OPENAI_API_KEY=
# Anthropic (for summarization, alternative to OpenAI)
ANTHROPIC_API_KEY=
# Ollama (local/private deployment)
OLLAMA_BASE_URL=
OLLAMA_API_KEY=
```

### Ingest Endpoint (Structure)

```python
# backend/app/api/routes/ingest.py
from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.db import get_db
from app.domain.ingest.service import ingest_text, ingest_file
from pydantic import BaseModel

router = APIRouter()

class IngestTextRequest(BaseModel):
    content: str
    source_name: str | None = None

class IngestResponse(BaseModel):
    conversation_count: int
    archive_ids: list[str]

@router.post("/ingest/text", response_model=IngestResponse)
async def ingest_text_endpoint(
    request: IngestTextRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await ingest_text(db, request.content, request.source_name)
    return result

@router.post("/ingest/file", response_model=IngestResponse)
async def ingest_file_endpoint(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    result = await ingest_file(db, content, file.filename)
    return result
```

### BYOK Validation Flow

```python
# backend/app/api/routes/byok.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.db import get_db
from app.infrastructure.settings import settings
from app.domain.policy.byok_validator import (
    validate_openai_key, validate_anthropic_key, validate_ollama_endpoint
)
from pydantic import BaseModel

router = APIRouter()

class ByokValidateRequest(BaseModel):
    provider: str  # "openai" | "anthropic" | "ollama"

class ByokValidateResponse(BaseModel):
    provider: str
    status: str  # "valid" | "invalid" | "insufficient_permissions" | "unreachable"
    fingerprint: str | None = None

@router.post("/settings/byok/validate", response_model=ByokValidateResponse)
async def validate_byok(
    request: ByokValidateRequest,
    db: AsyncSession = Depends(get_db),
):
    provider = request.provider
    if provider == "openai":
        if not settings.openai_api_key:
            raise HTTPException(400, "OPENAI_API_KEY not set in environment")
        result = await validate_openai_key(settings.openai_api_key)
        fingerprint = settings.openai_api_key[-4:] if result == "valid" else None
    elif provider == "anthropic":
        if not settings.anthropic_api_key:
            raise HTTPException(400, "ANTHROPIC_API_KEY not set in environment")
        result = await validate_anthropic_key(settings.anthropic_api_key)
        fingerprint = settings.anthropic_api_key[-4:] if result == "valid" else None
    elif provider == "ollama":
        if not settings.ollama_base_url:
            raise HTTPException(400, "OLLAMA_BASE_URL not set in environment")
        result = await validate_ollama_endpoint(settings.ollama_base_url, settings.ollama_api_key)
        fingerprint = None
    else:
        raise HTTPException(400, f"Unknown provider: {provider}")

    # Persist fingerprint to byok_config (not the key itself)
    if fingerprint:
        await upsert_byok_config(db, provider, fingerprint)

    return ByokValidateResponse(provider=provider, status=result, fingerprint=fingerprint)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `@app.on_event("startup")` | `@asynccontextmanager lifespan` | FastAPI 0.93 (2023) | Startup/shutdown logic now co-located; old handlers deprecated |
| `tailwind.config.js` | CSS-first `@import "tailwindcss"` | Tailwind v4 (2025) | No JS config file; all customization in CSS variables |
| shadcn/ui for React 18 | shadcn/ui 2.x for React 19 | shadcn/ui v2 (2025) | New install command `pnpm dlx shadcn@latest init`; not `npx shadcn-ui@latest` |
| `pip` + `requirements.txt` | `uv` + `pyproject.toml` | uv 0.x → stable (2024) | 10-100x faster installs; lockfile via `uv.lock` |
| `pytest-asyncio` 0.x | `pytest-asyncio` 1.x | 2025 | Asyncio mode config syntax changed; `asyncio_mode = "auto"` in `pyproject.toml` |

**Deprecated/outdated:**
- `@app.on_event`: Still works but deprecated; generates deprecation warning in FastAPI 0.93+
- `tailwind.config.js` with Tailwind v4: Silently ignored; use CSS `@layer` and custom properties
- React 18 for new code: shadcn/ui 2.x targets React 19; starting on 18 means mandatory migration
- Named Docker volumes for persistent data: Survivorship risk with `docker compose down -v`

---

## Open Questions

1. **`tech-stack.md` says "React 18" but STACK.md (live-verified) says React 19**
   - What we know: STATE.md and STACK.md both say React 19; tech-stack.md was created before live stack verification
   - Recommendation: Treat React 19 as correct (confirmed by live npm fetch). Update `docs/architecture/tech-stack.md` to React 19 in Phase 1 scaffolding commit.

2. **pgvector/pgvector Docker image tag**
   - What we know: `pgvector/pgvector:pg16` exists and includes pgvector; exact pgvector version in that image tag is not pinned to 0.8.2 specifically
   - What's unclear: Does `pgvector/pgvector:pg16` include pgvector 0.8.2 as of 2026-03?
   - Recommendation: Use `pgvector/pgvector:pg16` and verify extension version with `SELECT extversion FROM pg_extension WHERE extname='vector'` in post-deploy healthcheck. If < 0.8.2, pin to a specific image digest.

3. **pytest-asyncio 1.3.0 mode configuration**
   - What we know: v1.x changed asyncio mode configuration syntax from 0.x
   - What's unclear: exact `pyproject.toml` / `pytest.ini` configuration for `asyncio_mode = "auto"` in 1.3.0
   - Recommendation: Use `asyncio_mode = "auto"` in `[tool.pytest.ini_options]` in `pyproject.toml`. If this syntax fails, fall back to per-test `@pytest.mark.asyncio` decorator.

---

## Validation Architecture

> nyquist_validation is enabled (not set to false in config.json)

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio 1.3.0 |
| Config file | `backend/pyproject.toml` `[tool.pytest.ini_options]` — Wave 0 |
| Quick run command | `pytest backend/tests/ -x -q` |
| Full suite command | `pytest backend/tests/ -v` |
| Frontend | Vitest 3.x — `pnpm test` in `frontend/` |
| Frontend full | `pnpm run test:coverage` |

### Phase 1 Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INGT-01 | POST /api/ingest/text → 200, item in archive | integration | `pytest backend/tests/test_ingest.py::test_paste_ingest -x` | ❌ Wave 0 |
| INGT-01 | P95 ≤ 1s for paste ingest (single item) | smoke | `pytest backend/tests/test_ingest.py::test_ingest_latency -x` | ❌ Wave 0 |
| INGT-02 | POST /api/ingest/file (ChatGPT JSON) → N items created | integration | `pytest backend/tests/test_ingest.py::test_chatgpt_upload -x` | ❌ Wave 0 |
| INGT-02 | POST /api/ingest/file (Claude JSON) → N items created | integration | `pytest backend/tests/test_ingest.py::test_claude_upload -x` | ❌ Wave 0 |
| INGT-02 | POST /api/ingest/file (generic JSON) → handled | integration | `pytest backend/tests/test_ingest.py::test_generic_json_upload -x` | ❌ Wave 0 |
| INGT-03 | GET /api/archive returns ingested items | integration | `pytest backend/tests/test_archive.py::test_list_archive -x` | ❌ Wave 0 |
| BKUP-04 | Data survives container restart (bind mount) | manual | Manual: `docker compose restart`; verify archive count unchanged | manual only |
| WEBUI-01 | Left-nav renders all 8 items; 6 items disabled | component | `pnpm test -- IngestLayout` | ❌ Wave 0 |
| WEBUI-04 | (Chrome-only; no automated cross-browser) | manual | Manual: verify in Chrome/Chromium | manual only |
| BYOK-02 | GET /api/settings/byok returns provider status | integration | `pytest backend/tests/test_byok.py::test_get_byok_status -x` | ❌ Wave 0 |
| BYOK-03 | POST /api/settings/byok/validate → "valid" for valid key | integration (mock) | `pytest backend/tests/test_byok.py::test_validate_openai_key -x` | ❌ Wave 0 |
| BYOK-03 | POST /api/settings/byok/validate → "invalid" for bad key | integration (mock) | `pytest backend/tests/test_byok.py::test_validate_invalid_key -x` | ❌ Wave 0 |
| BYOK-04 | pg_dump output never contains API key strings | security assertion | `pytest backend/tests/test_byok.py::test_key_not_in_db -x` | ❌ Wave 0 |
| BYOK-05 | App starts + serves archive GET when no keys configured | integration | `pytest backend/tests/test_byok.py::test_degraded_mode_no_keys -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `pytest backend/tests/ -x -q` (all backend unit/integration)
- **Per wave merge:** `pytest backend/tests/ -v && pnpm test` (full suite both sides)
- **Phase gate:** Full suite green + manual BKUP-04 (restart) + manual WEBUI-04 (Chrome check)

### Wave 0 Gaps (must be created before implementation)

- [ ] `backend/tests/conftest.py` — async test DB session fixture (uses test database or in-memory via async engine)
- [ ] `backend/tests/test_ingest.py` — covers INGT-01, INGT-02, INGT-03
- [ ] `backend/tests/test_archive.py` — covers INGT-03
- [ ] `backend/tests/test_byok.py` — covers BYOK-02, BYOK-03, BYOK-04, BYOK-05
- [ ] `frontend/src/tests/IngestPage.test.tsx` — covers WEBUI-01 (left-nav disabled items)
- [ ] `backend/pyproject.toml` `[tool.pytest.ini_options]` with `asyncio_mode = "auto"`
- [ ] Framework install: `uv add --dev pytest pytest-asyncio==1.3.0 httpx` in `backend/`

---

## Sources

### Primary (HIGH confidence)

- `.planning/research/STACK.md` — live-verified package versions, 2026-03-22
- `.planning/research/PITFALLS.md` — pitfall registry, verified against official sources, 2026-03-22
- `docs/architecture/component-boundaries.md` — module map, dependency rules
- `docs/architecture/container-topology.md` — two-container topology
- `docs/architecture/tech-stack.md` — committed stack (note: React version stale, see Open Questions)
- https://fastapi.tiangolo.com/advanced/events/ — lifespan pattern (official FastAPI docs, verified)
- https://alembic.sqlalchemy.org/en/latest/cookbook.html — async Alembic env.py pattern (official)
- https://fastapi.tiangolo.com/tutorial/bigger-applications/ — APIRouter pattern (official)

### Secondary (MEDIUM confidence)

- ChatGPT JSON export structure: derived from community-documented format + direct structural analysis patterns. Format has been stable since 2023 but is undocumented officially by OpenAI.
- Claude JSON export structure: similar community-documented format; Anthropic does not publish a formal schema.

### Tertiary (LOW confidence)

- pytest-asyncio 1.3.0 exact `pyproject.toml` syntax — flagged in Open Questions above

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions live-verified in STACK.md (2026-03-22)
- Architecture patterns: HIGH — FastAPI lifespan and Alembic async from official docs
- ChatGPT/Claude format: MEDIUM — stable community-documented formats, no official schema
- Pitfalls: HIGH — verified against official docs in PITFALLS.md

**Research date:** 2026-03-22
**Valid until:** 2026-04-22 (30 days for stable stack; fast-moving: pnpm, uv — recheck if > 2 weeks)
