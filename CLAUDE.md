<!-- GSD:project-start source:PROJECT.md -->
## Project

**Recalium**

Recalium is a local-first, MCP-native personal memory platform that captures conversations from any AI tool, transforms them into durable searchable memory, and makes that memory retrievable by any MCP-compatible client. It runs as two Docker containers (`recalium-app` + `recalium-postgres`) on the user's machine. It is designed as infrastructure, not a feature — the app is the reference implementation of an open memory portability format.

**Core Value:** A user's future AI session — on any tool, with any model — can retrieve relevant, source-backed context from prior conversations that happened anywhere, without re-explaining anything.

### Constraints

- **Tech Stack**: Python/FastAPI + React/TypeScript + PostgreSQL/pgvector — committed, no deviation without explicit approval and doc update
- **Deployment**: Two containers only (`recalium-app` + `recalium-postgres`) for v1; no separate worker/backup/watcher containers
- **Single-user**: v1 is single-user local-first; no multi-tenant columns, auth systems, or policy engines
- **BYOK by default**: No Recalium-operated processing services in v1; user's own provider keys only
- **Service-ready boundaries**: Clean module separation (domain logic / deployment profile / policy hooks) to allow future hosted service without full rewrite
- **Package managers**: `uv` for Python, `pnpm` for Node
- **Secrets**: All via `.env` file; `.env.sample` must be maintained; never hardcoded
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

## Recommended Stack
### Core Technologies — Backend
| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | `3.12+` | Runtime | Required by sentence-transformers 5.x; 3.13 free-threaded GIL is experimental — stay on 3.12 for now |
| FastAPI | `0.135.1` | ASGI web framework + static file serving | Native async, Pydantic v2 native, automatic OpenAPI, excellent for both REST API and serving bundled UI |
| Uvicorn | `0.42.0` | ASGI server | Standard pairing with FastAPI; use `uvicorn[standard]` for WebSocket + HTTP/2 support |
| PostgreSQL | `16+` | Primary data store + FTS + job queue | Built-in `tsvector`/`tsquery` for FTS, pgvector extension for semantic search, LISTEN/NOTIFY for job queue — eliminates Redis/RabbitMQ for personal scale |
| pgvector | `0.8.2` | Vector similarity search extension | Native Postgres extension; IVFFlat index for baseline, HNSW available as latency upgrade path. v0.8.2 (2026-02-25) fixes buffer overflow in parallel HNSW builds — upgrade before enabling parallel HNSW |
| SQLAlchemy | `2.0.48` | Async ORM + query layer | 2.x async-native with asyncpg driver; `mapped_column` declarative style; type-safe query construction |
| asyncpg | `0.31.0` | Async PostgreSQL driver | Required by SQLAlchemy async; fastest Python Postgres driver; native asyncio |
| Alembic | `1.18.4` | Database migrations | Standard SQLAlchemy migration tool; supports async engines via `run_sync` |
| Pydantic | `2.12.5` | Data validation + settings | v2 is 5-50x faster than v1; FastAPI 0.100+ requires Pydantic v2; use `pydantic-settings` for `.env` loading |
| mcp (Python SDK) | `1.26.0` | MCP server/client implementation | Official SDK; stdio transport for CLI/agent use, SSE for local HTTP MCP |
### Core Technologies — Frontend
| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| React | `19.2.4` | UI framework | React 19 is current stable (dropped Dec 2024, 19.2 Oct 2025); shadcn/ui has full React 19 support; new projects should use 19 not 18 |
| TypeScript | `5.x` | Type safety | Required by shadcn/ui and React ecosystem; strict mode recommended |
| Vite | `8.0.1` | Frontend build tool | Fastest dev-server HMR; Vite 8 requires Node.js `^20.19.0 \|\| >=22.12.0` — verify Node version before setup |
| Tailwind CSS | `4.x` | Utility-first styling | v4 is current; CSS-first config (no `tailwind.config.js`); shadcn/ui 2.x is built for Tailwind v4 |
| shadcn/ui | `2.x` | Accessible component library | Not a package — copied components with full ownership; React 19 + Tailwind v4 support confirmed |
### Supporting Libraries — Backend
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `sentence-transformers` | `5.3.0` | Local embedding generation | Default path — no API key required; uses all-MiniLM-L6-v2 model |
| `openai` | `1.x` | OpenAI embeddings + completions | BYOK external provider path for embeddings (`text-embedding-3-small`) and summarization/extraction |
| `anthropic` | `0.x` | Anthropic completions | BYOK alternative provider for summarization/extraction |
| `httpx` | `0.28.1` | Async HTTP client | Used as FastAPI test client (`httpx.AsyncClient`) and for external API calls; replaces `requests` for async contexts |
| `pydantic-settings` | `2.x` | `.env` file loading + settings management | Load all config from `.env`; required for BYOK key management |
| `pytest` | `8.x` | Test runner | Standard Python test framework |
| `pytest-asyncio` | `1.3.0` | Async test support | Required for testing FastAPI async endpoints; v1.x is a major version jump from 0.x — review release notes before upgrading from 0.x projects |
### Supporting Libraries — Frontend
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Vitest | `3.x` | Unit/component testing | Native Vite integration; replaces Jest for Vite projects |
| React Testing Library | `16.x` | Component testing utilities | Behavior-focused testing; pairs with Vitest |
| Playwright | `1.x` | E2E testing | Browser automation for full workflow tests |
### Development & Infrastructure Tools
| Tool | Version | Purpose | Notes |
|------|---------|---------|-------|
| uv | `0.10.12` | Python package manager + venv | Very actively developed (weekly releases); production-ready; replaces pip + virtualenv + pip-tools |
| pnpm | `10.32.1` | Node package manager | Use v10 stable — v11 is beta with breaking changes (pure ESM, store format changes, config migration) |
| Docker Compose | `2.x` | Local container orchestration | Two containers: `recalium-app` + `recalium-postgres` |
| Node.js | `>=20.19.0` | Required by Vite 8 | Vite 8 requires `^20.19.0 \|\| >=22.12.0`; verify before dev environment setup |
## Installation
# Python backend (via uv)
# Python dev dependencies
# Frontend (via pnpm, requires Node >=20.19.0)
# shadcn/ui: use CLI (copies components, not a package)
## Alternatives Considered
| Recommended | Alternative | Why Not / When Alternative is Better |
|-------------|-------------|---------------------------------------|
| FastAPI | Django REST Framework | DRF is better for admin-heavy apps or teams already on Django; FastAPI wins on async-native design and Pydantic integration |
| FastAPI | Flask | Flask lacks native async; FastAPI's automatic OpenAPI docs are valuable for MCP tool documentation |
| PostgreSQL as job queue | Redis + Celery / RabbitMQ | Adds two more containers; personal-scale v1 doesn't need distributed workers; use Redis when horizontal worker scaling is needed |
| asyncpg | psycopg3 | asyncpg is faster for pure async workloads; psycopg3 is better if you need sync+async dual support |
| sentence-transformers | OpenAI embeddings only | sentence-transformers runs fully local with no API key — essential for the "usable without keys" requirement |
| pnpm | npm / yarn | pnpm has faster installs and strict hoisting; avoids phantom dependency issues in monorepo-style setups |
| uv | Poetry / pip-tools | uv is 10-100x faster; actively replacing pip in the ecosystem; Poetry has slower resolver and more complex lockfile format |
| Vitest | Jest | Vitest is native to Vite; no config bridging needed; faster test runs via Vite's transform pipeline |
| pgvector IVFFlat | Dedicated vector DB (Weaviate, Qdrant) | Adds a third container; for ≤100k items, pgvector in Postgres is sufficient; use dedicated vector DB only if query latency becomes a hard blocker |
## What NOT to Use
| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `mcp>=2` | MCP Python SDK v2 development is underway on `main` branch (breaking transport layer changes planned Q1 2026); v1.x is maintenance-only. Pin strictly to `mcp>=1.26,<2` | `mcp==1.26.0` (or `>=1.26,<2`) |
| pnpm v11 | Currently beta.2; breaking changes: pure ESM only, Node 18-21 dropped, store format changes, config moves from `.npmrc` to `pnpm-workspace.yaml` | `pnpm@10.32.1` |
| React 18 for new code | React 19 is current stable; shadcn/ui 2.x targets React 19; starting on 18 means a migration sooner | React `19.2.4` |
| `requests` library | Synchronous; blocks the asyncio event loop in async contexts | `httpx` (async) |
| `SQLite` | No pgvector support; no concurrent async writes; would require separate vector DB | `PostgreSQL 16+` with pgvector |
| `asyncio.run()` inside FastAPI routes | Blocks the event loop; crashes in nested async contexts | `await` natively; use `BackgroundTasks` or `asyncio.create_task()` for fire-and-forget |
| Hardcoded API keys | Security risk; violates BYOK model | `.env` file + `pydantic-settings`; never in committed code |
## Version Compatibility
| Package | Compatible With | Notes |
|---------|-----------------|-------|
| `mcp>=1.26,<2` | FastAPI 0.135.x, Python 3.12 | Pin upper bound — v2 has breaking transport changes |
| FastAPI `0.135.1` | Pydantic v2 (`>=2.12`), Python `3.8+` | Multiple breaking changes in 0.129–0.132 range (Feb 2026); read release notes before upgrading |
| Vite `8.0.1` | Node.js `^20.19.0 \|\| >=22.12.0` | Vite 8 dropped Node 18/20.0-20.18; verify Node version before CI/dev setup |
| `pytest-asyncio` `1.3.0` | pytest `8.x` | v1.x is a major version jump from 0.x; asyncio mode configuration syntax changed |
| `pgvector` `0.8.2` | PostgreSQL `14–17`, PostgreSQL `18 RC1` | v0.8.2 fixes buffer overflow in parallel HNSW builds — do not use older versions with parallel HNSW |
| shadcn/ui `2.x` | React `19.x`, Tailwind `4.x` | shadcn/ui 2.x is not backward-compatible with Tailwind v3 config format |
| `sentence-transformers` `5.3.0` | Python `3.9+`, PyTorch `2.x` | 5.x is a major version jump; requires PyTorch 2.x; model API surface changed from 4.x |
| Tailwind CSS `4.x` | Vite `5+`, PostCSS | v4 uses CSS-first config; `tailwind.config.js` is not used — configure via `@import "tailwindcss"` in CSS |
## Stack Patterns by Variant
- Use `sentence-transformers` (all-MiniLM-L6-v2) for embeddings
- Skip summarization/extraction jobs (queue them as deferred)
- Serve keyword search + cached semantic results (degraded mode per requirements)
- Use `text-embedding-3-small` via `openai` SDK through `EmbeddingAdapter`
- Use GPT-4o-mini (or configured model) via `CompletionAdapter` for summarization/extraction
- Route completions through `CompletionAdapter` → `AnthropicProvider`
- Embeddings still require OpenAI or sentence-transformers (Anthropic has no embeddings API as of 2026-03)
- Route completions through `CompletionAdapter` → `OllamaProvider`
- Use sentence-transformers for embeddings (keep everything local)
- Degrade gracefully if Ollama is unavailable
- Switch IVFFlat → HNSW index (pgvector 0.8.x supports this in-place)
- Tune `lists` parameter for IVFFlat or `m`/`ef_construction` for HNSW
- Do NOT add a separate vector database container for v1
## Sources
- PyPI live fetch (2026-03-22): FastAPI, Uvicorn, SQLAlchemy, asyncpg, Alembic, Pydantic, httpx, mcp, sentence-transformers, pytest-asyncio — HIGH confidence
- npm/GitHub live fetch (2026-03-22): React, Vite, pnpm, Tailwind CSS, shadcn/ui — HIGH confidence
- MCP Python SDK GitHub releases (2026-03-22): confirmed v1.26.0 stable, v2 development on `main` — HIGH confidence
- pgvector GitHub changelog (2026-03-22): confirmed v0.8.2, HNSW parallel build fix — HIGH confidence
- uv GitHub releases (2026-03-22): confirmed v0.10.12, weekly release cadence — HIGH confidence
- pnpm GitHub releases (2026-03-22): confirmed v10.32.1 stable, v11.0.0-beta.2 breaking changes — HIGH confidence
- `/home/andrey/projects/recalium/docs/architecture/tech-stack.md` — committed stack decisions (source of truth)
- `/home/andrey/projects/recalium/.planning/PROJECT.md` — constraints and key decisions
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
