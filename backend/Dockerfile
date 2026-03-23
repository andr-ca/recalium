# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base

# Install system dependencies (pg_isready for entrypoint health check)
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv (Python package manager)
RUN pip install uv==0.10.12

WORKDIR /app

# Copy dependency files first (layer cache)
COPY backend/pyproject.toml backend/uv.lock* ./backend/

# Install Python dependencies
RUN cd backend && uv sync --frozen --no-dev

COPY backend/ ./backend/
COPY backend/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Production: pre-built frontend static files
FROM base AS production
COPY frontend/dist/ ./backend/app/static/

FROM base AS development
# No static copy in dev — Vite dev server handles frontend separately

# Default to production target
FROM production
