---
wave: 1
depends_on: []
requirements_addressed: [BKUP-04, INGT-03]
files_modified:
  - backend/pyproject.toml
  - backend/alembic.ini
  - backend/alembic/env.py
  - backend/alembic/versions/0001_initial.py
autonomous: true
---

<objective>
Bootstrap the Python backend package (uv + pyproject.toml), configure Alembic, and create the initial database migration that establishes: the pgvector extension, the raw archive table (with soft-delete and source metadata), the settings table (key fingerprints only — no plaintext keys), a jobs stub table, and the audit_events table. After this plan, `alembic upgrade head` produces a correct schema that all subsequent plans build on.

Purpose: Establishes the schema contract for all Phase 1 feature plans. The source_status column and soft-delete pattern must be correct from migration 0001 — retroactive fixes are expensive (Pitfall 1).
Output: backend/pyproject.toml, backend/alembic.ini, backend/alembic/env.py, backend/alembic/versions/0001_initial.py
</objective>

<tasks>

<task id="1" name="Initialize uv project and pyproject.toml">
  <read_first>
    - .planning/research/STACK.md (exact versions: FastAPI 0.135.1, asyncpg 0.31.0, SQLAlchemy 2.0.48, etc.)
    - .planning/phases/01-foundation/01-CONTEXT.md (D-04 — uv, pyproject.toml at backend/)
  </read_first>
  <action>
Create `backend/pyproject.toml` with the following content. This defines all production and dev dependencies at exact pinned versions from STACK.md.

```toml
[project]
name = "recalium"
version = "0.1.0"
description = "Local-first MCP-native personal memory platform"
requires-python = ">=3.12"
dependencies = [
    # Web framework
    "fastapi==0.135.1",
    "uvicorn[standard]==0.42.0",
    # Database
    "sqlalchemy==2.0.48",
    "asyncpg==0.31.0",
    "alembic==1.18.4",
    # Validation & settings
    "pydantic==2.12.5",
    "pydantic-settings>=2.0,<3",
    # HTTP client (async — never use requests)
    "httpx==0.28.1",
    # MCP SDK (pin <2 — v2 has breaking transport changes)
    "mcp>=1.26,<2",
    # Embeddings (local, no API key required)
    "sentence-transformers==5.3.0",
    # BYOK providers
    "openai>=1.0,<2",
    "anthropic>=0.20,<1",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0,<9",
    "pytest-asyncio==1.3.0",
    "httpx>=0.28",
    "ruff>=0.9",
    "mypy>=1.0",
]

[tool.uv]
dev-dependencies = [
    "pytest>=8.0,<9",
    "pytest-asyncio==1.3.0",
    "httpx>=0.28",
    "ruff>=0.9",
    "mypy>=1.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.mypy]
python_version = "3.12"
strict = true
ignore_missing_imports = true
```

After writing the file, the executor should run inside `backend/`:
```bash
uv lock
```
to generate `backend/uv.lock` (commit this file — it pins all transitive deps).

If uv is not available locally, the lock file will be generated during the Docker build. In that case, create an empty `backend/uv.lock` placeholder and add a comment: `# Run: cd backend && uv lock`.
  </action>
  <acceptance_criteria>
    - `grep -n "fastapi==0.135.1" backend/pyproject.toml` returns 1 line
    - `grep -n "asyncpg==0.31.0" backend/pyproject.toml` returns 1 line
    - `grep -n "sqlalchemy==2.0.48" backend/pyproject.toml` returns 1 line
    - `grep -n "alembic==1.18.4" backend/pyproject.toml` returns 1 line
    - `grep -n "pytest-asyncio==1.3.0" backend/pyproject.toml` returns 1 line
    - `grep -n "mcp>=1.26,<2" backend/pyproject.toml` returns 1 line
    - `grep -n "pydantic==2.12.5" backend/pyproject.toml` returns 1 line
    - `grep -n "asyncio_mode = \"auto\"" backend/pyproject.toml` returns 1 line
    - File `backend/pyproject.toml` exists and is valid TOML (python3 -c "import tomllib; tomllib.load(open('backend/pyproject.toml','rb'))" exits 0)
  </acceptance_criteria>
</task>

<task id="2" name="Configure Alembic (alembic.ini + async env.py)">
  <read_first>
    - .planning/research/STACK.md (SQLAlchemy async, Alembic async pattern)
    - .planning/phases/01-foundation/01-CONTEXT.md (D-08 — entrypoint calls alembic upgrade head)
  </read_first>
  <action>
Create `backend/alembic.ini`:

```ini
[alembic]
# Alembic configuration for Recalium.
# script_location is relative to this file.
script_location = alembic
# version_path_separator = os (default)
# timezone = UTC

# Database URL is overridden in env.py from DATABASE_URL env var.
# Do NOT put real credentials here — this file is committed.
sqlalchemy.url = driver://user:pass@host/dbname

[post_write_hooks]
# Optional: auto-format generated migration files
# hooks = ruff
# ruff.type = exec
# ruff.entrypoint = ruff
# ruff.options = format %(output)

[loggers]
keys = root, sqlalchemy, alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

Create `backend/alembic/env.py` — async-aware, reads DATABASE_URL from environment:

```python
"""Alembic migration environment — async SQLAlchemy engine."""
from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import async_engine_from_config

# Import Base so Alembic sees all models for autogenerate.
# Add new model imports here as modules are created.
from app.infrastructure.db import Base  # noqa: F401 — registers metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override sqlalchemy.url with environment variable (never use alembic.ini value in prod).
database_url = os.environ.get("DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (no DB connection — outputs SQL)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):  # type: ignore[no-untyped-def]
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations using an async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=None,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (connects to DB)."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

Create `backend/alembic/script.py.mako` (Alembic template for new migration files):

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

Also create the empty `backend/alembic/versions/` directory (will hold migration files).
  </action>
  <acceptance_criteria>
    - `grep -n "script_location = alembic" backend/alembic.ini` returns 1 line
    - `grep -n "DATABASE_URL" backend/alembic/env.py` returns 1 line (environment override)
    - `grep -n "async_engine_from_config" backend/alembic/env.py` returns 1 line
    - `grep -n "run_sync" backend/alembic/env.py` returns 1 line
    - `grep -n "from app.infrastructure.db import Base" backend/alembic/env.py` returns 1 line
    - Directory `backend/alembic/versions/` exists
  </acceptance_criteria>
</task>

<task id="3" name="Write migration 0001_initial.py — schema with pgvector, raw archive, settings, jobs, audit">
  <read_first>
    - .planning/phases/01-foundation/01-CONTEXT.md (D-09 source_status, D-10 soft-delete, D-11 pgvector, D-12 key fingerprint only)
    - .planning/research/PITFALLS.md (Pitfall 1 — cascade flags from day one, Pitfall 5 — no keys in DB)
    - docs/architecture/component-boundaries.md (ingest, archive, jobs, audit, policy modules)
  </read_first>
  <action>
Create `backend/alembic/versions/0001_initial.py`:

```python
"""Initial schema: pgvector extension, raw archive, settings (BYOK fingerprints),
jobs stub, and audit events.

SECURITY CONTRACT:
- settings table stores ONLY key fingerprints (last 4 chars) and booleans.
- No column in any table is named *_key, *_secret, or *_token that holds
  a real credential. A startup assertion in app/infrastructure/db.py enforces this.

CASCADE CONTRACT:
- Every future derived table MUST include source_status ENUM('active','source_removed').
- raw_archive uses soft-delete (deleted_at TIMESTAMP NULL).
- All queries must filter deleted_at IS NULL.

Revision ID: 0001
Revises: None
Create Date: 2026-03-22
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── pgvector extension ──────────────────────────────────────────────────
    # Enable pgvector. The extension is pre-installed in pgvector/pgvector:pg16.
    # Embedding columns are added in Phase 2; the extension must exist now.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ── source_status ENUM ─────────────────────────────────────────────────
    # Used on ALL tables with derived data. Created once here, referenced by
    # all derived tables in future migrations.
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE source_status AS ENUM ('active', 'source_removed');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """)

    # ── raw_archive table ──────────────────────────────────────────────────
    # Stores every ingested conversation in its raw form.
    # soft-delete: deleted_at IS NULL means active; IS NOT NULL means soft-deleted.
    # All read queries MUST filter WHERE deleted_at IS NULL.
    op.create_table(
        "raw_archive",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("source_type", sa.String(64), nullable=False),
        # "chatgpt_json", "claude_json", "generic_json", "paste_text", "paste_markdown"
        sa.Column("source_name", sa.String(255), nullable=True),
        # Human-readable name (e.g. "ChatGPT export 2026-01-15")
        sa.Column("source_uri", sa.Text, nullable=True),
        # Optional: original filename or URL hint
        sa.Column("raw_content", sa.Text, nullable=False),
        # The verbatim ingested text / JSON
        sa.Column("content_hash", sa.String(64), nullable=False),
        # SHA-256 of raw_content for dedup detection (added Phase 2)
        sa.Column("conversation_count", sa.Integer, nullable=False, server_default="1"),
        # Number of conversations/turns in this raw item
        sa.Column("ingested_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        # Soft-delete: NULL = active; NOT NULL = deleted; filter in ALL queries
        sa.Column("metadata_json", sa.JSON, nullable=True),
        # Extra structured metadata from the source (e.g. ChatGPT conversation ID)
    )
    op.create_index("ix_raw_archive_ingested_at", "raw_archive", ["ingested_at"])
    op.create_index("ix_raw_archive_deleted_at", "raw_archive", ["deleted_at"],
                    postgresql_where=sa.text("deleted_at IS NOT NULL"))
    op.create_index("ix_raw_archive_content_hash", "raw_archive", ["content_hash"])

    # ── settings table (BYOK fingerprints — NO plaintext keys) ────────────
    # SECURITY: This table MUST NEVER hold plaintext API keys.
    # Columns ending in _fingerprint store the last 4 characters of a key.
    # Columns ending in _configured store a boolean: key is set in .env.
    # The actual keys live ONLY in .env / environment variables.
    op.create_table(
        "settings",
        sa.Column("id", sa.Integer, primary_key=True),
        # Single-row table (singleton pattern); id is always 1.

        # OpenAI
        sa.Column("openai_key_fingerprint", sa.String(4), nullable=True),
        sa.Column("openai_key_configured", sa.Boolean, nullable=False, server_default="false"),

        # Anthropic
        sa.Column("anthropic_key_fingerprint", sa.String(4), nullable=True),
        sa.Column("anthropic_key_configured", sa.Boolean, nullable=False, server_default="false"),

        # Ollama
        sa.Column("ollama_base_url", sa.String(512), nullable=True),
        # Ollama URL is not sensitive — storing it is fine
        sa.Column("ollama_key_fingerprint", sa.String(4), nullable=True),
        sa.Column("ollama_key_configured", sa.Boolean, nullable=False, server_default="false"),

        # Validation results (last check)
        sa.Column("openai_validation_status", sa.String(32), nullable=True),
        # "valid", "invalid", "insufficient_permissions", "unchecked"
        sa.Column("anthropic_validation_status", sa.String(32), nullable=True),
        sa.Column("ollama_validation_status", sa.String(32), nullable=True),
        sa.Column("openai_validated_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("anthropic_validated_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("ollama_validated_at", sa.TIMESTAMP(timezone=True), nullable=True),

        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    # Insert the singleton row so reads never return NULL
    op.execute("INSERT INTO settings (id) VALUES (1) ON CONFLICT DO NOTHING")

    # ── jobs table (stub for Phase 2 worker) ──────────────────────────────
    # Phase 1 stub: enqueue jobs at ingest time; worker processes them in Phase 2.
    # index on (status, created_at) per Pitfall 9 (full table scan prevention).
    op.create_table(
        "jobs",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("job_type", sa.String(64), nullable=False),
        # Phase 2 job types: "summarize", "extract_facts", "embed", "index_fts", "dedup"
        sa.Column("raw_archive_id", sa.UUID(as_uuid=True), sa.ForeignKey("raw_archive.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="'pending'"),
        # "pending", "claimed", "completed", "failed", "retryable_failed"
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer, nullable=False, server_default="3"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("claimed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    # Composite index for SKIP LOCKED polling (Pitfall 9 prevention)
    op.create_index("ix_jobs_status_created_at", "jobs", ["status", "created_at"])
    op.create_index("ix_jobs_raw_archive_id", "jobs", ["raw_archive_id"])

    # ── audit_events table ─────────────────────────────────────────────────
    # Append-only event log. Must be persisted to DB from day one (see PITFALLS.md
    # technical debt patterns: "Store audit events in application memory" — NEVER).
    op.create_table(
        "audit_events",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("event_type", sa.String(64), nullable=False),
        # "ingest", "archive_read", "settings_update", "key_validation", "delete"
        sa.Column("raw_archive_id", sa.UUID(as_uuid=True), nullable=True),
        # FK to raw_archive (nullable for non-archive events like settings_update)
        sa.Column("actor", sa.String(64), nullable=False, server_default="'user_ui'"),
        # "user_ui", "mcp_client", "worker", "system"
        sa.Column("operation_metadata", sa.JSON, nullable=True),
        # Structured details: source_type, conversation_count, etc.
        sa.Column("occurred_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_audit_events_occurred_at", "audit_events", ["occurred_at"])
    op.create_index("ix_audit_events_event_type", "audit_events", ["event_type"])
    op.create_index("ix_audit_events_raw_archive_id", "audit_events", ["raw_archive_id"],
                    postgresql_where=sa.text("raw_archive_id IS NOT NULL"))


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("jobs")
    op.drop_table("settings")
    op.drop_table("raw_archive")
    op.execute("DROP TYPE IF EXISTS source_status")
    op.execute("DROP EXTENSION IF EXISTS vector")
```

Also create `backend/app/infrastructure/` directory and its `__init__.py`, and create the stub `backend/app/infrastructure/db.py` that defines `Base` (required by alembic/env.py):

```python
# backend/app/infrastructure/db.py
"""SQLAlchemy async engine, session factory, and declarative Base.

All SQLAlchemy ORM models must inherit from Base defined here.
"""
from __future__ import annotations

import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


_engine = None
_async_session_factory = None


def get_database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set. "
            "Copy .env.sample to .env and configure it."
        )
    return url


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            get_database_url(),
            echo=os.environ.get("APP_ENV") == "development",
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
    return _engine


def get_session_factory():
    global _async_session_factory
    if _async_session_factory is None:
        _async_session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields an async DB session per request."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

Create stub `__init__.py` files for:
- `backend/app/__init__.py` (empty)
- `backend/app/infrastructure/__init__.py` (empty)
- `backend/alembic/__init__.py` (empty)
  </action>
  <acceptance_criteria>
    - `grep -n "CREATE EXTENSION IF NOT EXISTS vector" backend/alembic/versions/0001_initial.py` returns 1 line
    - `grep -n "source_status.*ENUM.*active.*source_removed" backend/alembic/versions/0001_initial.py` returns 1 line
    - `grep -n "deleted_at" backend/alembic/versions/0001_initial.py` returns ≥ 2 lines (column def + comment)
    - `grep -n "openai_key_fingerprint.*String(4)" backend/alembic/versions/0001_initial.py` returns 1 line
    - `grep -n "_key.*String\|_secret\|_token" backend/alembic/versions/0001_initial.py` returns 0 lines except fingerprint columns (4-char max)
    - `grep -n "ix_jobs_status_created_at" backend/alembic/versions/0001_initial.py` returns 1 line
    - `grep -n "audit_events" backend/alembic/versions/0001_initial.py` returns ≥ 3 lines
    - `grep -n "gen_random_uuid" backend/alembic/versions/0001_initial.py` returns ≥ 3 lines (UUIDs for raw_archive, jobs, audit_events)
    - `grep -n "class Base" backend/app/infrastructure/db.py` returns 1 line
    - `grep -n "create_async_engine" backend/app/infrastructure/db.py` returns 1 line
  </acceptance_criteria>
</task>

</tasks>

<verification>
After all tasks complete, run these checks from the `backend/` directory (or via Docker):

1. `python3 -c "import tomllib; tomllib.load(open('pyproject.toml','rb')); print('TOML valid')"` — exits 0
2. `grep -c "fastapi==0.135.1\|asyncpg==0.31.0\|sqlalchemy==2.0.48\|alembic==1.18.4" pyproject.toml` — returns 4
3. `grep "openai_key\|anthropic_key\|ollama_key" alembic/versions/0001_initial.py | grep -v fingerprint | grep -v configured | grep -v validation | grep -v validated` — returns 0 lines (no plaintext key columns)
4. Via Docker (after plan 01-01 is done): `docker compose run --rm recalium-app alembic -c backend/alembic.ini upgrade head` — must complete without error
5. Via Docker: `docker compose exec recalium-postgres psql -U recalium -d recalium -c "\dt"` — must show tables: raw_archive, settings, jobs, audit_events
6. Via Docker: `docker compose exec recalium-postgres psql -U recalium -d recalium -c "SELECT * FROM pg_extension WHERE extname='vector'"` — returns 1 row
</verification>

<must_haves>
1. The `settings` table contains zero columns named `*_key` or `*_secret` that hold full-length credentials — only `*_key_fingerprint` (String(4)) and `*_key_configured` (Boolean). Verified: `grep "_key.*String\|_secret\|_token" backend/alembic/versions/0001_initial.py | grep -v fingerprint | grep -v configured | grep -v validation | grep -v validated` returns 0 lines.
2. `raw_archive.deleted_at` column exists as `TIMESTAMP NULL` and code comment states "All read queries MUST filter WHERE deleted_at IS NULL". Verified: `grep "deleted_at.*TIMESTAMP" backend/alembic/versions/0001_initial.py` returns 1 line.
3. `source_status ENUM('active', 'source_removed')` type is created in migration 0001, before any derived tables are added in future migrations. Verified: `grep "CREATE TYPE source_status" backend/alembic/versions/0001_initial.py` returns 1 line.
</must_haves>
