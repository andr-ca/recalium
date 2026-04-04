"""Reprocess API endpoint tests — PIPE-05.

Tests will FAIL (RED) until POST /api/jobs/{job_id}/reprocess endpoint is created.
"""
from __future__ import annotations

import hashlib
import uuid


async def _make_archive_item(session):
    """Helper: insert a minimal RawArchiveItem to satisfy FK constraint on jobs."""
    from app.domain.archive.models import RawArchiveItem
    content = f"test content {uuid.uuid4()}"
    item = RawArchiveItem(
        id=uuid.uuid4(),
        source_type="test",
        raw_content=content,
        content_hash=hashlib.sha256(content.encode()).hexdigest(),
    )
    session.add(item)
    await session.flush()
    return item


async def test_reprocess_endpoint_returns_200(client, db_session):
    """PIPE-05: POST /api/jobs/{job_id}/reprocess resets a failed job to pending."""
    from app.domain.jobs.models import Job

    archive_item = await _make_archive_item(db_session)
    job = Job(
        id=uuid.uuid4(),
        job_type="process_archive_item",
        raw_archive_id=archive_item.id,
        status="failed",
        attempts=3,
        max_attempts=3,
        error_message="Old error",
    )
    db_session.add(job)
    await db_session.commit()

    response = await client.post(f"/api/jobs/{job.id}/reprocess")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "pending"
    assert data["job_id"] == str(job.id)


async def test_reprocess_unknown_job_returns_404(client):
    """PIPE-05: POST /api/jobs/{unknown_id}/reprocess returns 404."""
    response = await client.post(f"/api/jobs/{uuid.uuid4()}/reprocess")
    assert response.status_code == 404


async def test_reprocess_pending_provider_returns_200(client, db_session):
    """PIPE-05: pending_provider jobs can also be manually re-queued via reprocess endpoint."""
    from app.domain.jobs.models import Job

    archive_item = await _make_archive_item(db_session)
    job = Job(
        id=uuid.uuid4(),
        job_type="process_archive_item",
        raw_archive_id=archive_item.id,
        status="pending_provider",
        attempts=0,
    )
    db_session.add(job)
    await db_session.commit()

    response = await client.post(f"/api/jobs/{job.id}/reprocess")
    assert response.status_code == 200
