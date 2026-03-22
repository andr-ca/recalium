# Tech Stack

## Status
Committed. All agents must use these decisions without deviation. Do not introduce alternative frameworks, languages, or libraries unless a change is explicitly approved and this document is updated first.

## Runtime
- Language: Python 3.12+
- API framework: FastAPI
- ASGI server: Uvicorn

## Worker
- Execution model: in-process background worker co-located in `recalium-app`
- Implementation: asyncio task loop polling the PostgreSQL job queue
- Rationale: avoids a separate container for personal-scale v1; extract to a separate container only if horizontal scaling is needed in a future service profile

## Database
- PostgreSQL 16+ with the `pgvector` extension
- Query layer: SQLAlchemy 2.x (async, using `asyncpg` driver)
- Migrations: Alembic
- Job queue: PostgreSQL-backed (same database, separate schema group)

## UI
- Framework: React 18 + TypeScript
- Build tool: Vite
- Styling: Tailwind CSS
- Component library: shadcn/ui
- Served by: FastAPI static file serving embedded in `recalium-app`

## MCP interface
- Library: official Python MCP SDK (`mcp`)
- Transport: stdio for CLI/agent use; SSE for local HTTP MCP use

## Embeddings
- Local: `sentence-transformers` (all-MiniLM-L6-v2 as default local model)
- External provider: OpenAI embeddings API (`text-embedding-3-small` as default)
- Abstraction: provider-agnostic `EmbeddingAdapter` interface — all callers go through the adapter, never directly to a provider SDK

## Summarization and extraction
- External provider: OpenAI API (default); Anthropic API as alternative
- Local fallback: Ollama (optional, for high-privacy mode; degrades gracefully if unavailable)
- Abstraction: provider-agnostic `CompletionAdapter` interface

## Search
- Keyword: PostgreSQL full-text search (`tsvector` / `tsquery`)
- Semantic: `pgvector` with `ivfflat` index (HNSW index available as upgrade path if query latency requires it)
- Hybrid ranking: Reciprocal Rank Fusion (RRF) — see [retrieval-and-ranking.md](retrieval-and-ranking.md) for the exact algorithm

## Containerization
- Docker Compose for local deployment
- Two containers only: `recalium-app` and `recalium-postgres`
- See [container-topology.md](container-topology.md) for rationale and layout

## Package management
- Python: `uv` (dependency management and virtual environments)
- Node: `pnpm`

## Testing
- Unit and integration: `pytest` + `pytest-asyncio`
- API: `httpx` async test client against the FastAPI app
- UI: Vitest + React Testing Library
- E2E: Playwright

## Environment and secrets
- All environment variables and secrets via `.env` file; never hardcoded
- `.env.sample` must be maintained with all required variable names and safe placeholder values
- Sensitive values (provider API keys, auth secrets) must never appear in any committed file
