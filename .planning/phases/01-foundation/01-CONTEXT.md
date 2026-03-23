# Phase 1: Foundation - Context

**Gathered:** 2026-03-22
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver a working local platform that a user can actually start using: ingest conversations via paste or file upload, browse the raw archive, validate BYOK API keys, and restart the containers without data loss. This phase establishes the Docker topology, PostgreSQL schema (with cascade-aware `source_status` flags from day one), FastAPI skeleton, web UI shell, and the BYOK key storage pattern. No derived memory, no search, no processing pipeline — those are Phase 2+.

**In scope:** Docker setup, PostgreSQL + pgvector + FTS, Alembic migrations, raw archive ingest (paste + file), web UI shell (left-nav, Ingest page, Archive page, Settings/BYOK page), BYOK key validation (lightweight test call, no key in DB), bind-mount volume setup.

**Not in scope:** Processing pipeline, search, semantic embeddings, worker loop, canonical memory, MCP server, backup/restore UI, first-run wizard.

</domain>

<decisions>
## Implementation Decisions

### Project Layout

- **D-01:** Monorepo with `backend/` and `frontend/` directories at repo root. Docker build context is the repo root.
- **D-02:** Backend structure: `backend/app/` with `domain/` (subdirectory per module: `ingest/`, `archive/`, `policy/`, `audit/`, `jobs/`), `api/` (route handlers, thin adapters), `worker/` (loop, dispatcher), `infrastructure/` (db session, settings, BYOK config). Follows the `component-boundaries.md` module map exactly.
- **D-03:** Frontend structure: `frontend/src/` with `components/`, `pages/`, `hooks/`, `lib/` (API client). Standard Vite + shadcn/ui layout.
- **D-04:** Package managers: `uv` for Python (`pyproject.toml` at `backend/`), `pnpm` for Node (`package.json` at `frontend/`).

### Docker Topology

- **D-05:** Two containers: `recalium-app` (FastAPI + static serving) and `recalium-postgres`. No additional containers in v1.
- **D-06:** Bind-mount paths (not named volumes): `./data/postgres:/var/lib/postgresql/data` for PG data, `./backups:/app/backups` for backup output, `./import:/app/import` for watched folder (pre-created in Phase 1, used in Phase 5). These paths are `.gitignore`d.
- **D-07:** Single `docker-compose.yml` as the production base; `docker-compose.override.yml` for development (hot-reload via `--reload`, exposed ports for direct DB access during dev). Production uses only the base file.
- **D-08:** Container entrypoint runs `alembic upgrade head` before starting Uvicorn. pgvector extension created in migration `0001_initial.py`. No separate migration step required by the user.

### Database Schema (Phase 1 tables)

- **D-09:** Every derived table created in Phase 1 (and all future phases) includes a `source_status` column: `ENUM('active', 'source_removed') NOT NULL DEFAULT 'active'`. This is the cascade deletion marker — set in Phase 1 even for tables where deletion UI ships in Phase 4.
- **D-10:** Raw archive uses soft-delete: `deleted_at TIMESTAMP WITH TIME ZONE NULL`. Hard deletion with cascade propagation ships in Phase 4 (deletion cascade UI). In Phase 1, items with `deleted_at IS NOT NULL` are excluded from all read queries.
- **D-11:** `pgvector` extension enabled in migration 001; embedding columns added in Phase 2. The extension install does not block Phase 1 operation.

### BYOK Key Storage Pattern

- **D-12:** API keys live only in `.env` (or environment variables injected at runtime). The database stores only: `{provider}_key_fingerprint` (last 4 chars of key) and `{provider}_key_configured: boolean`. Plaintext keys are never written to any DB table, ever. This rule is enforced by a test assertion that scans schema column definitions.
- **D-13:** BYOK settings UI presents one section per provider (OpenAI, Anthropic, Ollama). Each has: a masked input field, a "Validate" button, and an inline status badge (✓ Valid / ✗ Invalid — [error detail] / ⚠ Insufficient permissions). No modal. Validation calls a lightweight test endpoint (e.g., `models.list` for OpenAI) before persisting the fingerprint.
- **D-14:** Ollama endpoint takes a URL + optional key (some Ollama deployments require auth). OpenAI and Anthropic take only an API key. The settings form adapts accordingly.

### Ingest UX

- **D-15:** Single Ingest page with two modes toggled via tab: "Paste" (textarea, plain text or Markdown) and "File Upload" (drag-and-drop zone + file browser, accepts `.json`, `.txt`, `.md`). Both submit to the same backend endpoint.
- **D-16:** On successful ingest, the UI shows a brief confirmation toast ("N conversations ingested") and navigates to the Archive page. No polling or live status update in Phase 1 — processing status UI ships in Phase 2.
- **D-17:** Archive page shows a card list: source name, ingested-at timestamp, item count (conversations or turns), and a simple status badge. In Phase 1, badge shows only "Ingested" — the full pipeline status (Processing / Done / Failed) ships in Phase 2.
- **D-18:** Supported ingest formats in Phase 1: plain text / Markdown (paste), ChatGPT JSON export, Claude JSON export, generic JSON. Format detection is automatic based on structure.

### Web UI Shell

- **D-19:** Left-nav layout with these items in order: Ingest, Archive, Facts (disabled, Phase 2), Canonical (disabled, Phase 2), Search (disabled, Phase 2+), Review Queue (disabled, Phase 2+), Audit (disabled, Phase 3+), Settings. Disabled items are visible but grayed out with a tooltip "Available in a future update."
- **D-20:** Chrome/Chromium only in v1. No polyfills for other browsers.
- **D-21:** No authentication in v1 (single-user local-first). The broader-than-localhost exposure requirement (PRIV-06) ships in Phase 4.

### the agent's Discretion

- Specific shadcn/ui component choices for the left-nav, card list, and form elements — use standard shadcn patterns.
- Loading/empty state designs for Archive and Ingest pages.
- Exact Alembic migration numbering and file naming convention.
- Whether Vite dev server proxies API calls or uses a separate dev port (standard Vite proxy is fine).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture

- `docs/architecture/component-boundaries.md` — Module map, dependency direction rules, sequence flows A and B, what each module owns/must-not-own
- `docs/architecture/container-topology.md` — Two-container topology, container responsibilities
- `docs/architecture/delivery-phases.md` — Phase 1 scope: local Docker topology, PostgreSQL + FTS + pgvector, raw archive ingest, basic web UI shell, provenance and audit foundations
- `docs/architecture/tech-stack.md` — Committed stack (FastAPI, PostgreSQL, React, versions)

### Requirements

- `.planning/REQUIREMENTS.md` — Phase 1 requirements: INGT-01, INGT-02, INGT-03, BKUP-04, WEBUI-01, WEBUI-04, BYOK-02, BYOK-03, BYOK-04, BYOK-05
- `.planning/PROJECT.md` — Constraints: `.env` only for secrets, bind mounts not named volumes, two containers, BYOK by default, no hardcoded env vars

### Research

- `.planning/research/PITFALLS.md` — Critical pitfalls for Phase 1: Docker volume bind mounts (Pitfall 5), API keys in DB (Pitfall 4), deletion cascade schema from day one (Pitfall 1)
- `.planning/research/STACK.md` — Live-verified versions, version-specific gotchas (React 19 not 18, pnpm 10 not 11, pgvector 0.8.2, Vite 8 requires Node ≥20.19.0)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets

- No application code exists yet — this is a greenfield build.

### Established Patterns

- Architecture docs define the module structure precisely. Follow `component-boundaries.md` for every file placement decision.
- `.env` / `.env.sample` pattern is mandated by AGENTS.md global instructions — always maintain both.

### Integration Points

- `backend/app/main.py` → FastAPI app factory, lifespan (DB pool init, worker task start), static file serving for the built frontend
- `backend/app/infrastructure/db.py` → SQLAlchemy async engine, session factory
- `backend/app/api/routes/` → Thin route handlers; call domain services only
- `frontend/src/lib/api.ts` → Typed API client (fetch or axios) used by all pages

</code_context>

<specifics>
## Specific Ideas

- Bind-mount paths must be pre-created by Docker Compose (using the `volumes` section with host paths) — not by the application startup code.
- The entrypoint script must handle `alembic upgrade head` gracefully if PostgreSQL is not yet ready (retry loop with exponential backoff, max 30 seconds).
- `.env.sample` must be committed alongside `.env` (which is gitignored). `.env.sample` contains every variable with placeholder values and inline comments explaining each.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-foundation*
*Context gathered: 2026-03-22*
