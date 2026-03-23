---
phase: 02-processing-pipeline
plan: "01"
subsystem: derived-memory-schema
tags: [migration, orm, pgvector, fts, schema, derived-memory]
dependency_graph:
  requires: [01-foundation]
  provides: [summaries-table, facts-table, embeddings-table, fts_entries-table, conflict_groups-table]
  affects: [02-02-test-scaffold, 02-03-worker, 02-04-policy-gate, 02-05-llm-handlers]
tech_stack:
  added: [pgvector==0.4.2]
  patterns: [SQLAlchemy Mapped columns with lambda defaults, Alembic raw SQL for pgvector/tsvector, source_status ENUM cascade contract]
key_files:
  created:
    - backend/alembic/versions/0002_derived_memory.py
    - backend/app/domain/derived_memory/__init__.py
    - backend/app/domain/derived_memory/models.py
  modified:
    - backend/pyproject.toml
    - backend/app/main.py
    - backend/uv.lock
decisions:
  - "Use ALTER TABLE for vector(384) and TSVECTOR columns since SQLAlchemy sa.Column() does not support pgvector/tsvector types natively in create_table"
  - "Create conflict_groups before facts so the FK constraint can reference it"
  - "source_status Enum defined with create_type=False in both ORM and migration since the type was created in 0001"
metrics:
  duration_seconds: 299
  completed_date: "2026-03-23"
  tasks_completed: 2
  files_created: 3
  files_modified: 3
requirements_addressed: [PIPE-01, PIPE-02, CANM-06]
---

# Phase 02 Plan 01: Derived Memory Schema Summary

**One-liner:** Alembic migration 0002 + SQLAlchemy ORM models for all five derived-memory tables (summaries, facts, embeddings, fts_entries, conflict_groups) with pgvector Vector(384) HNSW and PostgreSQL FTS GIN indexes.

---

## What Was Built

### Migration 0002 (`backend/alembic/versions/0002_derived_memory.py`)

Creates all five derived-memory tables on top of migration 0001:

| Table | Key Columns | Indexes |
|-------|-------------|---------|
| `conflict_groups` | `id`, `group_type`, `source_status`, `created_at`, `resolved_at` | `ix_conflict_groups_source_status` |
| `summaries` | `id`, `raw_archive_id`, `summary_text`, `model_used`, `derivation_method`, `source_status`, `created_at` | `ix_summaries_raw_archive_id`, `ix_summaries_source_status` |
| `facts` | `id`, `raw_archive_id`, `fact_text`, `source_span`, `confidence_tier`, `derivation_method`, `derivation_model`, `conflict_group_id`, `source_status`, `created_at` | `ix_facts_raw_archive_id`, `ix_facts_source_status`, partial `ix_facts_conflict_group_id` |
| `embeddings` | `id`, `raw_archive_id`, `embedding` (vector(384)), `embedding_model`, `source_status`, `created_at` | HNSW `ix_embeddings_vector`, `ix_embeddings_raw_archive_id`, `ix_embeddings_source_status` |
| `fts_entries` | `id`, `raw_archive_id`, `text_content`, `search_vector` (TSVECTOR), `source_status`, `created_at` | GIN `ix_fts_search_vector`, `ix_fts_raw_archive_id`, `ix_fts_source_status` |

**Cascade contract honored:** Every table has `raw_archive_id FK → raw_archive.id ON DELETE CASCADE` and `source_status ENUM NOT NULL DEFAULT 'active'`.

**No re-creation:** Does NOT re-create `pgvector` extension or `source_status` ENUM (both already in 0001).

### ORM Models (`backend/app/domain/derived_memory/models.py`)

Five SQLAlchemy 2.x `Mapped` models mirroring the migration schema:
- `ConflictGroup` — conflict group container
- `Summary` — LLM-generated summary per raw archive item
- `Fact` — extracted fact with `source_span`, `confidence_tier`, `derivation_method`, `derivation_model` per PIPE-02
- `Embedding` — `Vector(384)` embedding from `all-MiniLM-L6-v2`
- `FtsEntry` — FTS index entry with `TSVECTOR` search_vector

All models use `lambda: datetime.now(timezone.utc)` for datetime defaults (not deprecated `utcnow()`). All models import from `app.infrastructure.db.Base`.

### pyproject.toml + uv.lock

Added `pgvector==0.4.2` to main `[project.dependencies]`. Installed in venv (with numpy 2.4.3 as transitive dependency).

### main.py

Added `import app.domain.derived_memory.models  # noqa: F401` inside `_assert_no_keys_in_schema()` so the startup security assertion scans derived memory models for prohibited column name patterns at boot.

---

## Deviations from Plan

None — plan executed exactly as written.

---

## Verification Results

| Check | Result |
|-------|--------|
| `from app.domain.derived_memory.models import Summary, Fact, Embedding, FtsEntry, ConflictGroup` | ✅ OK |
| `source_status` mapped_column count in models.py | ✅ 5 (one per model) |
| `pgvector==0.4.2` in pyproject.toml | ✅ Present |
| `import app.domain.derived_memory.models` in main.py | ✅ Present |
| `down_revision = "0001"` in migration | ✅ Present |
| Migration Python syntax valid | ✅ ast.parse() OK |
| `source_span`, `confidence_tier`, `derivation_method`, `derivation_model` in Fact | ✅ All present |
| `Vector(384)` in Embedding model | ✅ Present |
| `TSVECTOR` in FtsEntry model | ✅ Present |
| No `CREATE EXTENSION` in migration | ✅ Correct |
| No `CREATE TYPE source_status` in migration | ✅ Correct |
| No `_key`, `_secret`, `_token`, `_password` column suffixes | ✅ Clean |

---

## Task Commits

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Add pgvector package and create derived_memory ORM models | e054ae1 | backend/pyproject.toml, backend/uv.lock, backend/app/domain/derived_memory/__init__.py, backend/app/domain/derived_memory/models.py, backend/app/main.py |
| 2 | Write Alembic migration 0002 for derived-memory tables | 96c83d6 | backend/alembic/versions/0002_derived_memory.py |

---

## Self-Check: PASSED

All created files exist and all task commits are present in git history.
