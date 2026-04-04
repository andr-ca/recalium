---
wave: 3
depends_on:
  - 01-02-postgres-schema-PLAN.md
  - 01-04-fastapi-skeleton-PLAN.md
requirements_addressed: [INGT-01, INGT-02, INGT-03, BYOK-05]
files_modified:
  - backend/app/domain/ingest/__init__.py
  - backend/app/domain/ingest/service.py
  - backend/app/domain/ingest/parsers.py
  - backend/app/domain/archive/models.py
  - backend/app/domain/jobs/models.py
  - backend/app/domain/audit/models.py
  - backend/app/api/routes/ingest.py
  - frontend/src/pages/IngestPage.tsx
autonomous: true
---

<objective>
Implement the ingest domain service and API endpoint: POST /api/ingest accepts text paste (plain text / Markdown) and POST /api/ingest/file accepts .json/.txt/.md uploads. Format detection (ChatGPT JSON, Claude JSON, generic JSON, plain text) is automatic. Each call persists to raw_archive, creates a job stub, emits an audit_event, and returns HTTP 202 with item_count and archive_ids within P95 ≤ 1s. Also implements the Ingest page UI with paste/file tabs.

Purpose: Satisfies INGT-01 (paste), INGT-02 (file upload), INGT-03 (archive within 1s), BYOK-05 (works without API keys).
Output: backend ingest domain + ORM models + route handler; frontend IngestPage with tabs.
</objective>

<tasks>

<task id="1" name="Create ORM models and ingest parsers">
  <read_first>
    - backend/alembic/versions/0001_initial.py (exact column names for raw_archive, jobs, audit_events)
    - backend/app/infrastructure/db.py (Base class)
    - .planning/phases/01-foundation/01-CONTEXT.md (D-18 formats, D-09 source_status, D-10 soft-delete)
    - docs/architecture/component-boundaries.md (ingest module responsibilities)
  </read_first>
  <action>
Create `backend/app/domain/archive/models.py` (ORM model for raw_archive — replaces stub):

```python
"""Archive domain ORM models."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, String, Text, Integer, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db import Base


class RawArchiveItem(Base):
    """Raw ingested conversation. Soft-deleted via deleted_at.

    ALL read queries MUST filter: WHERE deleted_at IS NULL
    """
    __tablename__ = "raw_archive"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    # "chatgpt_json" | "claude_json" | "generic_json" | "paste_text" | "paste_markdown"
    source_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    conversation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    ingested_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True, default=None
    )
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
```

Create `backend/app/domain/jobs/models.py` (ORM model for jobs table — replaces stub):

```python
"""Jobs domain ORM models."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import String, Text, Integer, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db import Base


class Job(Base):
    """Processing job. Status transitions: pending → claimed → completed | failed | retryable_failed."""
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job_type: Mapped[str] = mapped_column(String(64), nullable=False)
    # Phase 2 types: "summarize" | "extract_facts" | "embed" | "index_fts" | "dedup"
    # Phase 1 stub: enqueued as "pending_pipeline" — worker processes in Phase 2
    raw_archive_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("raw_archive.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    claimed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
```

Create `backend/app/domain/audit/models.py` (ORM model for audit_events — replaces stub):

```python
"""Audit domain ORM models."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, String, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db import Base


class AuditEvent(Base):
    """Append-only audit event log.

    NEVER update or delete rows in this table.
    Write events synchronously with the operation they record.
    """
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    # "ingest" | "archive_read" | "settings_update" | "key_validation" | "delete"
    raw_archive_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    actor: Mapped[str] = mapped_column(String(64), nullable=False, default="user_ui")
    operation_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow
    )
```

Create `backend/app/domain/ingest/parsers.py` (format detection and normalization):

```python
"""Ingest parsers: auto-detect format and normalize to canonical representation.

Supported formats (D-18):
- paste_text: plain text (not JSON, not Markdown-with-headers)
- paste_markdown: Markdown text (# headers detected)
- chatgpt_json: ChatGPT export format {"conversations": [...]}
- claude_json: Claude export format [{"uuid": ..., "chat_messages": [...]}]
- generic_json: any other JSON (list or dict)
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass


@dataclass
class ParsedIngest:
    """Result of parsing a raw ingest payload."""
    source_type: str
    # "chatgpt_json" | "claude_json" | "generic_json" | "paste_text" | "paste_markdown"
    raw_content: str
    content_hash: str
    conversation_count: int
    source_name: str | None
    metadata: dict | None


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _is_markdown(text: str) -> bool:
    """Heuristic: text is Markdown if it has ATX headers or fenced code blocks."""
    lines = text.splitlines()
    for line in lines[:50]:  # Check first 50 lines
        stripped = line.lstrip()
        if stripped.startswith("#") or stripped.startswith("```"):
            return True
    return False


def _count_chatgpt_conversations(data: dict) -> int:
    """Count conversations in ChatGPT export format."""
    conversations = data.get("conversations", [])
    if isinstance(conversations, list):
        return len(conversations)
    return 1


def _count_claude_conversations(data: list) -> int:
    """Count conversations in Claude export format."""
    return len(data) if isinstance(data, list) else 1


def detect_and_parse(
    content: str,
    filename: str | None = None,
    source_name: str | None = None,
) -> ParsedIngest:
    """Auto-detect format and parse content into ParsedIngest.

    Detection order:
    1. Attempt JSON parse
       a. If dict with "conversations" key → chatgpt_json
       b. If list with items having "uuid" + "chat_messages" → claude_json
       c. Else → generic_json
    2. If not JSON:
       a. If _is_markdown() → paste_markdown
       b. Else → paste_text
    """
    content = content.strip()
    raw_content = content
    content_hash = _sha256(content)

    # Try JSON
    parsed_json = None
    try:
        parsed_json = json.loads(content)
    except (json.JSONDecodeError, ValueError):
        pass

    if parsed_json is not None:
        # ChatGPT format: {"conversations": [...]}
        if isinstance(parsed_json, dict) and "conversations" in parsed_json:
            count = _count_chatgpt_conversations(parsed_json)
            return ParsedIngest(
                source_type="chatgpt_json",
                raw_content=raw_content,
                content_hash=content_hash,
                conversation_count=count,
                source_name=source_name or (filename if filename else "ChatGPT Export"),
                metadata={"conversation_count": count},
            )

        # Claude format: [{"uuid": ..., "chat_messages": [...]}]
        if (
            isinstance(parsed_json, list)
            and len(parsed_json) > 0
            and isinstance(parsed_json[0], dict)
            and "uuid" in parsed_json[0]
            and "chat_messages" in parsed_json[0]
        ):
            count = _count_claude_conversations(parsed_json)
            return ParsedIngest(
                source_type="claude_json",
                raw_content=raw_content,
                content_hash=content_hash,
                conversation_count=count,
                source_name=source_name or (filename if filename else "Claude Export"),
                metadata={"conversation_count": count},
            )

        # Generic JSON
        count = len(parsed_json) if isinstance(parsed_json, list) else 1
        return ParsedIngest(
            source_type="generic_json",
            raw_content=raw_content,
            content_hash=content_hash,
            conversation_count=count,
            source_name=source_name or (filename if filename else "JSON Import"),
            metadata={"json_type": type(parsed_json).__name__},
        )

    # Plain text or Markdown
    if _is_markdown(content):
        return ParsedIngest(
            source_type="paste_markdown",
            raw_content=raw_content,
            content_hash=content_hash,
            conversation_count=1,
            source_name=source_name or "Markdown Paste",
            metadata=None,
        )

    return ParsedIngest(
        source_type="paste_text",
        raw_content=raw_content,
        content_hash=content_hash,
        conversation_count=1,
        source_name=source_name or "Text Paste",
        metadata=None,
    )
```

Create `backend/app/domain/ingest/__init__.py`:
```python
"""Ingest domain — validate, parse, persist, and enqueue."""
```
  </action>
  <acceptance_criteria>
    - `grep -n "class RawArchiveItem" backend/app/domain/archive/models.py` returns 1 line
    - `grep -n "deleted_at.*Mapped\[datetime | None\]" backend/app/domain/archive/models.py` returns 1 line
    - `grep -n "class Job" backend/app/domain/jobs/models.py` returns 1 line
    - `grep -n "class AuditEvent" backend/app/domain/audit/models.py` returns 1 line
    - `grep -n "NEVER update or delete rows" backend/app/domain/audit/models.py` returns 1 line
    - `grep -n "chatgpt_json\|claude_json\|generic_json\|paste_text\|paste_markdown" backend/app/domain/ingest/parsers.py | wc -l` returns ≥ 5 (one per format)
    - `grep -n "def detect_and_parse" backend/app/domain/ingest/parsers.py` returns 1 line
    - `grep -n "def _sha256" backend/app/domain/ingest/parsers.py` returns 1 line
    - `grep -n "chat_messages.*uuid\|uuid.*chat_messages" backend/app/domain/ingest/parsers.py` returns ≥ 1 line (Claude detection)
    - `grep -n '"conversations"' backend/app/domain/ingest/parsers.py` returns ≥ 1 line (ChatGPT detection)
  </acceptance_criteria>
</task>

<task id="2" name="Create ingest domain service and wire POST /api/ingest route">
  <read_first>
    - backend/app/domain/ingest/parsers.py (from previous task — ParsedIngest)
    - backend/app/domain/archive/models.py (RawArchiveItem)
    - backend/app/domain/jobs/models.py (Job)
    - backend/app/domain/audit/models.py (AuditEvent)
    - backend/app/infrastructure/db.py (get_session)
    - .planning/phases/01-foundation/01-CONTEXT.md (D-15 paste+file modes, D-16 toast+navigate)
    - docs/architecture/component-boundaries.md (ingest sequence flow A)
  </read_first>
  <action>
Create `backend/app/domain/ingest/service.py`:

```python
"""Ingest domain service.

Sequence (per component-boundaries.md Sequence Flow A):
1. Parse payload (detect format, normalize)
2. Persist raw_archive item
3. Persist audit_event (synchronously)
4. Enqueue job stub (status="pending", type="pending_pipeline")
5. Return IngestResult

Atomicity: steps 2-4 are in a single DB transaction.
No external calls, no async background tasks in Phase 1.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.archive.models import RawArchiveItem
from app.domain.audit.models import AuditEvent
from app.domain.ingest.parsers import ParsedIngest, detect_and_parse
from app.domain.jobs.models import Job

logger = logging.getLogger(__name__)


@dataclass
class IngestResult:
    """Result of a successful ingest operation."""
    item_count: int
    archive_ids: list[UUID]


async def ingest_text_content(
    session: AsyncSession,
    content: str,
    source_name: str | None = None,
) -> IngestResult:
    """Ingest plain text or JSON content (paste mode).

    Raises:
        ValueError: if content is empty or too short (< 10 chars)
    """
    content = content.strip()
    if len(content) < 10:
        raise ValueError(f"Content too short to ingest (got {len(content)} chars, need ≥ 10)")

    parsed = detect_and_parse(content=content, filename=None, source_name=source_name)
    return await _persist_ingest(session=session, parsed=parsed, actor="user_ui")


async def ingest_file_content(
    session: AsyncSession,
    filename: str,
    content: str,
    source_name: str | None = None,
) -> IngestResult:
    """Ingest content from an uploaded file (.json, .txt, .md).

    Raises:
        ValueError: if filename extension is not supported
        ValueError: if content is empty
    """
    allowed_extensions = {".json", ".txt", ".md"}
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in allowed_extensions:
        raise ValueError(
            f"Unsupported file type: {filename!r}. "
            f"Allowed: {', '.join(sorted(allowed_extensions))}"
        )

    content = content.strip()
    if not content:
        raise ValueError(f"File {filename!r} is empty")

    parsed = detect_and_parse(
        content=content,
        filename=filename,
        source_name=source_name or filename,
    )
    return await _persist_ingest(session=session, parsed=parsed, actor="user_ui")


async def _persist_ingest(
    session: AsyncSession,
    parsed: ParsedIngest,
    actor: str,
) -> IngestResult:
    """Persist raw_archive item + audit_event + job stub in a single transaction."""
    # 1. Create raw archive item
    archive_item = RawArchiveItem(
        source_type=parsed.source_type,
        source_name=parsed.source_name,
        raw_content=parsed.raw_content,
        content_hash=parsed.content_hash,
        conversation_count=parsed.conversation_count,
        metadata_json=parsed.metadata,
    )
    session.add(archive_item)
    await session.flush()  # Get archive_item.id without committing

    # 2. Emit audit event (synchronous — must be in same transaction)
    audit_event = AuditEvent(
        event_type="ingest",
        raw_archive_id=archive_item.id,
        actor=actor,
        operation_metadata={
            "source_type": parsed.source_type,
            "conversation_count": parsed.conversation_count,
            "content_hash": parsed.content_hash,
        },
    )
    session.add(audit_event)

    # 3. Enqueue job stub (Phase 2 worker will process these)
    job = Job(
        job_type="pending_pipeline",
        raw_archive_id=archive_item.id,
        status="pending",
    )
    session.add(job)

    # Transaction commits in get_session() dependency on success
    logger.info(
        f"Ingested: id={archive_item.id} type={parsed.source_type} "
        f"conversations={parsed.conversation_count}"
    )

    return IngestResult(
        item_count=parsed.conversation_count,
        archive_ids=[archive_item.id],
    )
```

Replace the stub in `backend/app/api/routes/ingest.py` with the real implementation:

```python
"""Ingest routes — POST /api/ingest and POST /api/ingest/file."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.ingest.service import ingest_file_content, ingest_text_content
from app.infrastructure.db import get_session

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50 MB hard limit


class IngestTextRequest(BaseModel):
    mode: str = "text"
    content: str
    source_name: str | None = None

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("content must not be empty")
        return v


class IngestResponse(BaseModel):
    status: str = "accepted"
    item_count: int
    archive_ids: list[str]


@router.post("", response_model=IngestResponse, status_code=202)
async def ingest_text(
    request: IngestTextRequest,
    session: AsyncSession = Depends(get_session),
) -> IngestResponse:
    """POST /api/ingest — ingest plain text or JSON via paste.

    Accepts: plain text, Markdown, ChatGPT JSON, Claude JSON, generic JSON.
    Returns: HTTP 202 with item_count and archive_ids.
    P95 target: ≤ 1s (no processing, just parse + DB write).
    """
    try:
        result = await ingest_text_content(
            session=session,
            content=request.content,
            source_name=request.source_name,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return IngestResponse(
        status="accepted",
        item_count=result.item_count,
        archive_ids=[str(aid) for aid in result.archive_ids],
    )


@router.post("/file", response_model=IngestResponse, status_code=202)
async def ingest_file(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
) -> IngestResponse:
    """POST /api/ingest/file — ingest a .json, .txt, or .md file upload.

    Returns: HTTP 202 with item_count and archive_ids.
    P95 target: ≤ 1s (no processing, just parse + DB write).
    """
    if file.size and file.size > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large: {file.size} bytes. Max: {MAX_UPLOAD_BYTES} bytes.",
        )

    raw_bytes = await file.read()
    if len(raw_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (50 MB limit).")

    try:
        content = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=422,
            detail="File must be UTF-8 encoded text (.json, .txt, .md).",
        )

    filename = file.filename or "upload"
    try:
        result = await ingest_file_content(
            session=session,
            filename=filename,
            content=content,
            source_name=filename,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    return IngestResponse(
        status="accepted",
        item_count=result.item_count,
        archive_ids=[str(aid) for aid in result.archive_ids],
    )
```
  </action>
  <acceptance_criteria>
    - `grep -n "async def ingest_text_content\|async def ingest_file_content\|async def _persist_ingest" backend/app/domain/ingest/service.py | wc -l` returns 3
    - `grep -n "session.flush()" backend/app/domain/ingest/service.py` returns 1 line (get ID before commit)
    - `grep -n "AuditEvent\|Job\|RawArchiveItem" backend/app/domain/ingest/service.py | wc -l` returns ≥ 3 (all three model imports used)
    - `grep -n "status_code=202" backend/app/api/routes/ingest.py` returns ≥ 1 line (HTTP 202 Accepted)
    - `grep -n "MAX_UPLOAD_BYTES = 50" backend/app/api/routes/ingest.py` returns 1 line
    - `grep -n "status_code=413" backend/app/api/routes/ingest.py` returns ≥ 1 line
    - `grep -n "UnicodeDecodeError" backend/app/api/routes/ingest.py` returns 1 line
    - `grep -n "UploadFile\|File" backend/app/api/routes/ingest.py` returns ≥ 2 lines
  </acceptance_criteria>
</task>

<task id="3" name="Implement Ingest page UI with paste/file tabs">
  <read_first>
    - frontend/src/lib/api.ts (ingestText, ingestFile, IngestResponse)
    - frontend/src/components/ui/button.tsx, badge.tsx, toast.tsx
    - .planning/phases/01-foundation/01-CONTEXT.md (D-15 paste+file tabs, D-16 toast+navigate)
  </read_first>
  <action>
Replace the stub `frontend/src/pages/IngestPage.tsx` with the full implementation:

```typescript
import * as React from "react";
import { useNavigate } from "react-router-dom";
import { Upload, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Toast } from "@/components/ui/toast";
import { ingestText, ingestFile, ApiError } from "@/lib/api";
import { cn } from "@/lib/utils";

type Tab = "paste" | "file";

export function IngestPage() {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = React.useState<Tab>("paste");
  const [pasteContent, setPasteContent] = React.useState("");
  const [sourceName, setSourceName] = React.useState("");
  const [isDragging, setIsDragging] = React.useState(false);
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [toast, setToast] = React.useState<{ message: string; type: "success" | "error" } | null>(null);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const handlePasteSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pasteContent.trim()) return;
    setIsSubmitting(true);
    try {
      const result = await ingestText(pasteContent, sourceName || undefined);
      setToast({ message: `${result.item_count} conversation(s) ingested`, type: "success" });
      setTimeout(() => navigate("/archive"), 1500);
    } catch (err) {
      const detail = err instanceof ApiError ? err.detail : "Ingest failed. Please try again.";
      setToast({ message: detail, type: "error" });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleFileSubmit = async (file: File) => {
    setIsSubmitting(true);
    try {
      const result = await ingestFile(file);
      setToast({ message: `${result.item_count} conversation(s) ingested from ${file.name}`, type: "success" });
      setTimeout(() => navigate("/archive"), 1500);
    } catch (err) {
      const detail = err instanceof ApiError ? err.detail : "File ingest failed. Please try again.";
      setToast({ message: detail, type: "error" });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFileSubmit(file);
  };

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFileSubmit(file);
  };

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Ingest Conversations</h1>

      {/* Tab switcher */}
      <div className="flex gap-1 mb-6 border-b">
        {(["paste", "file"] as Tab[]).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={cn(
              "px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors",
              activeTab === tab
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            )}
            aria-selected={activeTab === tab}
            role="tab"
          >
            {tab === "paste" ? (
              <><FileText className="inline h-4 w-4 mr-1.5" aria-hidden="true" />Paste Text</>
            ) : (
              <><Upload className="inline h-4 w-4 mr-1.5" aria-hidden="true" />Upload File</>
            )}
          </button>
        ))}
      </div>

      {/* Paste tab */}
      {activeTab === "paste" && (
        <form onSubmit={handlePasteSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="source-name" className="text-sm font-medium">
              Source name <span className="text-muted-foreground">(optional)</span>
            </label>
            <input
              id="source-name"
              type="text"
              value={sourceName}
              onChange={(e) => setSourceName(e.target.value)}
              placeholder="e.g. ChatGPT session 2026-01-15"
              className="rounded-md border border-input px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label htmlFor="paste-content" className="text-sm font-medium">
              Content <span className="text-red-500">*</span>
            </label>
            <textarea
              id="paste-content"
              value={pasteContent}
              onChange={(e) => setPasteContent(e.target.value)}
              rows={12}
              placeholder="Paste plain text, Markdown, or JSON export here…"
              className="rounded-md border border-input px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-primary resize-vertical"
              required
            />
            <p className="text-xs text-muted-foreground">
              Supported: plain text, Markdown, ChatGPT JSON export, Claude JSON export, generic JSON
            </p>
          </div>
          <Button type="submit" disabled={isSubmitting || !pasteContent.trim()}>
            {isSubmitting ? "Ingesting…" : "Ingest"}
          </Button>
        </form>
      )}

      {/* File upload tab */}
      {activeTab === "file" && (
        <div className="flex flex-col gap-4">
          <div
            onDrop={handleDrop}
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onClick={() => fileInputRef.current?.click()}
            className={cn(
              "flex flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed p-12 cursor-pointer transition-colors",
              isDragging
                ? "border-primary bg-primary/5"
                : "border-muted-foreground/30 hover:border-primary/50"
            )}
            role="button"
            aria-label="Click or drag and drop a file to upload"
          >
            <Upload className="h-10 w-10 text-muted-foreground" aria-hidden="true" />
            <div className="text-center">
              <p className="text-sm font-medium">
                {isDragging ? "Drop file here" : "Click to browse or drag and drop"}
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                Supported: .json, .txt, .md — max 50 MB
              </p>
            </div>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept=".json,.txt,.md"
            className="hidden"
            onChange={handleFileInputChange}
            aria-label="File input"
          />
          {isSubmitting && (
            <p className="text-sm text-center text-muted-foreground">Uploading and ingesting…</p>
          )}
        </div>
      )}

      {toast && (
        <Toast
          message={toast.message}
          type={toast.type}
          onDismiss={() => setToast(null)}
        />
      )}
    </div>
  );
}
```
  </action>
  <acceptance_criteria>
    - `grep -n "activeTab.*paste\|activeTab.*file" frontend/src/pages/IngestPage.tsx | wc -l` returns ≥ 2 (tab state)
    - `grep -n "ingestText\|ingestFile" frontend/src/pages/IngestPage.tsx | wc -l` returns ≥ 2
    - `grep -n "navigate.*archive" frontend/src/pages/IngestPage.tsx` returns 1 line (redirect after success)
    - `grep -n "aria-label\|role=\"tab\"\|aria-selected" frontend/src/pages/IngestPage.tsx | wc -l` returns ≥ 3 (accessibility)
    - `grep -n "onDrop\|onDragOver\|onDragLeave" frontend/src/pages/IngestPage.tsx | wc -l` returns 3 (drag-and-drop)
    - `grep -n "accept=\".json,.txt,.md\"" frontend/src/pages/IngestPage.tsx` returns 1 line
    - `grep -n "50 MB" frontend/src/pages/IngestPage.tsx` returns ≥ 1 line
    - `grep -n "Toast" frontend/src/pages/IngestPage.tsx` returns ≥ 2 lines (import + usage)
  </acceptance_criteria>
</task>

</tasks>

<verification>
After all tasks complete (requires Plan 01-01 + 01-02 + 01-04 done):

1. Test paste ingest:
   ```bash
   curl -s -X POST http://localhost:8000/api/ingest \
     -H "Content-Type: application/json" \
     -d '{"content": "User: Hello\nAssistant: Hi there, how can I help?", "source_name": "test"}' | python3 -m json.tool
   ```
   Expected: `{"status": "accepted", "item_count": 1, "archive_ids": ["...uuid..."]}` with HTTP 202.

2. Test ChatGPT JSON detection:
   ```bash
   curl -s -X POST http://localhost:8000/api/ingest \
     -H "Content-Type: application/json" \
     -d '{"content": "{\"conversations\": [{\"id\": \"test\", \"title\": \"Hello\", \"mapping\": {}}]}", "source_name": "chatgpt"}' | python3 -m json.tool
   ```
   Expected: `"item_count": 1`, `"status": "accepted"`.

3. Test DB persistence:
   ```bash
   docker compose exec recalium-postgres psql -U recalium -d recalium -c "SELECT id, source_type, conversation_count, ingested_at FROM raw_archive ORDER BY ingested_at DESC LIMIT 5;"
   ```
   Must return rows from the two previous curl calls.

4. Test audit event:
   ```bash
   docker compose exec recalium-postgres psql -U recalium -d recalium -c "SELECT event_type, actor, operation_metadata FROM audit_events ORDER BY occurred_at DESC LIMIT 3;"
   ```
   Must show `event_type='ingest'` rows with `actor='user_ui'`.

5. Test validation:
   ```bash
   curl -s -X POST http://localhost:8000/api/ingest \
     -H "Content-Type: application/json" \
     -d '{"content": "x"}' | python3 -m json.tool
   ```
   Expected: HTTP 422 with detail about content too short.
</verification>

<must_haves>
1. `POST /api/ingest` returns HTTP 202 (not 200, not 201 — Accepted per async ingest contract) within P95 ≤ 1s with `{"status":"accepted","item_count":N,"archive_ids":[...]}`. Verified by curl test above.
2. All five format types are correctly detected by `detect_and_parse()`: `chatgpt_json` (dict with "conversations" key), `claude_json` (list with "uuid"+"chat_messages" items), `generic_json` (other JSON), `paste_markdown` (has # headers), `paste_text` (plain text). Verified by unit tests in Plan 01-08.
3. Every ingest creates both a `raw_archive` row AND an `audit_event` row in the same transaction — if either fails, both are rolled back. Verified: `grep "session.flush()" backend/app/domain/ingest/service.py` returns 1 line; both objects added before any commit.
</must_haves>
