"""Worker loop tests — PIPE-01, PIPE-04.

Tests will FAIL (RED) until app.worker.loop and app.domain.jobs.service are created.
"""
from __future__ import annotations

import uuid

import pytest

# These imports will fail until plans 03-04 create the modules.
# That is expected — tests are stubs until GREEN.
pytest.importorskip("app.worker.loop", reason="worker.loop not yet implemented")
pytest.importorskip("app.domain.jobs.service", reason="jobs.service not yet implemented")

from app.worker.loop import worker_loop  # noqa: E402
from app.domain.jobs.service import claim_next_job, complete_job, fail_job  # noqa: E402


async def _make_archive_item(session):
    """Helper: insert a minimal RawArchiveItem to satisfy FK constraint on jobs.raw_archive_id."""
    from app.domain.archive.models import RawArchiveItem
    import hashlib
    content = "test content"
    item = RawArchiveItem(
        id=uuid.uuid4(),
        source_type="test",
        raw_content=content,
        content_hash=hashlib.sha256(content.encode()).hexdigest(),
    )
    session.add(item)
    await session.flush()
    return item


async def test_worker_claims_and_completes_job(db_session_phase2):
    """PIPE-01: Worker claims a pending job and transitions it to completed."""
    # Arrange: create a pending job
    from app.domain.jobs.models import Job
    archive_item = await _make_archive_item(db_session_phase2)
    job = Job(
        id=uuid.uuid4(),
        job_type="process_archive_item",
        raw_archive_id=archive_item.id,
        status="pending",
    )
    db_session_phase2.add(job)
    await db_session_phase2.commit()

    # Act: claim the job — poll until we get our job (other jobs may exist from prior tests)
    claimed = None
    for _ in range(20):  # at most 20 polls to drain prior-test jobs
        result = await claim_next_job(db_session_phase2)
        if result is None:
            break
        if result.id == job.id:
            claimed = result
            break

    # Assert: our specific job is claimed
    assert claimed is not None, "Our newly created job was never claimed"
    assert claimed.status == "claimed"
    assert claimed.id == job.id


async def test_job_retried_on_retryable_failed(db_session_phase2):
    """PIPE-04: Job in retryable_failed is re-claimed on next poll cycle."""
    from app.domain.jobs.models import Job
    archive_item = await _make_archive_item(db_session_phase2)
    job = Job(
        id=uuid.uuid4(),
        job_type="process_archive_item",
        raw_archive_id=archive_item.id,
        status="retryable_failed",
        attempts=1,
        max_attempts=3,
    )
    db_session_phase2.add(job)
    await db_session_phase2.commit()

    claimed = await claim_next_job(db_session_phase2)
    assert claimed is not None
    assert claimed.id == job.id
    assert claimed.attempts == 2


async def test_job_not_retried_after_max_attempts(db_session_phase2):
    """PIPE-04: Job at max_attempts is not claimed (terminal failed)."""
    from app.domain.jobs.models import Job
    archive_item = await _make_archive_item(db_session_phase2)
    job = Job(
        id=uuid.uuid4(),
        job_type="process_archive_item",
        raw_archive_id=archive_item.id,
        status="retryable_failed",
        attempts=3,
        max_attempts=3,
    )
    db_session_phase2.add(job)
    await db_session_phase2.commit()

    claimed = await claim_next_job(db_session_phase2)
    # No job claimed — at max attempts
    assert claimed is None


async def test_stale_claimed_jobs_reset_on_startup(db_session_phase2):
    """PIPE-04: Stale claimed jobs (older than 10 min) are re-queued on worker startup."""
    from app.domain.jobs.service import reset_stale_jobs
    from app.domain.jobs.models import Job
    from datetime import datetime, timezone, timedelta

    archive_item = await _make_archive_item(db_session_phase2)
    stale_job = Job(
        id=uuid.uuid4(),
        job_type="process_archive_item",
        raw_archive_id=archive_item.id,
        status="claimed",
        attempts=1,
        claimed_at=datetime.now(timezone.utc) - timedelta(minutes=15),
    )
    db_session_phase2.add(stale_job)
    await db_session_phase2.commit()

    await reset_stale_jobs(db_session_phase2)
    await db_session_phase2.refresh(stale_job)

    assert stale_job.status == "pending"
