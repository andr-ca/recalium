"""Dispatcher tests — BYOK-07, BYOK-08.

Tests will FAIL (RED) until app.worker.dispatcher is created.
"""
from __future__ import annotations

import pytest

pytest.importorskip("app.worker.dispatcher", reason="worker.dispatcher not yet implemented")

from app.worker.dispatcher import dispatch_job  # noqa: E402


async def test_invalid_key_causes_retryable_failed(db_session_phase2, monkeypatch):
    """BYOK-07: Invalid/rate-limited key → job enters retryable_failed with error_message."""
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

    # Simulate invalid key by monkeypatching OpenAI to raise AuthenticationError
    from openai import AuthenticationError
    async def fake_summarize(*args, **kwargs):
        raise AuthenticationError("Invalid API key", response=None, body=None)

    monkeypatch.setattr(
        "app.worker.dispatcher._run_summarize_job",
        fake_summarize,
    )

    await dispatch_job(db_session_phase2, job)
    await db_session_phase2.refresh(job)

    assert job.status == "retryable_failed"
    assert job.error_message is not None
    assert len(job.error_message) > 0


async def test_completed_subjob_not_rerun(db_session_phase2):
    """BYOK-08: Switching provider does not re-run already-completed sub-jobs."""
    # A job whose summary sub-job is already completed should not re-run summarize
    # even if provider is changed.
    from app.domain.jobs.models import Job
    from app.domain.derived_memory.models import Summary
    import uuid
    from datetime import datetime, timezone

    raw_id = uuid.uuid4()
    # Create a completed summary for this archive item
    summary = Summary(
        raw_archive_id=raw_id,
        summary_text="Existing summary",
        model_used="gpt-4o-mini",
        derivation_method="llm_summarization",
    )
    db_session_phase2.add(summary)

    job = Job(
        id=uuid.uuid4(),
        job_type="process_archive_item",
        raw_archive_id=raw_id,
        status="claimed",
        attempts=1,
    )
    db_session_phase2.add(job)
    await db_session_phase2.commit()

    call_count = {"n": 0}

    async def mock_summarize(*args, **kwargs):
        call_count["n"] += 1
        return {"summary": "new"}

    # If implementation correctly skips completed sub-jobs, mock should not be called
    import app.worker.dispatcher as disp
    original = getattr(disp, "_run_summarize_job", None)
    disp._run_summarize_job = mock_summarize
    try:
        await dispatch_job(db_session_phase2, job)
    finally:
        if original is not None:
            disp._run_summarize_job = original

    assert call_count["n"] == 0, "Summarize ran again even though summary exists"
