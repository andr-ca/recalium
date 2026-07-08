# syntax=docker/dockerfile:1
# ─────────────────────────────────────────────────────────────────────────────
# Recalium backend image
#
# Build args:
#   EMBED_BACKEND  cpu   → install sentence-transformers with CPU-only torch (~1.5 GB)
#                  gpu   → install sentence-transformers with CUDA torch (~4 GB)
#                  none  → skip local ML; use OpenAI / Anthropic / Ollama only
#
# Examples:
#   docker compose build                          # defaults to cpu
#   docker compose build --build-arg EMBED_BACKEND=gpu
#   docker compose build --build-arg EMBED_BACKEND=none
# ─────────────────────────────────────────────────────────────────────────────
FROM python:3.12-slim AS base

ARG EMBED_BACKEND=cpu

# Install system dependencies (pg_isready for entrypoint health check)
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv (Python package manager)
RUN pip install --no-cache-dir uv==0.10.12

WORKDIR /app

# ── Python path & venv ───────────────────────────────────────────────────────
# Store the venv at /app/.venv (NOT inside /app/backend) so that the dev
# volume mount (./backend:/app/backend) does NOT overwrite it with the host venv.
# /app/backend is where app/ lives; add it so `import app.*` works for both
# uvicorn (production & dev --reload) and alembic.
ENV UV_PROJECT_ENVIRONMENT=/app/.venv
ENV PYTHONPATH=/app/backend
ENV PATH="/app/.venv/bin:$PATH"
ENV VIRTUAL_ENV=/app/.venv

# ── Dependency installation ───────────────────────────────────────────────────
# Copy only the dependency manifests first to maximise layer cache hits.
COPY backend/pyproject.toml backend/uv.lock* ./backend/

# Install core deps, skipping optional ML extras (sentence-transformers / torch).
# --no-extra prevents uv from installing local-ml-cpu or local-ml-gpu from the lockfile.
RUN cd backend && uv sync --frozen --no-dev --no-install-project \
    --no-extra local-ml-cpu --no-extra local-ml-gpu

# Install local ML extras based on EMBED_BACKEND build arg.
# CPU: install torch as cpu-only wheel first, then sentence-transformers.
# GPU: install sentence-transformers (torch CUDA wheels from the lockfile).
# none: skip entirely.
RUN if [ "$EMBED_BACKEND" = "cpu" ]; then \
        cd backend && \
        uv pip install \
            --index-url https://download.pytorch.org/whl/cpu \
            "torch>=2.0,<3" && \
        uv pip install "sentence-transformers==5.3.0"; \
    elif [ "$EMBED_BACKEND" = "gpu" ]; then \
        cd backend && uv pip install "sentence-transformers==5.3.0"; \
    fi

# Copy application source
COPY backend/ ./backend/
COPY backend/entrypoint.sh /app/entrypoint.sh
COPY backend/dev-entrypoint.sh /app/dev-entrypoint.sh
RUN chmod +x /app/entrypoint.sh /app/dev-entrypoint.sh

# ── Production stage ──────────────────────────────────────────────────────────
FROM base AS production
# Pre-built React SPA served as static files
COPY frontend/dist/ ./backend/app/static/

# ── Development stage ─────────────────────────────────────────────────────────
FROM base AS development
# Copy built React SPA as static files (dev uses compiled dist, not Vite dev server)
COPY frontend/dist/ ./backend/app/static/

# Default to production target
FROM production
