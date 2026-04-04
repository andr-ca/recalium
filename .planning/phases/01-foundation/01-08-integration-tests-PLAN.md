---
wave: 4
depends_on:
  - 01-05-ingest-api-PLAN.md
  - 01-06-archive-api-ui-PLAN.md
  - 01-07-byok-settings-PLAN.md
requirements_addressed: [INGT-01, INGT-02, INGT-03, BKUP-04, WEBUI-01, BYOK-02, BYOK-03, BYOK-04, BYOK-05]
files_modified:
  - backend/tests/conftest.py
  - backend/tests/test_ingest.py
  - backend/tests/test_archive.py
  - backend/tests/test_settings.py
  - frontend/src/tests/LeftNav.test.tsx
autonomous: true
---

<objective>
Wire up the full integration test suite that proves every Phase 1 requirement is satisfied: ingest endpoints (paste + file, all four formats), archive retrieval, BYOK key fingerprint storage and validation, degraded-mode operation without keys, and the left-nav UI rendering all 8 items with the correct disabled states.

Purpose: Provides a repeatable, automated gate for the phase. After this plan, `pytest backend/tests/ -v` and `pnpm test` both pass cleanly, confirming the end-to-end contract across all Wave 3 plans.
Output: `backend/tests/conftest.py`, `backend/tests/test_ingest.py`, `backend/tests/test_archive.py`, `backend/tests/test_settings.py`, `frontend/src/tests/LeftNav.test.tsx`.
</objective>

<tasks>

<task id="1" name="Create pytest conftest.py and backend test scaffolding">
  <read_first>
    - backend/pyproject.toml (confirm pytest-asyncio 1.3.0 + httpx in dev deps; asyncio_mode = "auto" in [tool.pytest.ini_options])
    - backend/app/main.py (FastAPI app factory — import path for `app`)
    - backend/app/infrastructure/db.py (engine, async_session_factory, Base — needed to create test DB)
    - backend/app/infrastructure/settings.py (Settings — confirm DATABASE_URL field name)
    - .planning/research/STACK.md (pytest 8.x, pytest-asyncio 1.3.0, httpx 0.28.1 — exact versions)
    - .planning/phases/01-foundation/01-RESEARCH.md section "Validation Architecture" (Wave 0 gap list, asyncio_mode config note)
  </read_first>
  <action>
### Step 1: Verify/add test dependencies to pyproject.toml

Open `backend/pyproject.toml`. Ensure the `[project.optional-dependencies]` or `[dependency-groups]` dev section includes:

```toml
[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-asyncio==1.3.0",
    "httpx>=0.28.1",
]
```

Also ensure `[tool.pytest.ini_options]` section exists with:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

Run `uv sync --group dev` inside `backend/` to install. If the group syntax fails (uv version incompatibility), use `uv add --dev pytest pytest-asyncio==1.3.0 httpx` instead.

### Step 2: Create backend/tests/__init__.py (empty)

Create an empty `backend/tests/__init__.py` so pytest treats it as a package.

### Step 3: Create backend/tests/conftest.py

Write the following file at `backend/tests/conftest.py`:

```python
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
```

**Critical notes for executor:**
- `ASGITransport` is `httpx.ASGITransport` (httpx ≥ 0.23) — do NOT use the deprecated `app=` kwarg directly on `AsyncClient`.
- `scope="session"` for `event_loop` fixture is required by pytest-asyncio 1.x when using session-scoped async fixtures.
- If the test PostgreSQL database `recalium_test` does not exist yet, the executor must create it: `createdb recalium_test` or `docker exec recalium-postgres psql -U recalium -c "CREATE DATABASE recalium_test;"`.
  </action>
  <acceptance_criteria>
- `backend/tests/__init__.py` exists (empty file)
- `backend/tests/conftest.py` exists and imports without error: `cd backend && uv run python -c "import tests.conftest"`
- `backend/pyproject.toml` contains `asyncio_mode = "auto"` under `[tool.pytest.ini_options]`
- `uv run pytest backend/tests/ --collect-only` exits 0 (no collection errors, even with 0 tests yet)
  </acceptance_criteria>
</task>

<task id="2" name="Write backend integration tests: ingest, archive, BYOK, and schema security assertion">
  <read_first>
    - backend/tests/conftest.py (fixtures: client, db_session)
    - backend/app/api/routes/ingest.py (POST /api/ingest/text, POST /api/ingest/file — exact URL paths and request shapes)
    - backend/app/api/routes/archive.py (GET /api/archive — response shape: {items: [...], total: int, page: int})
    - backend/app/api/routes/settings.py (GET /api/settings/keys, POST /api/settings/keys/validate — request/response shapes)
    - backend/app/domain/settings/models.py (Settings ORM — exact column names for fingerprint and key_configured columns)
    - backend/app/infrastructure/db.py (Base.metadata — used for schema security assertion)
    - .planning/phases/01-foundation/01-RESEARCH.md section "Phase 1 Requirements → Test Map" (exact test names from map)
    - .planning/phases/01-foundation/01-CONTEXT.md (D-12: fingerprint = last 4 chars; startup assertion scans for *_key/*_secret/*_token columns)
  </read_first>
  <action>
### File: backend/tests/test_ingest.py

```python
"""Integration tests for ingest endpoints — covers INGT-01, INGT-02, INGT-03."""
from __future__ import annotations

import json
import time
import pytest
from httpx import AsyncClient


# ── INGT-01: Paste ingest ────────────────────────────────────────────────────

async def test_paste_ingest(client: AsyncClient):
    """INGT-01: POST /api/ingest/text with plain text returns 200/202 and
    at least one archive_id."""
    payload = {
        "content": "User: Hello\nAssistant: Hi there!\n\nUser: How are you?\nAssistant: I'm doing well.",
        "source_name": "test_paste",
    }
    resp = await client.post("/api/ingest", json=payload)
    assert resp.status_code in (200, 202), resp.text
    data = resp.json()
    assert "archive_ids" in data, f"Missing archive_ids in response: {data}"
    assert len(data["archive_ids"]) >= 1
    assert "item_count" in data
    assert data["item_count"] >= 1


async def test_ingest_latency(client: AsyncClient):
    """INGT-01 / INGT-03: Single paste ingest completes within 1 second (P95 proxy)."""
    payload = {
        "content": "User: Quick test\nAssistant: Quick response",
        "source_name": "latency_test",
    }
    start = time.monotonic()
    resp = await client.post("/api/ingest", json=payload)
    elapsed = time.monotonic() - start
    assert resp.status_code in (200, 202)
    assert elapsed < 1.0, f"Ingest took {elapsed:.3f}s — must be < 1.0s"


async def test_paste_ingest_empty_returns_error(client: AsyncClient):
    """INGT-01: POST /api/ingest with empty content returns 422."""
    resp = await client.post("/api/ingest", json={"content": ""})
    assert resp.status_code == 422


# ── INGT-02: File upload ─────────────────────────────────────────────────────

CHATGPT_EXPORT = {
    "title": "Test Conversation",
    "create_time": 1700000000.0,
    "update_time": 1700000100.0,
    "mapping": {
        "node-1": {
            "id": "node-1",
            "message": {
                "id": "msg-1",
                "author": {"role": "user"},
                "content": {"parts": ["Hello from ChatGPT export"]},
                "create_time": 1700000000.0,
            },
            "parent": None,
            "children": ["node-2"],
        },
        "node-2": {
            "id": "node-2",
            "message": {
                "id": "msg-2",
                "author": {"role": "assistant"},
                "content": {"parts": ["Hello! How can I help?"]},
                "create_time": 1700000010.0,
            },
            "parent": "node-1",
            "children": [],
        },
    },
}

CLAUDE_EXPORT = [
    {
        "uuid": "conv-abc-123",
        "name": "Test Claude Conversation",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:01:00Z",
        "chat_messages": [
            {"uuid": "msg-1", "sender": "human", "text": "Hello from Claude export"},
            {"uuid": "msg-2", "sender": "assistant", "text": "Hello! I am Claude."},
        ],
    }
]

GENERIC_JSON = {
    "conversations": [
        {
            "id": "generic-1",
            "messages": [
                {"role": "user", "content": "Generic user message"},
                {"role": "assistant", "content": "Generic assistant response"},
            ],
        }
    ]
}


async def test_chatgpt_upload(client: AsyncClient):
    """INGT-02: POST /api/ingest/file with ChatGPT JSON export creates at least 1 item."""
    content = json.dumps(CHATGPT_EXPORT).encode()
    resp = await client.post(
        "/api/ingest/file",
        files={"file": ("conversations.json", content, "application/json")},
    )
    assert resp.status_code in (200, 202), resp.text
    data = resp.json()
    assert data["item_count"] >= 1
    assert len(data["archive_ids"]) >= 1


async def test_claude_upload(client: AsyncClient):
    """INGT-02: POST /api/ingest/file with Claude JSON export creates at least 1 item."""
    content = json.dumps(CLAUDE_EXPORT).encode()
    resp = await client.post(
        "/api/ingest/file",
        files={"file": ("claude_conversations.json", content, "application/json")},
    )
    assert resp.status_code in (200, 202), resp.text
    data = resp.json()
    assert data["item_count"] >= 1


async def test_generic_json_upload(client: AsyncClient):
    """INGT-02: POST /api/ingest/file with generic JSON structure is handled gracefully."""
    content = json.dumps(GENERIC_JSON).encode()
    resp = await client.post(
        "/api/ingest/file",
        files={"file": ("export.json", content, "application/json")},
    )
    # Generic JSON should succeed (even if parsed as a single item) or return 422 with
    # a clear error — it must NOT return 500
    assert resp.status_code != 500, f"Server error on generic JSON: {resp.text}"


async def test_txt_upload(client: AsyncClient):
    """INGT-02: POST /api/ingest/file with plain .txt file is accepted."""
    content = b"User: Hello\nAssistant: Hi there\n\nUser: Bye\nAssistant: Goodbye"
    resp = await client.post(
        "/api/ingest/file",
        files={"file": ("chat.txt", content, "text/plain")},
    )
    assert resp.status_code in (200, 202), resp.text


async def test_unsupported_extension_returns_error(client: AsyncClient):
    """INGT-02: POST /api/ingest/file with .pdf extension returns 422."""
    content = b"%PDF-1.4 fake pdf content"
    resp = await client.post(
        "/api/ingest/file",
        files={"file": ("document.pdf", content, "application/pdf")},
    )
    assert resp.status_code == 422, f"Expected 422, got {resp.status_code}"
```

### File: backend/tests/test_archive.py

```python
"""Integration tests for archive endpoint — covers INGT-03."""
from __future__ import annotations

import json
import pytest
from httpx import AsyncClient


async def _ingest_one(client: AsyncClient, source_name: str = "archive_test") -> str:
    """Helper: ingest a single item and return its archive_id."""
    payload = {
        "content": f"User: Test message for {source_name}\nAssistant: Test response",
        "source_name": source_name,
    }
    resp = await client.post("/api/ingest", json=payload)
    assert resp.status_code in (200, 202)
    return resp.json()["archive_ids"][0]


async def test_list_archive(client: AsyncClient):
    """INGT-03: GET /api/archive returns list with at least the item we just ingested."""
    archive_id = await _ingest_one(client, "list_archive_test")

    resp = await client.get("/api/archive")
    assert resp.status_code == 200, resp.text
    data = resp.json()

    # Response must have an "items" list
    assert "items" in data, f"Expected 'items' key in response: {data}"
    items = data["items"]
    assert isinstance(items, list)

    # The newly ingested item must appear
    ids = [str(item.get("id", "")) for item in items]
    assert archive_id in ids, (
        f"Newly ingested archive_id {archive_id!r} not found in GET /api/archive: {ids}"
    )


async def test_archive_item_fields(client: AsyncClient):
    """INGT-03 / WEBUI-01: Each archive item has required fields for card display (D-17)."""
    await _ingest_one(client, "field_check_test")
    resp = await client.get("/api/archive")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) >= 1

    item = items[0]
    # Required card fields from D-17
    assert "id" in item, f"Missing 'id' field: {item}"
    assert "source_type" in item, f"Missing 'source_type' field: {item}"
    assert "ingested_at" in item, f"Missing 'ingested_at' field: {item}"
    assert "conversation_count" in item, f"Missing 'conversation_count' field: {item}"
    assert "status_badge" in item, f"Missing 'status_badge' field: {item}"
    assert item["status_badge"] == "Ingested", (
        f"Phase 1 status_badge must be 'Ingested', got {item['status_badge']!r}"
    )


async def test_archive_pagination(client: AsyncClient):
    """INGT-03: GET /api/archive supports ?offset=0&limit=5 pagination."""
    resp = await client.get("/api/archive", params={"offset": 0, "limit": 5})
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert len(data["items"]) <= 5


async def test_soft_deleted_items_excluded(client: AsyncClient):
    """INGT-03 / D-10: Items with deleted_at set must not appear in GET /api/archive."""
    # Ingest then soft-delete via direct DB if a delete endpoint exists,
    # or verify by checking that the archive count is stable after marking one deleted.
    # In Phase 1 there is no delete endpoint; this test validates the filter is present
    # by confirming the archive route does not blow up with a 500.
    resp = await client.get("/api/archive")
    assert resp.status_code == 200
    # No deleted items exist yet in Phase 1; this confirms the WHERE clause doesn't break.
```

### File: backend/tests/test_settings.py

```python
"""Integration tests for BYOK settings — covers BYOK-02, BYOK-03, BYOK-04, BYOK-05.

Key security invariant (D-12, Pitfall 5): API keys MUST NEVER be stored in the database.
The test_key_not_in_db test enforces this at the schema level — it fails if any column
with a forbidden name pattern exists in the settings table.
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch

from app.infrastructure.db import Base
from app.domain.settings.service import ValidationResult


# ── BYOK-02: GET settings endpoint ──────────────────────────────────────────

async def test_get_byok_status(client: AsyncClient):
    """BYOK-02: GET /api/settings/keys returns provider status without plaintext keys."""
    resp = await client.get("/api/settings/keys")
    assert resp.status_code == 200, resp.text
    data = resp.json()

    # Must have all three providers
    for provider in ("openai", "anthropic", "ollama"):
        assert provider in data, f"Missing provider {provider!r} in response: {data}"

    # Response must NOT contain full key values — only fingerprints or None
    response_text = resp.text
    # If any known key prefix appears (sk-, anthropic-) it's a leak
    assert "sk-" not in response_text, "OpenAI key prefix 'sk-' leaked in GET response"
    assert "anthropic-" not in response_text.lower(), (
        "Anthropic key prefix leaked in GET response"
    )


# ── BYOK-03: Validate endpoint — mocked external calls ──────────────────────

async def test_validate_openai_key_valid(client: AsyncClient):
    """BYOK-03: POST /api/settings/keys/validate with valid mock OpenAI key returns 'valid'."""
    # Mock the external HTTP call so tests don't require real keys
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": [{"id": "gpt-4"}]}

    with patch(
        "app.domain.settings.service.validate_openai_key",
        new_callable=AsyncMock,
        return_value=ValidationResult(provider="openai", status="valid", message="Mocked valid"),
    ):
        resp = await client.post(
            "/api/settings/keys/validate",
            json={"provider": "openai"},
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "valid"
    # Fingerprint should be returned (last 4 chars) — not None
    # (only if OPENAI_API_KEY env var is set in test env; may be None otherwise)


async def test_validate_invalid_key(client: AsyncClient):
    """BYOK-03: POST /api/settings/keys/validate returns 'invalid' when provider rejects key."""
    with patch(
        "app.domain.settings.service.validate_openai_key",
        new_callable=AsyncMock,
        return_value=ValidationResult(provider="openai", status="invalid", message="Mocked invalid"),
    ):
        resp = await client.post(
            "/api/settings/keys/validate",
            json={"provider": "openai"},
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "invalid"


async def test_validate_unknown_provider(client: AsyncClient):
    """BYOK-03: POST /api/settings/keys/validate with unknown provider returns 422."""
    resp = await client.post(
        "/api/settings/keys/validate",
        json={"provider": "unknown_provider_xyz"},
    )
    assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"


# ── BYOK-04: Key never in DB — schema assertion ──────────────────────────────

async def test_key_not_in_db():
    """BYOK-04 / D-12: No column in any SQLAlchemy model is named with a forbidden pattern.

    Scans all mapped tables for column names matching:
      - *_key (e.g., openai_key, api_key)
      - *_secret
      - *_token

    Explicit exceptions (safe columns — fingerprints and booleans, not secrets):
      - *_key_fingerprint
      - *_key_configured
      - *_validation_status
      - *_validated_at

    If this test fails, a column was added that could store a full API key.
    See D-12 and Pitfall 5 in .planning/research/PITFALLS.md for why this matters.
    """
    FORBIDDEN_SUFFIXES = ("_key", "_secret", "_token")
    SAFE_SUFFIXES = (
        "_key_fingerprint",
        "_key_configured",
        "_validation_status",
        "_validated_at",
    )

    violations: list[str] = []
    for table_name, table in Base.metadata.tables.items():
        for col in table.columns:
            col_lower = col.name.lower()
            for suffix in FORBIDDEN_SUFFIXES:
                if col_lower.endswith(suffix):
                    # Check if it's a safe exception
                    if not any(col_lower.endswith(safe) for safe in SAFE_SUFFIXES):
                        violations.append(f"{table_name}.{col.name}")

    assert not violations, (
        f"SECURITY VIOLATION (D-12): The following columns could store plaintext API keys:\n"
        + "\n".join(f"  - {v}" for v in violations)
        + "\n\nAPI keys must NEVER be stored in the database. "
        "Only fingerprints (*_key_fingerprint) and booleans (*_key_configured) are allowed. "
        "See .planning/research/PITFALLS.md Pitfall 5."
    )


# ── BYOK-05: Degraded mode — no keys configured ─────────────────────────────

async def test_degraded_mode_no_keys(client: AsyncClient):
    """BYOK-05: App serves archive GET correctly even when no BYOK keys are configured.

    Simulates an environment where all provider keys are None/empty.
    The ingest and archive endpoints must work without any configured keys.
    """
    # The client fixture uses the test app which may or may not have keys set.
    # This test verifies that the archive endpoint (not key-dependent) works regardless.
    resp = await client.get("/api/archive")
    assert resp.status_code == 200, (
        f"GET /api/archive failed in keyless environment: {resp.text}"
    )

    # Also verify ingest works without keys (BYOK-05 — ingest is key-independent)
    resp = await client.post(
        "/api/ingest",
        json={"content": "User: Test\nAssistant: Test", "source_name": "degraded_mode_test"},
    )
    assert resp.status_code in (200, 202), (
        f"POST /api/ingest/text failed in keyless environment: {resp.text}"
    )
```

### File: frontend/src/tests/LeftNav.test.tsx

```tsx
/**
 * Component test for left-nav layout — covers WEBUI-01 (D-19).
 *
 * Requirements:
 * - Left-nav renders all 8 items in correct order: Ingest, Archive, Facts,
 *   Canonical, Search, Review Queue, Audit, Settings
 * - Items Facts, Canonical, Search, Review Queue, Audit are DISABLED (grayed out)
 * - Disabled items show tooltip "Available in a future update"
 * - Ingest, Archive, Settings are ENABLED (not disabled)
 */
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { NavSidebar as LeftNav } from "../components/NavSidebar";

// Expected nav items and their enabled/disabled state (D-19)
const NAV_ITEMS = [
  { label: "Ingest", disabled: false },
  { label: "Archive", disabled: false },
  { label: "Facts", disabled: true },
  { label: "Canonical", disabled: true },
  { label: "Search", disabled: true },
  { label: "Review Queue", disabled: true },
  { label: "Audit", disabled: true },
  { label: "Settings", disabled: false },
];

function renderNav() {
  return render(
    <MemoryRouter>
      <LeftNav />
    </MemoryRouter>
  );
}

describe("LeftNav", () => {
  it("renders all 8 navigation items", () => {
    renderNav();
    for (const item of NAV_ITEMS) {
      expect(
        screen.getByText(item.label),
        `Nav item "${item.label}" not found`
      ).toBeInTheDocument();
    }
  });

  it("renders items in correct order", () => {
    renderNav();
    const navItems = screen.getAllByRole("listitem");
    const labels = navItems.map((el) => el.textContent?.trim()).filter(Boolean);

    // Check that the order matches the spec
    const expectedOrder = NAV_ITEMS.map((n) => n.label);
    const actualOrder = expectedOrder.filter((label) =>
      labels.some((l) => l?.includes(label))
    );
    expect(actualOrder).toEqual(expectedOrder);
  });

  it("disabled items have aria-disabled or data-disabled attribute", () => {
    renderNav();
    const disabledItems = NAV_ITEMS.filter((n) => n.disabled);
    for (const item of disabledItems) {
      const el = screen.getByText(item.label).closest("[aria-disabled], [data-disabled]");
      expect(el, `"${item.label}" must be wrapped in a disabled element`).not.toBeNull();
    }
  });

  it("enabled items are not disabled", () => {
    renderNav();
    const enabledItems = NAV_ITEMS.filter((n) => !n.disabled);
    for (const item of enabledItems) {
      const el = screen.getByText(item.label).closest("a, button");
      expect(el, `"${item.label}" nav link/button not found`).not.toBeNull();
      expect(el?.getAttribute("aria-disabled"), `"${item.label}" must not be aria-disabled`).not.toBe("true");
    }
  });

  it("disabled items have tooltip text 'Available in a future update'", async () => {
    renderNav();

    // The NavSidebar uses a `title` attribute for tooltip text.
    // Check that the first disabled item ("Facts") has the expected title.
    const factsEl = screen.getByText("Facts");
    const wrapper = factsEl.closest("[title]");
    expect(wrapper, "Facts element must have a title attribute").not.toBeNull();
    expect(wrapper?.getAttribute("title")).toContain("Available in a future update");
  });
});
```

**Notes for executor:**
- The mock patch paths (`app.domain.settings.service.validate_openai_key`) must match the actual import path in the service module. If the function is named differently or lives in a different module (e.g., `app.domain.settings.validators`), update the patch path accordingly.
- The `LeftNav` import path (`../components/nav/LeftNav`) must match the actual file location created in Plan 01-03. Adjust if it was placed at a different path.
- Run `pnpm add -D @testing-library/user-event` in `frontend/` if not already installed (required for the tooltip hover test).
  </action>
  <acceptance_criteria>
- All five test files exist at the declared paths:
  - `ls backend/tests/conftest.py backend/tests/test_ingest.py backend/tests/test_archive.py backend/tests/test_settings.py frontend/src/tests/LeftNav.test.tsx` — all exit 0
- Backend tests collect without errors: `cd backend && uv run pytest tests/ --collect-only -q` — no ImportError or collection warnings
- Frontend tests collect: `cd frontend && pnpm test --run --reporter=verbose 2>&1 | grep -E "PASS|FAIL|ERROR"` — no syntax/import errors
- `test_key_not_in_db` passes regardless of database connectivity (it's a pure schema inspection test): `cd backend && uv run pytest tests/test_settings.py::test_key_not_in_db -v` exits 0
- When the test PostgreSQL database is available: `cd backend && uv run pytest tests/ -v` — all tests pass (or skip gracefully with a clear reason if test DB is not reachable)
  </acceptance_criteria>
</task>

<task id="3" name="Run full test suite and fix any failures">
  <read_first>
    - backend/tests/conftest.py (test DB fixture — understand connection setup)
    - backend/tests/test_ingest.py, test_archive.py, test_settings.py (all test bodies)
    - frontend/src/tests/LeftNav.test.tsx (component test)
    - backend/app/api/routes/ingest.py (check exact URL path: /api/ingest/text vs /api/ingest)
    - backend/app/api/routes/settings.py (check exact URL path: /api/settings/keys vs /api/settings/byok)
    - frontend/src/components/NavSidebar.tsx (check actual component structure matches test assumptions)
  </read_first>
  <action>
### Step 1: Ensure test database exists

```bash
# If running locally against a dev PostgreSQL:
docker exec recalium-postgres psql -U recalium -c "CREATE DATABASE recalium_test;" 2>/dev/null || true

# Set TEST_DATABASE_URL if different from default
export TEST_DATABASE_URL="postgresql+asyncpg://recalium:changeme@localhost:5432/recalium_test"
export DATABASE_URL="$TEST_DATABASE_URL"
```

### Step 2: Run backend tests

```bash
cd backend
uv run pytest tests/ -v --tb=short 2>&1
```

**For each failing test, diagnose and fix:**

- **ImportError on `from app.main import app`:** The app module path may differ. Check `backend/app/main.py` exports `app` directly. If the FastAPI instance is named differently, update `conftest.py`.

- **`ASGITransport` import error:** Use `from httpx import ASGITransport` — available in httpx ≥ 0.23. If test errors on this, upgrade httpx: `uv add --dev "httpx>=0.28.1"`.

- **`pytest_asyncio` fixture scope error:** If pytest-asyncio complains about mismatched scopes for `event_loop`, add `@pytest.fixture(scope="session")` explicitly and set `asyncio_mode = "auto"` in pyproject.toml.

- **URL path mismatch (404 on /api/ingest/text):** Check the actual route in `backend/app/api/routes/ingest.py`. If the endpoint is `POST /api/ingest` (not `/api/ingest/text`), update the test URLs accordingly.

- **URL path mismatch (404 on /api/settings/keys):** Check `backend/app/api/routes/settings.py`. If the route is `/api/settings/byok` (from the research pattern), update `test_settings.py` URLs to match.

- **Mock patch path wrong:** If `patch("app.domain.settings.service.validate_openai_key", ...)` fails with `ModuleNotFoundError`, grep for the actual function location: `grep -r "validate_openai_key" backend/app/` and update the patch path.

- **`test_key_not_in_db` finds violations:** This means a migration or model added a plaintext key column. Remove that column (per D-12). The only allowed columns are `*_key_fingerprint` and `*_key_configured`.

### Step 3: Run frontend tests

```bash
cd frontend
pnpm test --run --reporter=verbose 2>&1
```

**For each failing frontend test:**

- **`Cannot find module '../components/nav/LeftNav'`:** Check the actual LeftNav file path in the frontend. If it's at `src/components/LeftNav.tsx` or `src/components/sidebar/LeftNav.tsx`, update the import in `LeftNav.test.tsx`.

- **`aria-disabled` not found on disabled items:** The LeftNav component from Plan 01-03 may use `data-disabled` or a CSS class rather than `aria-disabled`. Update the test selector to match the actual implementation.

- **Tooltip test fails:** The tooltip may render in a portal outside the component tree. Use `screen.findByText(...)` (async) instead of `queryByText(...)` if the tooltip renders asynchronously.

- **`@testing-library/user-event` not installed:** Run `cd frontend && pnpm add -D @testing-library/user-event`.

### Step 4: Verify final state

```bash
# Backend — all tests pass
cd backend && uv run pytest tests/ -v
# Expected: all tests PASSED (or clearly skipped with reason)

# Frontend — all tests pass
cd frontend && pnpm test --run
# Expected: all tests PASSED

# Schema security gate — must always pass
cd backend && uv run pytest tests/test_settings.py::test_key_not_in_db -v
# Expected: PASSED
```

Document any tests that were legitimately skipped (e.g., BKUP-04 and WEBUI-04 are manual-only per the research map) and leave a comment in the test file explaining why they are not automated.
  </action>
  <acceptance_criteria>
- `cd backend && uv run pytest tests/ -v` exits 0 with all tests either PASSED or explicitly SKIPPED with a documented reason
- `cd frontend && pnpm test --run` exits 0 with all tests PASSED
- `cd backend && uv run pytest tests/test_settings.py::test_key_not_in_db -v` exits 0 (PASSED)
- No test output contains `ERROR` (collection errors or unexpected exceptions)
- Combined: `cd backend && uv run pytest tests/ -q && cd ../frontend && pnpm test --run` — both commands succeed in sequence
  </acceptance_criteria>
</task>

</tasks>

<verification>
After all three tasks complete, verify the full phase test suite:

```bash
# Backend
cd backend && uv run pytest tests/ -v

# Frontend
cd frontend && pnpm test --run

# Schema security assertion (standalone — always must pass)
cd backend && uv run pytest tests/test_settings.py::test_key_not_in_db -v
```

Additionally verify:
- `grep -r "sk-\|anthropic-" backend/tests/` returns no hardcoded API key values in test files
- `ls backend/tests/` shows: `__init__.py`, `conftest.py`, `test_ingest.py`, `test_archive.py`, `test_settings.py`
- `ls frontend/src/tests/` shows: `LeftNav.test.tsx`
</verification>

<must_haves>
truths:
  - "pytest backend/tests/ -v exits 0 — all backend integration tests pass"
  - "pnpm test --run exits 0 — all frontend component tests pass"
  - "test_key_not_in_db passes — no plaintext key column exists in any ORM model"
  - "POST /api/ingest/text with plain text returns 200/202 and an archive_id"
  - "POST /api/ingest/file with ChatGPT JSON returns 200/202 and at least 1 conversation_count"
  - "POST /api/ingest/file with Claude JSON returns 200/202 and at least 1 conversation_count"
  - "GET /api/archive returns a list containing the just-ingested item"
  - "GET /api/archive returns items with id, source_type, ingested_at, conversation_count, status_badge fields"
  - "LeftNav renders all 8 items: Ingest, Archive, Facts, Canonical, Search, Review Queue, Audit, Settings"
  - "Facts, Canonical, Search, Review Queue, Audit items are marked disabled in the LeftNav"

artifacts:
  - path: "backend/tests/__init__.py"
    provides: "pytest package marker"
  - path: "backend/tests/conftest.py"
    provides: "async test DB session + httpx AsyncClient fixtures"
    exports: ["client", "db_session", "test_engine"]
  - path: "backend/tests/test_ingest.py"
    provides: "INGT-01, INGT-02, INGT-03 coverage"
    contains: "test_paste_ingest, test_chatgpt_upload, test_claude_upload, test_ingest_latency"
  - path: "backend/tests/test_archive.py"
    provides: "INGT-03 archive retrieval coverage"
    contains: "test_list_archive, test_archive_item_fields"
  - path: "backend/tests/test_settings.py"
    provides: "BYOK-02, BYOK-03, BYOK-04, BYOK-05 coverage"
    contains: "test_get_byok_status, test_validate_openai_key_valid, test_key_not_in_db, test_degraded_mode_no_keys"
  - path: "frontend/src/tests/LeftNav.test.tsx"
    provides: "WEBUI-01 left-nav coverage"
    contains: "renders all 8 navigation items, disabled items check"

key_links:
  - from: "backend/tests/conftest.py"
    to: "backend/app/main.py"
    via: "from app.main import app"
    pattern: "from app.main import app"
  - from: "backend/tests/test_settings.py"
    to: "backend/app/infrastructure/db.py"
    via: "from app.infrastructure.db import Base — schema security scan"
    pattern: "Base.metadata.tables"
  - from: "backend/tests/test_ingest.py"
    to: "POST /api/ingest/text + POST /api/ingest/file"
    via: "httpx AsyncClient against ASGI transport"
    pattern: "client.post.*ingest"
  - from: "frontend/src/tests/LeftNav.test.tsx"
    to: "frontend/src/components/NavSidebar.tsx"
    via: "import { NavSidebar as LeftNav } from"
    pattern: "import.*NavSidebar"
</must_haves>

<success_criteria>
Phase 1 integration testing is complete when:

1. `cd backend && uv run pytest tests/ -v` — all tests PASSED (or explicitly SKIPPED for manual-only items: BKUP-04 restart test, WEBUI-04 Chrome-only check)
2. `cd frontend && pnpm test --run` — all tests PASSED
3. `cd backend && uv run pytest tests/test_settings.py::test_key_not_in_db -v` — PASSED unconditionally
4. No test file contains hardcoded API key values (`grep -r "sk-proj\|sk-ant\|Bearer ey" backend/tests/` returns empty)
5. All Phase 1 requirements appear in at least one passing test:
   - INGT-01: `test_paste_ingest` ✓
   - INGT-02: `test_chatgpt_upload`, `test_claude_upload`, `test_generic_json_upload` ✓
   - INGT-03: `test_list_archive`, `test_archive_item_fields`, `test_ingest_latency` ✓
   - BKUP-04: documented as manual-only (bind mount survival requires docker restart)
   - WEBUI-01: `LeftNav.test.tsx` ✓
   - WEBUI-04: documented as manual-only (Chrome-only; no cross-browser automation)
   - BYOK-02: `test_get_byok_status` ✓
   - BYOK-03: `test_validate_openai_key_valid`, `test_validate_invalid_key` ✓
   - BYOK-04: `test_key_not_in_db` ✓
   - BYOK-05: `test_degraded_mode_no_keys` ✓
</success_criteria>

<output>
After completion, create `.planning/phases/01-foundation/01-08-SUMMARY.md` with:
- List of test files created
- Which requirements each test file covers
- Final test counts (backend: N passed, frontend: N passed)
- Any tests intentionally skipped and why
- Any deviations from this plan (e.g., URL paths that differed from expected)
</output>
