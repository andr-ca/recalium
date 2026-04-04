# Plan 03-01 Implementation Summary

## What Was Implemented

### ORM Models (Task 1)

**`backend/app/domain/canonical_memory/models.py`**
- `CanonicalMemoryItem` table (`canonical_memory`)
- Nullable FKs to `raw_archive.id` and `facts.id` (both `SET NULL` on delete)
- `source_status` cascade contract column (references existing ENUM)
- `search_vector` TSVECTOR column (DB-generated, do not set manually)
- `promoted_from`, `promoted_by`, `provenance_note` provenance columns

**`backend/app/domain/review_queue/models.py`**
- `ReviewQueueItem` table (`review_queue_items`)
- Non-nullable FK to `conflict_groups.id` (`CASCADE` on delete)
- `source_status` cascade contract column
- `item_type`, `status`, `resolution_note`, `resolved_by`, `resolved_at` workflow columns

### Migration (Task 2)

**`backend/migrations/versions/0003_canonical_memory.py`**
- Chains from `0002` via `down_revision = "0002"`
- Uses `postgresql.ENUM(name="source_status", create_type=False)` — does NOT re-create the existing ENUM type
- Creates `canonical_memory` with partial indexes on nullable FKs and a GIN FTS index on `search_vector` (DB-generated stored column)
- Creates `review_queue_items` with indexes on `status`, `conflict_group_id`, `source_status`
- `downgrade()` drops both tables in reverse dependency order

### main.py Update
- Added `canonical_memory.models` and `review_queue.models` to `_assert_no_keys_in_schema()` import block

## Verification

```
ORM models import OK
down_revision = "0002"
postgresql.ENUM(name="source_status", create_type=False),   (×2)
import app.domain.canonical_memory.models  # noqa: F401
import app.domain.review_queue.models  # noqa: F401
```

## Critical Bug Fixed

The plan noted that `sa.Enum("active", "source_removed", name="source_status", create_type=False)` in migrations still emits `CREATE TYPE` in SQLAlchemy 2.x. The migration uses `postgresql.ENUM(name="source_status", create_type=False)` (no values, just the name) to safely reference the pre-existing type.
