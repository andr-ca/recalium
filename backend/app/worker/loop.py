"""Pipeline worker loop.

Single asyncio.Task started in FastAPI lifespan. Polls the jobs table with SKIP LOCKED.
Processes one job at a time (Semaphore(1) for personal scale).

PIPELINE ORDER (enforced in dispatch_job, which is wired in plan 04):
  1. Sensitivity gate (MANDATORY — blocks personal/relationship/unclassified before external call)
  2. LLM summarize + extract (if provider configured and not already done)
  3. Embed (local sentence-transformers, always attempted)
  4. FTS index (always)
  5. Conflict detection (after embedding)
"""
from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)

_MAX_CONCURRENT = 1  # personal scale: one job at a time in v1
_POLL_INTERVAL_SECONDS = 2  # back-off when queue is empty


async def worker_loop() -> None:
    """Main worker loop. Runs forever until cancelled.

    Started via asyncio.create_task() in main.py lifespan.
    Cancelled cleanly on shutdown via task.cancel() + await task.
    """
    from app.infrastructure.db import get_session_factory
    from app.domain.jobs.service import claim_next_job, reset_stale_jobs

    sem = asyncio.Semaphore(_MAX_CONCURRENT)

    logger.info("Pipeline worker loop starting")

    # Run stale job recovery before first poll
    session_factory = get_session_factory()
    async with session_factory() as session:
        stale_count = await reset_stale_jobs(session)
        if stale_count > 0:
            logger.warning("Recovered %d stale jobs on startup", stale_count)

    while True:
        try:
            async with sem:
                # One session spans claim AND dispatch: complete_job/fail_job/
                # set_pending_provider mutate the claimed Job instance, which is
                # only attached to the session that loaded it. With a second
                # session those status commits persist nothing and every job
                # stays 'claimed' forever (then gets stale-reset and reprocessed).
                async with session_factory() as session:
                    job = await claim_next_job(session)

                    if job is not None:
                        logger.info("Processing job %s (type=%s)", job.id, job.job_type)

                        # Dispatch job through pipeline — import here to avoid circular imports
                        from app.worker.dispatcher import dispatch_job  # noqa: PLC0415
                        await dispatch_job(session, job)

                if job is None:
                    await asyncio.sleep(_POLL_INTERVAL_SECONDS)
                    continue

        except asyncio.CancelledError:
            logger.info("Pipeline worker loop cancelled — shutting down cleanly")
            raise  # re-raise so Task completes cleanly

        except Exception as e:
            logger.exception("Worker loop unhandled error (will retry in 5s): %s", e)
            await asyncio.sleep(5)  # brief pause before retrying poll cycle
