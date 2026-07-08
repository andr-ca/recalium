# QA Automation

## Purpose
This area defines how Recalium v1 automates quality checks during implementation and release validation.

## Documents
- [qa-automation-stack.md](qa-automation-stack.md) — selected QA automation tools, gates, and execution model
- [../validations/recalium-v1-release-readiness-gap-register.md](../validations/recalium-v1-release-readiness-gap-register.md) — active release-readiness gap register and evidence requirements
- [../../guides/local-use-and-test.md](../../guides/local-use-and-test.md) — local startup, usage, MCP, and testing walkthrough

## Evidence location
- [artifacts/](artifacts/) — generated QA artifacts such as benchmark outputs, accessibility reports, restore validation evidence, and test run summaries

## Current test entry points

### Backend

Run from [../../../backend](../../../backend) with the backend Python environment active:

- `pytest` — full backend suite.
- `pytest tests/mcp` — MCP unit/schema coverage.
- `pytest tests/e2e` — live-stack E2E tests after Docker Compose is running.

### Frontend

Run from [../../../frontend](../../../frontend):

- `pnpm build` — TypeScript and production build validation.
- `pnpm test` — Vitest tests.
- Playwright E2E — required for release readiness after config is added.

### Manual release evidence

For any manual validation, create a report under this folder and store screenshots, logs, traces, or benchmark output under [artifacts/](artifacts/).

Release-ready validation must cover:

- MCP ingest/retrieve through a real client.
- UI keyboard-only workflows.
- Backup trigger and restore validation.
- Degraded no-provider mode.
- Ingest and retrieval latency targets.
- Secret-safety checks for database, logs, backups, exports, and docs.
