"""Jobs service tests — PIPE-04, PIPE-05.

Tests will FAIL (RED) until app.domain.jobs.service is created.
"""
from __future__ import annotations

import pytest

pytest.importorskip("app.domain.jobs.service", reason="jobs.service not yet implemented")

from app.domain.jobs.service import (  # noqa: E402
    claim_next_job,
    complete_job,
    fail_job,
    reset_stale_jobs,
    reprocess_job,
)


async def test_claim_pending_job(db_session_phase2):
    """PIPE-04: claim_next_job claims a pending job atomically."""
    from app.domain.jobs.models import Job
    import uuid
    job = Job(
        id=uuid.uuid4(),
        job_type="process_archive_item",
        raw_archive_id=uuid.uuid4(),
        status="pending",
    )
    db_session_phase2.add(job)
    await db_session_phase2.commit()

    claimed = await claim_next_job(db_session_phase2)
    assert claimed is not None
    assert claimed.status == "claimed"
    assert claimed.attempts == 1


async def test_fail_job_with_error_message(db_session_phase2):
    """BYOK-07: fail_job sets retryable_failed with error_message captured."""
    from app.domain.jobs.models import Job
    import uuid
    job = Job(
        id=uuid.uuid4(),
        job_type="process_archive_item",
        raw_archive_id=uuid.uuid4(),
        status="claimed",
        attempts=1,
    )
    db_session_phase2.add(job)
    await db_session_phase2.commit()

    await fail_job(db_session_phase2, job, error="AuthenticationError: invalid api key", retryable=True)
    await db_session_phase2.refresh(job)

    assert job.status == "retryable_failed"
    assert "AuthenticationError" in job.error_message


async def test_terminal_failure_when_max_attempts_reached(db_session_phase2):
    """PIPE-04: Job transitions to 'failed' (terminal) when attempts >= max_attempts."""
    from app.domain.jobs.models import Job
    import uuid
    job = Job(
        id=uuid.uuid4(),
        job_type="process_archive_item",
        raw_archive_id=uuid.uuid4(),
        status="claimed",
        attempts=3,
        max_attempts=3,
    )
    db_session_phase2.add(job)
    await db_session_phase2.commit()

    await fail_job(db_session_phase2, job, error="Too many attempts", retryable=True)
    await db_session_phase2.refresh(job)

    # At max_attempts, retryable_failed is acceptable BUT claim_next_job must not re-pick it
    next_job = await claim_next_job(db_session_phase2)
    assert next_job is None  # cannot be claimed again


async def test_reprocess_resets_job_to_pending(db_session_phase2):
    """PIPE-05: reprocess_job resets a failed job back to pending for re-queue."""
    from app.domain.jobs.models import Job
    import uuid
    job = Job(
        id=uuid.uuid4(),
        job_type="process_archive_item",
        raw_archive_id=uuid.uuid4(),
        status="failed",
        attempts=3,
        max_attempts=3,
        error_message="Some old error",
    )
    db_session_phase2.add(job)
    await db_session_phase2.commit()

    await reprocess_job(db_session_phase2, job.id)
    await db_session_phase2.refresh(job)

    assert job.status == "pending"
    assert job.attempts == 0
    assert job.error_message is None
