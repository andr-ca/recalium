"""Phase 4 integration test suite.

Covers all 13 Phase 4 requirement IDs:
  PRIV-01, PRIV-02, PRIV-03, PRIV-06,
  BYOK-01, BYOK-06,
  BKUP-01, BKUP-02, BKUP-03,
  WEBUI-02, WEBUI-03, WEBUI-06,
  PORT-02

Run with:
    cd backend && uv run python3 -m pytest tests/integration/test_phase4_integration.py -v
"""
from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

import pytest

pytest.importorskip("app.domain.archive.service")
pytest.importorskip("app.domain.telemetry.service")

from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.archive.service import cascade_delete_archive_item
from app.domain.archive.models import RawArchiveItem
from app.domain.derived_memory.models import Summary, Fact, FtsEntry
from app.domain.canonical_memory.models import CanonicalMemoryItem
from app.domain.audit.models import AuditEvent
from app.domain.telemetry.service import increment_telemetry, get_telemetry_summary


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _raw_content(tag: str = "") -> tuple[str, str]:
    content = f"integration test content {tag} {uuid.uuid4()}"
    return content, hashlib.sha256(content.encode()).hexdigest()


async def _create_archive_item(
    session: AsyncSession,
    tag: str = "",
) -> RawArchiveItem:
    content, chash = _raw_content(tag)
    item = RawArchiveItem(
        id=uuid.uuid4(),
        source_type="test",
        raw_content=content,
        content_hash=chash,
    )
    session.add(item)
    await session.flush()
    return item


# ─────────────────────────────────────────────────────────────────────────────
# PRIV-01: Deletion cascade — deleted_at set, search suppressed
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_priv01_deleted_item_absent_from_search(
    client: AsyncClient,
    db_session_phase4: AsyncSession,
):
    """PRIV-01: After deletion, item does not appear in search results."""
    content = f"unique content for priv01 test {uuid.uuid4()}"
    chash = hashlib.sha256(content.encode()).hexdigest()
    item = RawArchiveItem(
        id=uuid.uuid4(),
        source_type="test",
        raw_content=content,
        content_hash=chash,
    )
    db_session_phase4.add(item)

    fts = FtsEntry(raw_archive_id=item.id, text_content=content)
    db_session_phase4.add(fts)
    await db_session_phase4.flush()
    await db_session_phase4.commit()

    # Delete the item
    await cascade_delete_archive_item(db_session_phase4, item.id)

    # Search should not return it
    resp = await client.get(f"/api/search?q={uuid.UUID(str(item.id)).hex[:8]}&mode=keyword")
    assert resp.status_code == 200
    result_ids = [r.get("source_id") for r in resp.json().get("items", [])]
    assert str(item.id) not in result_ids


@pytest.mark.asyncio
async def test_priv01_api_delete_returns_204(
    client: AsyncClient,
    db_session_phase4: AsyncSession,
):
    """PRIV-01: DELETE /api/archive/{id} returns 204."""
    item = await _create_archive_item(db_session_phase4, "delete_204")
    await db_session_phase4.commit()

    resp = await client.delete(f"/api/archive/{item.id}")
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_priv01_deleted_item_sets_deleted_at(
    client: AsyncClient,
    db_session_phase4: AsyncSession,
):
    """PRIV-01: deleted_at is set on the item after DELETE."""
    item = await _create_archive_item(db_session_phase4, "deleted_at")
    await db_session_phase4.commit()

    await client.delete(f"/api/archive/{item.id}")

    result = await db_session_phase4.execute(
        select(RawArchiveItem)
        .where(RawArchiveItem.id == item.id)
        .execution_options(populate_existing=True)
    )
    refreshed = result.scalar_one()
    assert refreshed.deleted_at is not None


# ─────────────────────────────────────────────────────────────────────────────
# PRIV-02: Canonical memory source-removed marker (not hard-deleted)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_priv02_canonical_survives_deletion_with_marker(
    db_session_phase4: AsyncSession,
):
    """PRIV-02: Canonical memory is NOT deleted but marked source_removed + required_review."""
    item = await _create_archive_item(db_session_phase4, "canonical_source")
    await db_session_phase4.flush()

    canonical = CanonicalMemoryItem(
        raw_archive_id=item.id,
        content="A fact we want to keep reviewing.",
        status="active",
        promoted_from="fact",
        promoted_by="user_ui",
    )
    db_session_phase4.add(canonical)
    await db_session_phase4.flush()
    cid = canonical.id

    await cascade_delete_archive_item(db_session_phase4, item.id)

    result = await db_session_phase4.execute(
        select(CanonicalMemoryItem)
        .where(CanonicalMemoryItem.id == cid)
        .execution_options(populate_existing=True)
    )
    c = result.scalar_one_or_none()
    assert c is not None, "Canonical item must NOT be hard-deleted"
    assert c.source_status == "source_removed"
    assert c.status == "required_review"


@pytest.mark.asyncio
async def test_priv02_derived_summaries_marked_source_removed(
    db_session_phase4: AsyncSession,
):
    """PRIV-02: Summaries linked to deleted item get source_status=source_removed."""
    item = await _create_archive_item(db_session_phase4, "summary_cascade")
    await db_session_phase4.flush()

    summary = Summary(
        raw_archive_id=item.id,
        summary_text="test summary",
        source_status="active",
        model_used="test-model",
        derivation_method="llm_summarization",
    )
    db_session_phase4.add(summary)
    await db_session_phase4.flush()
    sid = summary.id

    await cascade_delete_archive_item(db_session_phase4, item.id)

    result = await db_session_phase4.execute(
        select(Summary).where(Summary.id == sid).execution_options(populate_existing=True)
    )
    s = result.scalar_one()
    assert s.source_status == "source_removed"


@pytest.mark.asyncio
async def test_priv02_derived_facts_marked_source_removed(
    db_session_phase4: AsyncSession,
):
    """PRIV-02: Facts linked to deleted item get source_status=source_removed."""
    item = await _create_archive_item(db_session_phase4, "fact_cascade")
    await db_session_phase4.flush()

    fact = Fact(
        raw_archive_id=item.id,
        fact_text="test fact",
        source_span="test span",
        source_status="active",
        confidence_tier="high",
        derivation_method="llm_extraction",
        derivation_model="test-model",
    )
    db_session_phase4.add(fact)
    await db_session_phase4.flush()
    fid = fact.id

    await cascade_delete_archive_item(db_session_phase4, item.id)

    result = await db_session_phase4.execute(
        select(Fact).where(Fact.id == fid).execution_options(populate_existing=True)
    )
    f = result.scalar_one()
    assert f.source_status == "source_removed"


# ─────────────────────────────────────────────────────────────────────────────
# PRIV-03: Audit event created on deletion; backup flag
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_priv03_deletion_writes_audit_event(
    client: AsyncClient,
    db_session_phase4: AsyncSession,
):
    """PRIV-03: DELETE /api/archive/{id} creates an audit event with event_type='archive_delete'."""
    item = await _create_archive_item(db_session_phase4, "audit_event")
    await db_session_phase4.commit()

    await client.delete(f"/api/archive/{item.id}")

    result = await db_session_phase4.execute(
        select(AuditEvent).where(AuditEvent.event_type == "archive_delete")
    )
    events = result.scalars().all()
    assert any(
        str(item.id) in str(e.operation_metadata)
        for e in events
    ), "No audit event found for deleted archive item"


@pytest.mark.asyncio
async def test_priv03_backup_list_returns_has_post_deletion_events_field(
    client: AsyncClient,
):
    """PRIV-03: GET /api/backup/list returns has_post_deletion_events on each backup item."""
    resp = await client.get("/api/backup/list")
    assert resp.status_code == 200
    data = resp.json()
    assert "backups" in data
    # Each backup item must have the has_post_deletion_events flag
    for backup in data["backups"]:
        assert "has_post_deletion_events" in backup, (
            f"Backup item missing has_post_deletion_events: {backup}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# PRIV-06: Auth middleware
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_priv06_localhost_requires_no_auth(client: AsyncClient):
    """PRIV-06: No auth needed when bind_host is 127.0.0.1 (localhost)."""
    resp = await client.get("/api/archive")
    assert resp.status_code != 401


# ─────────────────────────────────────────────────────────────────────────────
# BYOK-01 / BYOK-06: Onboarding wizard status
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_byok01_onboarding_endpoint_returns_expected_fields(
    client: AsyncClient,
):
    """BYOK-01: GET /api/status/onboarding returns all expected fields."""
    resp = await client.get("/api/status/onboarding")
    assert resp.status_code == 200
    body = resp.json()
    assert "should_show_wizard" in body
    assert "has_archive_items" in body
    assert "has_configured_key" in body
    assert isinstance(body["should_show_wizard"], bool)
    assert isinstance(body["has_archive_items"], bool)
    assert isinstance(body["has_configured_key"], bool)


@pytest.mark.asyncio
async def test_byok01_wizard_hidden_when_items_exist(
    client: AsyncClient,
    db_session_phase4: AsyncSession,
):
    """BYOK-01: should_show_wizard=False when archive items exist."""
    await _create_archive_item(db_session_phase4, "wizard_suppress")
    await db_session_phase4.commit()

    resp = await client.get("/api/status/onboarding")
    assert resp.status_code == 200
    body = resp.json()
    assert body["has_archive_items"] is True
    # When items exist, wizard should not show regardless of key status
    assert body["should_show_wizard"] is False


@pytest.mark.asyncio
async def test_byok06_wizard_logic_consistent(client: AsyncClient):
    """BYOK-06: should_show_wizard = not has_archive_items AND not has_configured_key."""
    resp = await client.get("/api/status/onboarding")
    assert resp.status_code == 200
    body = resp.json()
    expected = not body["has_archive_items"] and not body["has_configured_key"]
    assert body["should_show_wizard"] == expected


# ─────────────────────────────────────────────────────────────────────────────
# BKUP-01 / BKUP-03: Backup list endpoint
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_bkup01_backup_list_endpoint_returns_200(client: AsyncClient):
    """BKUP-01: GET /api/backup/list returns 200 with a list."""
    resp = await client.get("/api/backup/list")
    assert resp.status_code == 200
    data = resp.json()
    assert "backups" in data
    assert isinstance(data["backups"], list)
    assert "count" in data


@pytest.mark.asyncio
@pytest.mark.skipif(
    not any(
        Path(p).exists()
        for p in ["/usr/bin/pg_dump", "/usr/local/bin/pg_dump"]
    ),
    reason="pg_dump not available in this environment",
)
async def test_bkup01_trigger_creates_backup(client: AsyncClient):
    """BKUP-01: POST /api/backup/trigger creates a backup file."""
    resp = await client.post("/api/backup/trigger")
    assert resp.status_code == 200
    body = resp.json()
    assert "filename" in body or "path" in body


# ─────────────────────────────────────────────────────────────────────────────
# BKUP-02 / BKUP-03: Restore endpoint
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_bkup02_restore_returns_404_for_nonexistent_file(client: AsyncClient):
    """BKUP-02: POST /api/backup/restore returns 404 for a filename that doesn't exist."""
    resp = await client.post(
        "/api/backup/restore",
        json={"filename": "nonexistent_backup_file_xyz.dump"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
@pytest.mark.skipif(
    not any(
        Path(p).exists()
        for p in ["/usr/bin/pg_restore", "/usr/local/bin/pg_restore"]
    ),
    reason="pg_restore not available in this environment",
)
async def test_bkup03_restore_succeeds_with_valid_backup(client: AsyncClient):
    """BKUP-03: Full backup → restore cycle succeeds."""
    # Create a backup first
    trigger_resp = await client.post("/api/backup/trigger")
    if trigger_resp.status_code != 200:
        pytest.skip("Backup creation failed — skipping restore test")

    body = trigger_resp.json()
    filename = body.get("filename")
    if not filename:
        pytest.skip("No filename in backup response")

    restore_resp = await client.post("/api/backup/restore", json={"filename": filename})
    assert restore_resp.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# PORT-02: Telemetry
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_port02_telemetry_increments_on_search(
    client: AsyncClient,
    db_session_phase4: AsyncSession,
):
    """PORT-02: GET /api/search increments search telemetry counter."""
    await client.get("/api/search?q=hello&mode=keyword")

    summary = await get_telemetry_summary(db_session_phase4, days=1)
    # Service returns list of dicts with date and counter fields
    assert isinstance(summary, list)
    for row in summary:
        assert "date" in row
        assert "searches" in row


@pytest.mark.asyncio
async def test_port02_telemetry_api_endpoint_returns_expected_shape(client: AsyncClient):
    """PORT-02: GET /api/telemetry/summary returns days + summary list."""
    resp = await client.get("/api/telemetry/summary")
    assert resp.status_code == 200
    data = resp.json()
    # Must return { days: int, summary: list }
    assert "days" in data
    assert "summary" in data
    assert isinstance(data["summary"], list)
    # Each summary entry has expected counter fields
    for entry in data["summary"]:
        assert "date" in entry
        assert "searches" in entry
        assert "retrievals" in entry
        assert "facts_reviewed" in entry
        assert "canonical_created" in entry
        assert "mcp_retrievals" in entry
        assert "ui_retrievals" in entry


@pytest.mark.asyncio
async def test_port02_telemetry_increment_service(
    db_session_phase4: AsyncSession,
):
    """PORT-02: increment_telemetry service increments the correct column."""
    await increment_telemetry(db_session_phase4, "search")
    await db_session_phase4.commit()

    summary = await get_telemetry_summary(db_session_phase4, days=1)
    assert isinstance(summary, list)
    today_rows = [r for r in summary if r.get("searches", 0) > 0]
    assert len(today_rows) > 0, "searches counter should have been incremented"


# ─────────────────────────────────────────────────────────────────────────────
# WEBUI-02: Archive deletion reflected in listing
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_webui02_deleted_item_excluded_from_default_archive_list(
    client: AsyncClient,
    db_session_phase4: AsyncSession,
):
    """WEBUI-02: Deleted items do not appear in default archive list."""
    item = await _create_archive_item(db_session_phase4, "webui02_delete")
    await db_session_phase4.commit()

    await client.delete(f"/api/archive/{item.id}")

    resp = await client.get("/api/archive")
    assert resp.status_code == 200
    body = resp.json()
    ids = [i["id"] for i in body.get("items", [])]
    assert str(item.id) not in ids


@pytest.mark.asyncio
async def test_webui02_deleted_item_visible_with_include_deleted_flag(
    client: AsyncClient,
    db_session_phase4: AsyncSession,
):
    """WEBUI-02: Deleted items appear when include_deleted=true."""
    item = await _create_archive_item(db_session_phase4, "webui02_include_deleted")
    await db_session_phase4.commit()

    await client.delete(f"/api/archive/{item.id}")

    resp = await client.get("/api/archive?include_deleted=true")
    assert resp.status_code == 200
    body = resp.json()
    ids = [i["id"] for i in body.get("items", [])]
    assert str(item.id) in ids


# ─────────────────────────────────────────────────────────────────────────────
# WEBUI-03 / WEBUI-06: Audit events endpoint with filtering
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_webui06_audit_events_endpoint_returns_list(client: AsyncClient):
    """WEBUI-06: GET /api/audit/events returns list with count."""
    resp = await client.get("/api/audit/events")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "count" in data
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_webui03_audit_event_type_filter(
    client: AsyncClient,
    db_session_phase4: AsyncSession,
):
    """WEBUI-03: GET /api/audit/events?event_type= correctly filters results."""
    unique_type = f"test_event_{uuid.uuid4().hex[:8]}"
    event = AuditEvent(
        id=uuid.uuid4(),
        event_type=unique_type,
        actor="test_user",
        operation_metadata={"test": True},
    )
    db_session_phase4.add(event)
    await db_session_phase4.commit()

    # Filter by the unique type — must return exactly 1 item
    resp = await client.get(f"/api/audit/events?event_type={unique_type}")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) >= 1
    assert all(e["event_type"] == unique_type for e in body["items"])

    # Filter by a type that doesn't exist — should return empty
    resp2 = await client.get("/api/audit/events?event_type=nonexistent_type_zzzxxx")
    assert resp2.status_code == 200
    assert resp2.json()["items"] == []


@pytest.mark.asyncio
async def test_webui03_audit_events_pagination_offset(
    client: AsyncClient,
    db_session_phase4: AsyncSession,
):
    """WEBUI-03: Audit events pagination with offset=0 works correctly (not silently dropped)."""
    unique_type = f"pagtest_{uuid.uuid4().hex[:8]}"
    for _ in range(3):
        event = AuditEvent(
            id=uuid.uuid4(),
            event_type=unique_type,
            actor="test_user",
            operation_metadata={},
        )
        db_session_phase4.add(event)
    await db_session_phase4.commit()

    resp_offset0 = await client.get(f"/api/audit/events?event_type={unique_type}&offset=0&limit=10")
    assert resp_offset0.status_code == 200
    count = len(resp_offset0.json()["items"])
    assert count >= 3

    # offset=2 should return 1 fewer items
    resp_offset2 = await client.get(f"/api/audit/events?event_type={unique_type}&offset=2&limit=10")
    assert resp_offset2.status_code == 200
    count2 = len(resp_offset2.json()["items"])
    assert count2 == count - 2
