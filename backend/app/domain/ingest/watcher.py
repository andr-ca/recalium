"""Watched import folder service (INGT-04).

Polls a configured directory every N seconds and ingests any new
.json, .txt, or .md files via the ingest service. Successfully
ingested files are moved to {watch_dir}/processed/; failed files
are moved to {watch_dir}/failed/.

Enabled when settings.watch_dir is non-empty; disabled otherwise.
"""
from __future__ import annotations

import asyncio
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_WATCHED_EXTENSIONS = {".json", ".txt", ".md"}


async def file_watcher_loop(watch_dir: str, poll_interval: int = 10) -> None:
    """Poll watch_dir every poll_interval seconds and ingest new files.

    Cancellation-safe: raises CancelledError cleanly on shutdown.
    """
    from app.domain.ingest.service import ingest_file_content
    from app.infrastructure.db import get_session_factory

    watch_path = Path(watch_dir)
    processed_path = watch_path / "processed"
    failed_path = watch_path / "failed"

    logger.info("File watcher started: watching %s every %ds", watch_dir, poll_interval)

    while True:
        try:
            await asyncio.sleep(poll_interval)
        except asyncio.CancelledError:
            logger.info("File watcher cancelled — shutting down")
            break

        if not watch_path.exists():
            logger.warning("Watch dir %s does not exist — skipping poll", watch_dir)
            continue

        # Ensure processed/ and failed/ directories exist
        processed_path.mkdir(exist_ok=True)
        failed_path.mkdir(exist_ok=True)

        # Collect files to process (top-level only, skip subdirectories)
        files_to_process: list[Path] = []
        for ext in _WATCHED_EXTENSIONS:
            for file_path in watch_path.glob(f"*{ext}"):
                if file_path.is_file() and file_path.parent == watch_path:
                    files_to_process.append(file_path)

        if not files_to_process:
            continue

        logger.info("File watcher: found %d file(s) to ingest", len(files_to_process))

        factory = get_session_factory()
        for file_path in files_to_process:
            await _ingest_file(file_path, processed_path, failed_path, factory, ingest_file_content)


async def _ingest_file(
    file_path: Path,
    processed_path: Path,
    failed_path: Path,
    factory,
    ingest_file_content,
) -> None:
    """Ingest a single file and move to processed/ or failed/."""
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as exc:
        logger.error("File watcher: cannot read %s: %s", file_path.name, exc)
        _move_file(file_path, failed_path, suffix="_read_error")
        return

    try:
        async with factory() as session:
            result = await ingest_file_content(
                session=session,
                filename=file_path.name,
                content=content,
                source_name=file_path.stem,
            )
            await session.commit()
        logger.info(
            "File watcher: ingested %s → %d item(s) %s",
            file_path.name, result.item_count, result.archive_ids,
        )
        _move_file(file_path, processed_path)
    except Exception as exc:
        logger.error("File watcher: ingest failed for %s: %s", file_path.name, exc)
        _move_file(file_path, failed_path, suffix="_ingest_error")


def _move_file(file_path: Path, dest_dir: Path, suffix: str = "") -> None:
    """Move file to dest_dir, appending suffix + timestamp if name conflicts."""
    dest = dest_dir / file_path.name
    if dest.exists():
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        stem = file_path.stem + suffix + f"_{ts}"
        dest = dest_dir / (stem + file_path.suffix)
    try:
        shutil.move(str(file_path), str(dest))
    except Exception as exc:
        logger.error("File watcher: could not move %s to %s: %s", file_path.name, dest_dir, exc)
