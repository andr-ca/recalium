---
wave: 3
depends_on:
  - 01-02-postgres-schema-PLAN.md
  - 01-04-fastapi-skeleton-PLAN.md
requirements_addressed: [INGT-03, WEBUI-01]
files_modified:
  - backend/app/api/routes/archive.py
  - frontend/src/pages/ArchivePage.tsx
  - frontend/src/components/ArchiveItemCard.tsx
autonomous: true
---

<objective>
Implement the Archive API (GET /api/archive with pagination and optional keyword search) and the Archive page UI (card list with source badge, timestamp, conversation count, and status badge). After this plan, items ingested in Plan 01-05 appear in the Archive UI within P95 ≤ 1s.

Purpose: Satisfies INGT-03 (item visible in Archive UI within 1s) and WEBUI-01 (archive page in left-nav shell).
Output: backend archive route; frontend ArchivePage + ArchiveItemCard components.
</objective>

<tasks>

<task id="1" name="Implement GET /api/archive with pagination and soft-delete filter">
  <read_first>
    - backend/app/domain/archive/models.py (RawArchiveItem — deleted_at, source_type, etc.)
    - backend/app/infrastructure/db.py (get_session)
    - backend/alembic/versions/0001_initial.py (ix_raw_archive_ingested_at index)
    - .planning/phases/01-foundation/01-CONTEXT.md (D-10 soft-delete filter, D-17 card list fields)
  </read_first>
  <action>
Replace the stub in `backend/app/api/routes/archive.py` with the full implementation:

```python
"""Archive routes — GET /api/archive with pagination."""
from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.archive.models import RawArchiveItem
from app.infrastructure.db import get_session

logger = logging.getLogger(__name__)
router = APIRouter()


class ArchiveItemOut(BaseModel):
    """Archive item response schema — safe for client consumption."""
    id: str
    source_type: str
    source_name: str | None
    conversation_count: int
    ingested_at: str  # ISO 8601 string
    status_badge: str  # Phase 1: always "Ingested"; Phase 2+ adds pipeline status

    model_config = {"from_attributes": True}


class ArchiveListResponse(BaseModel):
    items: list[ArchiveItemOut]
    total: int
    offset: int
    limit: int


def _source_badge_label(source_type: str) -> str:
    """Human-readable source label for badge display."""
    labels = {
        "chatgpt_json": "ChatGPT",
        "claude_json": "Claude",
        "generic_json": "JSON",
        "paste_text": "Text Paste",
        "paste_markdown": "Markdown",
    }
    return labels.get(source_type, source_type.replace("_", " ").title())


@router.get("", response_model=ArchiveListResponse)
async def list_archive(
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
    limit: int = Query(default=50, ge=1, le=200, description="Page size (max 200)"),
    q: str | None = Query(default=None, description="Keyword filter on source_name (future: FTS)"),
    session: AsyncSession = Depends(get_session),
) -> ArchiveListResponse:
    """GET /api/archive — returns paginated raw archive items.

    Filters:
    - Always excludes soft-deleted items (deleted_at IS NULL).
    - Optional keyword filter on source_name (basic ILIKE in Phase 1; FTS in Phase 3).

    Ordered by ingested_at DESC (newest first).
    """
    # Base query: exclude soft-deleted items (D-10 — ALL read queries must filter)
    base_stmt = select(RawArchiveItem).where(RawArchiveItem.deleted_at.is_(None))

    # Optional keyword filter
    if q and q.strip():
        search_term = f"%{q.strip()}%"
        base_stmt = base_stmt.where(
            RawArchiveItem.source_name.ilike(search_term)
        )

    # Count total matching items
    count_stmt = select(func.count()).select_from(base_stmt.subquery())
    total_result = await session.execute(count_stmt)
    total = total_result.scalar_one()

    # Paginated results, ordered newest first
    items_stmt = (
        base_stmt
        .order_by(desc(RawArchiveItem.ingested_at))
        .offset(offset)
        .limit(limit)
    )
    items_result = await session.execute(items_stmt)
    items = list(items_result.scalars().all())

    return ArchiveListResponse(
        items=[
            ArchiveItemOut(
                id=str(item.id),
                source_type=_source_badge_label(item.source_type),
                source_name=item.source_name,
                conversation_count=item.conversation_count,
                ingested_at=item.ingested_at.isoformat(),
                status_badge="Ingested",  # Phase 1 only; Phase 2 adds pipeline status
            )
            for item in items
        ],
        total=total,
        offset=offset,
        limit=limit,
    )
```
  </action>
  <acceptance_criteria>
    - `grep -n "deleted_at.is_(None)" backend/app/api/routes/archive.py` returns 1 line (soft-delete filter)
    - `grep -n "status_badge.*Ingested" backend/app/api/routes/archive.py` returns 1 line
    - `grep -n "order_by.*desc.*ingested_at" backend/app/api/routes/archive.py` returns 1 line
    - `grep -n "offset.*limit" backend/app/api/routes/archive.py | wc -l` returns ≥ 2 (pagination params)
    - `grep -n "func.count" backend/app/api/routes/archive.py` returns 1 line (total count query)
    - `grep -n "ilike" backend/app/api/routes/archive.py` returns 1 line (keyword filter)
    - Via curl (after Plan 01-05 ran):
      `curl -s http://localhost:8000/api/archive | python3 -c "import sys,json; d=json.load(sys.stdin); assert 'items' in d and 'total' in d; print('OK')"` — prints "OK"
  </acceptance_criteria>
</task>

<task id="2" name="Implement ArchivePage UI with card list, badges, and empty state">
  <read_first>
    - frontend/src/lib/api.ts (listArchive, ArchiveItem, ArchiveListResponse)
    - frontend/src/components/ui/badge.tsx
    - .planning/phases/01-foundation/01-CONTEXT.md (D-17 archive card fields: source name, timestamp, item count, status badge)
  </read_first>
  <action>
Create `frontend/src/components/ArchiveItemCard.tsx`:

```typescript
import { Badge } from "@/components/ui/badge";
import type { ArchiveItem } from "@/lib/api";

interface ArchiveItemCardProps {
  item: ArchiveItem;
}

function formatDate(isoString: string): string {
  const date = new Date(isoString);
  return date.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const SOURCE_BADGE_VARIANTS: Record<string, "default" | "secondary" | "outline"> = {
  ChatGPT: "default",
  Claude: "secondary",
  JSON: "outline",
  "Text Paste": "outline",
  Markdown: "outline",
};

export function ArchiveItemCard({ item }: ArchiveItemCardProps) {
  const badgeVariant = SOURCE_BADGE_VARIANTS[item.source_type] ?? "outline";

  return (
    <article
      className="rounded-lg border border-border bg-card px-5 py-4 flex items-start gap-4 hover:bg-muted/30 transition-colors"
      aria-label={`Archive item: ${item.source_name ?? item.source_type}`}
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap mb-1">
          <Badge variant={badgeVariant}>{item.source_type}</Badge>
          <Badge variant="success">{item.status_badge}</Badge>
        </div>
        <h2 className="text-sm font-semibold truncate">
          {item.source_name ?? item.source_type}
        </h2>
        <p className="text-xs text-muted-foreground mt-1">
          {item.conversation_count === 1
            ? "1 conversation"
            : `${item.conversation_count} conversations`}{" "}
          · Ingested {formatDate(item.ingested_at)}
        </p>
      </div>
    </article>
  );
}
```

Replace the stub `frontend/src/pages/ArchivePage.tsx` with the full implementation:

```typescript
import * as React from "react";
import { ArchiveItemCard } from "@/components/ArchiveItemCard";
import { listArchive, ApiError, type ArchiveItem } from "@/lib/api";

type LoadState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "success"; items: ArchiveItem[]; total: number }
  | { status: "error"; message: string };

const PAGE_SIZE = 50;

export function ArchivePage() {
  const [state, setState] = React.useState<LoadState>({ status: "idle" });
  const [searchQuery, setSearchQuery] = React.useState("");
  const [offset, setOffset] = React.useState(0);

  const loadArchive = React.useCallback(async (q: string, off: number) => {
    setState({ status: "loading" });
    try {
      const result = await listArchive({ offset: off, limit: PAGE_SIZE, q: q || undefined });
      setState({ status: "success", items: result.items, total: result.total });
    } catch (err) {
      const message = err instanceof ApiError ? err.detail : "Failed to load archive.";
      setState({ status: "error", message });
    }
  }, []);

  // Initial load
  React.useEffect(() => {
    loadArchive("", 0);
  }, [loadArchive]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setOffset(0);
    loadArchive(searchQuery, 0);
  };

  const handlePrevPage = () => {
    const newOffset = Math.max(0, offset - PAGE_SIZE);
    setOffset(newOffset);
    loadArchive(searchQuery, newOffset);
  };

  const handleNextPage = () => {
    if (state.status !== "success") return;
    const newOffset = offset + PAGE_SIZE;
    if (newOffset < state.total) {
      setOffset(newOffset);
      loadArchive(searchQuery, newOffset);
    }
  };

  const total = state.status === "success" ? state.total : 0;

  return (
    <div className="max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Archive</h1>
        {state.status === "success" && (
          <span className="text-sm text-muted-foreground">
            {state.total} item{state.total !== 1 ? "s" : ""}
          </span>
        )}
      </div>

      {/* Search */}
      <form onSubmit={handleSearch} className="flex gap-2 mb-6">
        <input
          type="search"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Filter by source name…"
          aria-label="Search archive"
          className="flex-1 rounded-md border border-input px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
        />
        <button
          type="submit"
          className="rounded-md bg-primary text-primary-foreground px-4 py-2 text-sm font-medium hover:bg-primary/90 transition-colors"
        >
          Search
        </button>
      </form>

      {/* States */}
      {state.status === "loading" && (
        <div
          role="status"
          aria-label="Loading archive"
          className="flex items-center justify-center py-12 text-muted-foreground text-sm"
        >
          Loading…
        </div>
      )}

      {state.status === "error" && (
        <div
          role="alert"
          className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700"
        >
          {state.message}
        </div>
      )}

      {state.status === "success" && state.items.length === 0 && (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <p className="text-lg font-semibold mb-2">No items yet</p>
          <p className="text-sm text-muted-foreground">
            {searchQuery
              ? `No items match "${searchQuery}". Try a different search.`
              : "Ingest your first conversation to get started."}
          </p>
        </div>
      )}

      {state.status === "success" && state.items.length > 0 && (
        <>
          <ul className="flex flex-col gap-3" aria-label="Archive items">
            {state.items.map((item) => (
              <li key={item.id}>
                <ArchiveItemCard item={item} />
              </li>
            ))}
          </ul>

          {/* Pagination */}
          {total > PAGE_SIZE && (
            <div className="flex items-center justify-between mt-6 text-sm text-muted-foreground">
              <span>
                Showing {offset + 1}–{Math.min(offset + PAGE_SIZE, total)} of {total}
              </span>
              <div className="flex gap-2">
                <button
                  onClick={handlePrevPage}
                  disabled={offset === 0}
                  className="rounded-md border px-3 py-1.5 text-xs hover:bg-muted disabled:opacity-40 disabled:cursor-not-allowed"
                  aria-label="Previous page"
                >
                  ← Previous
                </button>
                <button
                  onClick={handleNextPage}
                  disabled={offset + PAGE_SIZE >= total}
                  className="rounded-md border px-3 py-1.5 text-xs hover:bg-muted disabled:opacity-40 disabled:cursor-not-allowed"
                  aria-label="Next page"
                >
                  Next →
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
```
  </action>
  <acceptance_criteria>
    - `grep -n "ArchiveItemCard" frontend/src/pages/ArchivePage.tsx | wc -l` returns ≥ 2 (import + usage)
    - `grep -n "listArchive" frontend/src/pages/ArchivePage.tsx` returns ≥ 1 line
    - `grep -n "status.*loading\|status.*success\|status.*error\|status.*idle" frontend/src/pages/ArchivePage.tsx | wc -l` returns 4 (all states)
    - `grep -n "No items yet" frontend/src/pages/ArchivePage.tsx` returns 1 line (empty state)
    - `grep -n "aria-label\|role=" frontend/src/pages/ArchivePage.tsx | wc -l` returns ≥ 3 (accessibility)
    - `grep -n "deleted_at.is_(None)" backend/app/api/routes/archive.py` returns 1 line (soft-delete filter always applied)
    - `grep -n "status_badge.*Ingested" backend/app/api/routes/archive.py` returns 1 line
  </acceptance_criteria>
</task>

</tasks>

<verification>
After all tasks complete (requires Plan 01-01 + 01-02 + 01-04 + 01-05 done):

1. Ingest a test item then check it appears in archive:
   ```bash
   # Ingest
   curl -s -X POST http://localhost:8000/api/ingest \
     -H "Content-Type: application/json" \
     -d '{"content": "User: What is 2+2?\nAssistant: 4.", "source_name": "Test Conversation"}' | python3 -m json.tool

   # Archive list — must show the item
   curl -s "http://localhost:8000/api/archive" | python3 -c "
   import sys, json
   d = json.load(sys.stdin)
   assert d['total'] >= 1
   assert d['items'][0]['source_name'] == 'Text Paste' or 'Test' in str(d['items'])
   print('Archive list OK, total:', d['total'])
   "
   ```

2. Test keyword filter:
   ```bash
   curl -s "http://localhost:8000/api/archive?q=Test" | python3 -c "
   import sys, json
   d = json.load(sys.stdin)
   print('Filter result total:', d['total'])
   "
   ```

3. Test pagination:
   ```bash
   curl -s "http://localhost:8000/api/archive?offset=0&limit=2" | python3 -c "
   import sys, json
   d = json.load(sys.stdin)
   assert d['limit'] == 2
   assert d['offset'] == 0
   print('Pagination OK')
   "
   ```

4. Visual check in browser: navigate to `/archive` — must show cards with source badge (e.g. "Text Paste"), "Ingested" green badge, source name, conversation count, timestamp.
</verification>

<must_haves>
1. `GET /api/archive` ALWAYS filters `WHERE deleted_at IS NULL` — soft-deleted items never appear in results. Verified: `grep "deleted_at.is_(None)" backend/app/api/routes/archive.py` returns 1 line.
2. Each archive card shows: source type badge (ChatGPT / Claude / JSON / Text Paste / Markdown), "Ingested" status badge, source name, conversation count, ingested_at timestamp. Verified visually in browser.
3. Empty state is displayed when archive is empty (not a blank page or error). Verified: `grep "No items yet" frontend/src/pages/ArchivePage.tsx` returns 1 line.
</must_haves>
