# Recalium Project Context

Recalium is a local-first, MCP-enabled personal memory platform that captures user interactions across LLMs, agents, and tools, transforming them into durable, searchable context for future interactions.

## Project Overview

- **Purpose:** Provide a portable memory layer that persists across models, sessions, and applications while remaining inspectable and user-controlled.
- **Architecture:** Modular monolith deployed as two Docker containers (`recalium-app`, `recalium-postgres`). Worker, backup scheduler, and import-watcher run as in-process tasks inside `recalium-app`.
- **Core Stack:**
  - **Backend:** Python 3.12 + FastAPI + SQLAlchemy.
  - **Database:** PostgreSQL with `pgvector` (semantic search) and Full-Text Search (keyword search).
  - **Frontend:** Localhost Web UI (accessible, keyboard-operable, left-nav layout).
  - **Integration:** MCP (Model Context Protocol) for agent/tool compatibility.
- **Current Phase:** Implementation starting (WS1: Durable ingest spine).

## Key Folders

- `src/`: Application source code (implementation starting).
- `docs/`: Comprehensive documentation (architecture, requirements, plans, operational).
- `agents/`: Agent instructions, prompts, and operational artifacts.
- `.github/agents/`: Canonical agent definitions for project-level sync.

## Key Files

- `README.md`: High-level project overview.
- `agents/core.instructions.md`: **Crucial** mandatory workflows (Branch safety, TDD, Documentation).
- `agents/python.instructions.md`: Detailed Python 3.12 modular development and DI guidelines.
- `agents/tdd.instructions.md`: Mandatory Red-Green-Refactor workflow.
- `agents/sync-agents.py`: Script to sync agent instructions between user profile and project.
- `docs/plans/implementation-plan.md`: Roadmap and batch-level delivery details.

## Building and Running

*Note: Initial implementation batch is underway. Commands below are based on planned stack.*

- **Environment Setup:** Copy `.env.sample` to `.env` and configure.
- **Agent Sync:** `python agents/sync-agents.py [push|pull]`
- **Testing (TODO):** `pytest` (Mandatory TDD workflow).
- **Linting (TODO):** `ruff check .`
- **Docker (TODO):** `docker-compose up`

## Development Conventions

### 🔴 Branch Safety (Mandatory First Step)
Before any change, run `git status -sb` and confirm the branch strategy with the user. Never commit directly to trunk branches (`main`, `master`, `develop`, etc.).

### 🚨 TDD is Mandatory (Non-Negotiable)
Follow the **Red-Green-Refactor** cycle for every change:
1. **RED:** Write a failing test first.
2. **GREEN:** Write minimal code to pass.
3. **REFACTOR:** Improve code while keeping tests green.

### 📊 Test Coverage
- **Business Logic:** 100% (services, validators, utils, rules).
- **Overall Project:** 80% minimum.

### 🏗️ Modular Python Design
- Depend on abstractions (Interfaces/Protocols), not concrete implementations.
- Use Constructor Injection for dependencies.
- Follow SOLID principles (SRP, DIP, ISP specifically highlighted in project docs).

### 📚 Documentation
- All code changes must be accompanied by updates to relevant files in `docs/`.
- Update `CHANGES.md` (or equivalent as established) for every feature/fix.
