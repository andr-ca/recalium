# Phase 1: Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-22
**Phase:** 01-foundation
**Mode:** --auto (all decisions auto-selected using recommended defaults)
**Areas discussed:** Project Layout, Docker Topology, Database Schema, BYOK Key Storage, Ingest UX, Web UI Shell

---

## Project Layout

| Option | Description | Selected |
|--------|-------------|----------|
| `backend/` + `frontend/` at root | Standard FastAPI + Vite monorepo layout; Docker context at repo root | ✓ |
| Flat root with `app/` + `ui/` | Less conventional for Python projects | |

**Selected:** `backend/` + `frontend/` at repo root, Docker build context at repo root
**Notes:** Auto-selected as the standard layout for this stack combination.

---

## Docker Topology

| Option | Description | Selected |
|--------|-------------|----------|
| Bind mounts (`./data/postgres`, `./backups`, `./import`) | Data survives `docker compose down`; explicit host paths; no `-v` risk | ✓ |
| Named volumes | More portable but risky with `down -v`; forbidden by pitfalls doc | |

**BYOK paths:** `./data/postgres`, `./backups`, `./import`
**dev/prod split:** `docker-compose.yml` (base/prod) + `docker-compose.override.yml` (dev hot-reload)
**Notes:** Bind mounts are mandatory per research pitfall #5 (Docker volume destruction). Pre-created in Phase 1 before Phase 5 needs them.

---

## Database Schema (Phase 1 tables)

| Option | Description | Selected |
|--------|-------------|----------|
| `source_status` column on every derived table | Simple, queryable, no join overhead; enforced at column level | ✓ |
| Separate suppression join table | More flexible but adds query complexity and join overhead | |
| App-layer soft-delete only | No DB-level guarantee; easy to bypass | |

**Soft-delete on raw archive:** `deleted_at TIMESTAMP WITH TIME ZONE NULL`
**Hard deletion UI:** deferred to Phase 4
**Notes:** Cascade schema must be in Phase 1 to prevent the most expensive data integrity pitfall (orphaned derived data). Auto-selected as the correct long-term pattern.

---

## BYOK Key Storage

| Option | Description | Selected |
|--------|-------------|----------|
| `.env` only; DB stores fingerprint + bool | Keys never in DB; fingerprint allows settings UI to show "configured" state | ✓ |
| DB encrypted column | Key in DB even if encrypted; appears in pg_dump | |
| OS keychain / secrets manager | Complex, platform-specific, overkill for local-first | |

**Validation UI:** Inline status badge per provider (no modal)
**Notes:** `.env`-only is the architectural rule. Test assertion to be added that scans schema for key columns.

---

## Ingest UX

| Option | Description | Selected |
|--------|-------------|----------|
| Single page with Paste / File Upload tabs | Unified view; same endpoint; less navigation | ✓ |
| Separate pages for paste and upload | More nav items; cleaner per-mode UX but more surface to build | |

**Post-ingest flow:** Toast confirmation → navigate to Archive
**Archive card content:** Source name, ingested-at, item count, "Ingested" badge (Phase 2 adds pipeline status)
**Notes:** Single page with tab toggle is recommended for v1 simplicity.

---

## Web UI Shell

| Option | Description | Selected |
|--------|-------------|----------|
| Left-nav with disabled items for future phases visible | Users see what's coming; grayed out with tooltip | ✓ |
| Left-nav with only enabled items | Cleaner but gives no roadmap visibility | |

**Nav items in order:** Ingest, Archive, Facts (disabled), Canonical (disabled), Search (disabled), Review Queue (disabled), Audit (disabled), Settings
**Browser support:** Chrome/Chromium only in v1
**Notes:** Showing disabled future items aligns with the "infrastructure, not just a feature" positioning.

---

## the agent's Discretion

- Specific shadcn/ui component selection for nav, cards, forms
- Loading and empty state designs
- Alembic migration numbering convention
- Vite dev server proxy configuration

## Deferred Ideas

None

---

*Discussion log: Phase 01-foundation*
*Date: 2026-03-22*
*Mode: auto*
