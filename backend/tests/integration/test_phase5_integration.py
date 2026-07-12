"""Phase 5 integration test suite.

Covers all 4 Phase 5 requirement IDs:
  INGT-04: Watched import folder
  INGT-05: MCP ingest endpoint (content acceptance and queuing)
  MCP-02:  MCP ingest — reject missing required fields with descriptive error
  PORT-01: JSON export/import via open memory bundle format

Run with:
    cd backend && uv run python3 -m pytest tests/integration/test_phase5_integration.py -v
"""
from __future__ import annotations

import hashlib
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import patch

import pytest

pytest.importorskip("app.domain.ingest.watcher")
pytest.importorskip("app.api.routes.portability")

from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.archive.models import RawArchiveItem
from app.domain.ingest.watcher import _ingest_file
from app.mcp_server.server import ingest_memory


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _unique_content(tag: str = "") -> str:
    # No trailing spaces — parser strips before hashing
    return (f"phase5 integration test content {tag} {uuid.uuid4()}") * 3


def _content_hash(content: str) -> str:
    """Compute the same SHA256 hash that the parser stores (after strip)."""
    return hashlib.sha256(content.strip().encode("utf-8")).hexdigest()


def _make_session_factory(session: AsyncSession):
    """Wrap a test session in a factory-like callable for use with watcher/MCP tests."""
    @asynccontextmanager
    async def factory():
        yield session
    return factory


# ─────────────────────────────────────────────────────────────────────────────
# INGT-04: Watched import folder
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ingt04_watcher_ingests_txt_file(
    db_session_phase5: AsyncSession,
    tmp_path: Path,
):
    """INGT-04: A .txt file placed in watch_dir is ingested and moved to processed/."""
    content = _unique_content("txt")
    test_file = tmp_path / "test_conversation.txt"
    test_file.write_text(content, encoding="utf-8")

    processed_dir = tmp_path / "processed"
    failed_dir = tmp_path / "failed"
    processed_dir.mkdir()
    failed_dir.mkdir()

    factory = _make_session_factory(db_session_phase5)

    from app.domain.ingest.service import ingest_file_content
    await _ingest_file(test_file, processed_dir, failed_dir, factory, ingest_file_content)

    # File should be moved to processed/
    assert not test_file.exists(), "Original file should be moved"
    assert (processed_dir / "test_conversation.txt").exists(), "File should be in processed/"

    # Flush to ensure DB row is visible in current session
    await db_session_phase5.flush()
    result = await db_session_phase5.execute(
        text("SELECT COUNT(*) FROM raw_archive WHERE source_name = 'test_conversation'")
    )
    count = result.scalar()
    assert count >= 1, "Archive item should be created"


@pytest.mark.asyncio
async def test_ingt04_watcher_ingests_json_file(
    db_session_phase5: AsyncSession,
    tmp_path: Path,
):
    """INGT-04: A .json file placed in watch_dir is ingested and moved to processed/."""
    content = _unique_content("json")
    test_file = tmp_path / "export.json"
    test_file.write_text(content, encoding="utf-8")

    processed_dir = tmp_path / "processed"
    failed_dir = tmp_path / "failed"
    processed_dir.mkdir()
    failed_dir.mkdir()

    factory = _make_session_factory(db_session_phase5)

    from app.domain.ingest.service import ingest_file_content
    await _ingest_file(test_file, processed_dir, failed_dir, factory, ingest_file_content)

    assert not test_file.exists(), "Original file should be moved"
    assert (processed_dir / "export.json").exists(), "File should be in processed/"


@pytest.mark.asyncio
async def test_ingt04_watcher_moves_failed_file_to_failed_dir(
    db_session_phase5: AsyncSession,
    tmp_path: Path,
):
    """INGT-04: A file with unsupported extension fails and is moved to failed/ directory."""
    # .csv is not a supported extension — ingest_file_content raises ValueError
    test_file = tmp_path / "bad.csv"
    test_file.write_text("col1,col2\nval1,val2", encoding="utf-8")

    processed_dir = tmp_path / "processed"
    failed_dir = tmp_path / "failed"
    processed_dir.mkdir()
    failed_dir.mkdir()

    factory = _make_session_factory(db_session_phase5)

    from app.domain.ingest.service import ingest_file_content
    await _ingest_file(test_file, processed_dir, failed_dir, factory, ingest_file_content)

    assert not test_file.exists(), "Original file should be moved"
    assert not (processed_dir / "bad.csv").exists(), "Failed file should NOT be in processed/"
    # File should be in failed/ (with or without suffix)
    failed_files = list(failed_dir.iterdir())
    assert len(failed_files) == 1, f"Expected 1 failed file, got: {failed_files}"


@pytest.mark.asyncio
async def test_ingt04_watcher_settings_fields():
    """INGT-04: Settings has watch_dir and watch_poll_interval fields."""
    from app.infrastructure.settings import Settings

    s = Settings(database_url="postgresql+asyncpg://x:x@localhost/x")
    assert hasattr(s, "watch_dir")
    assert hasattr(s, "watch_poll_interval")
    assert s.watch_dir == ""
    assert s.watch_poll_interval == 10


# ─────────────────────────────────────────────────────────────────────────────
# INGT-05 + MCP-02: MCP ingest tool
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mcp02_ingest_memory_success(db_session_phase5: AsyncSession):
    """MCP-02 / INGT-05: ingest_memory with valid content returns accepted status."""
    content = _unique_content("mcp_success")

    factory = _make_session_factory(db_session_phase5)
    with patch("app.mcp_server.server.get_session_factory", return_value=factory):
        result = await ingest_memory(
            content=content,
            source_metadata={"source_type": "mcp", "source_name": "mcp-test-session"},
        )

    assert result.get("status") == "accepted", f"Expected accepted, got: {result}"
    assert result.get("item_count", 0) >= 1
    assert len(result.get("archive_ids", [])) >= 1


@pytest.mark.asyncio
async def test_mcp02_ingest_memory_empty_content():
    """MCP-02: ingest_memory with empty content returns descriptive error."""
    result = await ingest_memory(content="")

    # RR-009: stable error envelope {status, error: {code, message, details, retryable}}
    assert result.get("status") == "error", f"Expected error status, got: {result}"
    assert "content" in result["error"]["message"].lower(), (
        f"Error should mention 'content': {result['error']}"
    )


@pytest.mark.asyncio
async def test_mcp02_ingest_memory_missing_content():
    """MCP-02: ingest_memory with whitespace-only content returns descriptive error."""
    result = await ingest_memory(content="   ")

    assert "error" in result, f"Expected error key, got: {result}"


@pytest.mark.asyncio
async def test_mcp02_ingest_memory_too_short():
    """MCP-02: ingest_memory with content < 10 chars returns descriptive error."""
    result = await ingest_memory(content="short")

    # RR-009: stable error envelope {status, error: {code, message, details, retryable}}
    assert result.get("status") == "error", f"Expected error status, got: {result}"
    error_msg = result["error"]["message"].lower()
    assert "short" in error_msg or "10" in error_msg or "minimum" in error_msg, (
        f"Error should mention short content or minimum: {result['error']}"
    )


@pytest.mark.asyncio
async def test_mcp02_ingest_memory_tool_registered():
    """MCP-02: ingest_memory tool is registered on mcp_app."""
    from app.mcp_server.server import mcp_app
    tools = mcp_app._tool_manager.list_tools()
    tool_names = [t.name for t in tools]
    assert "ingest_memory" in tool_names, f"ingest_memory not found in tools: {tool_names}"
    assert "retrieve_memory" in tool_names, f"retrieve_memory not found in tools: {tool_names}"


# ─────────────────────────────────────────────────────────────────────────────
# PORT-01: Memory bundle export / import
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_port01_export_bundle_format(
    client: AsyncClient,
):
    """PORT-01: GET /api/export/bundle returns correct bundle format structure."""
    resp = await client.get("/api/export/bundle")

    assert resp.status_code == 200
    data = resp.json()
    assert data["format"] == "recalium-memory-bundle"
    assert data["version"] == "1"
    assert "exported_at" in data
    assert "items" in data
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_port01_export_excludes_deleted_items(
    client: AsyncClient,
    db_session_phase5: AsyncSession,
):
    """PORT-01 / PRIV-03: Deleted items are excluded from the export bundle."""
    content_keep = _unique_content("export_keep")
    content_delete = _unique_content("export_delete")

    item_keep = RawArchiveItem(
        id=uuid.uuid4(),
        source_type="test",
        raw_content=content_keep,
        content_hash=_content_hash(content_keep),
    )
    item_delete = RawArchiveItem(
        id=uuid.uuid4(),
        source_type="test",
        raw_content=content_delete,
        content_hash=_content_hash(content_delete),
    )
    db_session_phase5.add(item_keep)
    db_session_phase5.add(item_delete)
    await db_session_phase5.flush()

    # Soft-delete the second item
    from app.domain.archive.service import cascade_delete_archive_item
    await cascade_delete_archive_item(db_session_phase5, item_delete.id)
    await db_session_phase5.commit()

    resp = await client.get("/api/export/bundle")
    assert resp.status_code == 200
    data = resp.json()

    exported_ids = [item["id"] for item in data["items"]]
    assert str(item_keep.id) in exported_ids, "Non-deleted item should be in export"
    assert str(item_delete.id) not in exported_ids, "Deleted item should NOT be in export"


@pytest.mark.asyncio
async def test_port01_import_bundle_success(
    client: AsyncClient,
):
    """PORT-01: POST /api/import/bundle imports items and returns correct counts."""
    content = _unique_content("import_success")
    content_hash = _content_hash(content)

    bundle = {
        "format": "recalium-memory-bundle",
        "version": "1",
        "exported_at": "2026-03-24T00:00:00Z",
        "items": [
            {
                "id": str(uuid.uuid4()),
                "source_type": "test",
                "source_name": "imported-session",
                "ingested_at": "2026-03-24T00:00:00Z",
                "raw_content": content,
                "content_hash": content_hash,
                "conversation_count": 1,
                "metadata": None,
            }
        ],
    }

    resp = await client.post("/api/import/bundle", json=bundle)

    assert resp.status_code == 200
    data = resp.json()
    assert data["imported"] == 1
    assert data["skipped"] == 0
    assert data["errors"] == []


@pytest.mark.asyncio
async def test_port01_import_bundle_dedup_by_content_hash(
    client: AsyncClient,
):
    """PORT-01: Importing the same bundle twice skips duplicates (content_hash dedup)."""
    content = _unique_content("import_dedup")
    content_hash = _content_hash(content)

    bundle = {
        "format": "recalium-memory-bundle",
        "version": "1",
        "exported_at": "2026-03-24T00:00:00Z",
        "items": [
            {
                "id": str(uuid.uuid4()),
                "source_type": "test",
                "source_name": "dedup-test",
                "ingested_at": "2026-03-24T00:00:00Z",
                "raw_content": content,
                "content_hash": content_hash,
                "conversation_count": 1,
                "metadata": None,
            }
        ],
    }

    # First import
    resp1 = await client.post("/api/import/bundle", json=bundle)
    assert resp1.status_code == 200
    assert resp1.json()["imported"] == 1

    # Second import — should skip
    resp2 = await client.post("/api/import/bundle", json=bundle)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["imported"] == 0
    assert data2["skipped"] == 1


@pytest.mark.asyncio
async def test_port01_import_bundle_invalid_format(client: AsyncClient):
    """PORT-01: Import with wrong format field returns 422."""
    bundle = {
        "format": "not-recalium",
        "version": "1",
        "items": [],
    }
    resp = await client.post("/api/import/bundle", json=bundle)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_port01_import_bundle_invalid_version(client: AsyncClient):
    """PORT-01: Import with unsupported version returns 422."""
    bundle = {
        "format": "recalium-memory-bundle",
        "version": "99",
        "items": [],
    }
    resp = await client.post("/api/import/bundle", json=bundle)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_port01_export_import_roundtrip(
    client: AsyncClient,
    db_session_phase5: AsyncSession,
):
    """PORT-01: Export and re-import produces same content (roundtrip)."""
    content = _unique_content("roundtrip")
    item = RawArchiveItem(
        id=uuid.uuid4(),
        source_type="roundtrip_test",
        source_name="roundtrip-source",
        raw_content=content,
        content_hash=_content_hash(content),
    )
    db_session_phase5.add(item)
    await db_session_phase5.flush()
    await db_session_phase5.commit()

    # Export
    export_resp = await client.get("/api/export/bundle")
    assert export_resp.status_code == 200
    bundle = export_resp.json()

    # Verify our item is in the export
    exported_hashes = {i["content_hash"] for i in bundle["items"]}
    assert item.content_hash in exported_hashes, "Item should be in export"

    # Now importing back should skip (already exists)
    import_resp = await client.post("/api/import/bundle", json=bundle)
    assert import_resp.status_code == 200
    result = import_resp.json()
    # All items should be skipped (already in DB by content_hash)
    assert result["skipped"] >= 1


# ─────────────────────────────────────────────────────────────────────────────
# API Contract versioning (PORT-01 — module boundary / contract hardening)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_api_version_header_present(client: AsyncClient):
    """API versioning: X-API-Version header is present on API responses."""
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    assert resp.headers.get("x-api-version") == "1", (
        f"Expected X-API-Version: 1, got: {resp.headers.get('x-api-version')}"
    )


@pytest.mark.asyncio
async def test_health_includes_api_version(client: AsyncClient):
    """API versioning: GET /api/health response body includes api_version field."""
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("api_version") == "1", (
        f"Expected api_version='1' in health response, got: {data}"
    )


@pytest.mark.asyncio
async def test_service_boundary_comments_present():
    """PORT-01: SERVICE-BOUNDARY comments exist in domain module __init__.py files."""
    import pathlib

    boundary_modules = [
        "app/domain/ingest/__init__.py",
        "app/domain/retrieval/__init__.py",
        "app/domain/backup/__init__.py",
        "app/mcp_server/__init__.py",
    ]

    # Find the backend directory relative to this test file
    tests_dir = pathlib.Path(__file__).parent.parent  # tests/
    backend_dir = tests_dir.parent  # backend/

    for rel_path in boundary_modules:
        full_path = backend_dir / rel_path
        assert full_path.exists(), f"File not found: {full_path}"
        content = full_path.read_text(encoding="utf-8")
        assert "SERVICE-BOUNDARY" in content, (
            f"SERVICE-BOUNDARY comment missing in {rel_path}"
        )
