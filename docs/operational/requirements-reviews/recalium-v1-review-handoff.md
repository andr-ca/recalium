# Requirements Reviewer Handoff

## 1. Handoff status
- Ready for review: Yes
- Open questions remaining: No

## 2. Request classification
- Classification: new product

## 3. Problem statement
Recalium addresses fragmented user context across LLM chats, local notes, code repositories, agent interactions, and tool-specific memory systems by providing a local-first, source-backed memory layer that preserves raw history, derives useful memory representations, and exposes governed retrieval for future AI interactions.

## 4. Intended outcome
Users and MCP-compatible tools should be able to retrieve durable, source-backed context across sessions and applications while the user retains inspection, correction, suppression, promotion, deletion, and audit visibility over stored memory.

## 5. Scope summary
### In scope
- Local Docker-based single-user deployment
- Manual paste import, file upload, direct text submission, MCP ingestion, and watched-folder import
- Raw archive, summaries, structured facts, embeddings, canonical memory, provenance, and audit events
- PostgreSQL + PostgreSQL FTS + `pgvector` baseline
- Search, retrieval, duplicate review queue, canonical curation, local web UI, backups, restore UI, and configurable audit visibility

### Out of scope
- Automated vendor-specific connectors
- Multi-user support
- Advanced per-agent permissions
- Knowledge graph visualization
- Automated memory decay beyond manual status handling
- Enterprise policy engine and complex cloud sync

## 6. Actors and roles
- Primary user — imports, reviews, curates, deletes, promotes, restores, configures
- Local web UI client — primary review surface
- MCP-compatible agent/tool client — ingests and retrieves memory with auditable access
- Processing pipeline components — summarize, extract, embed, classify, index, retry, and reprocess

## 7. Functional requirements summary
- Ingest conversations and artifacts while preserving raw source, timestamps, metadata, and attribution
- Keep raw, derived, embedded, and canonical memory layers distinct
- Support asynchronous derivation after synchronous raw persistence and metadata capture
- Provide keyword, semantic, and hybrid search plus bounded retrieval modes
- Support duplicate/overlap review through a dedicated queue
- Provide canonical memory workflows and provenance-linked review/edit/delete actions
- Expose MCP-compatible ingestion and retrieval capabilities with auditable access events

## 8. Non-functional requirements summary
- Local-first Docker deployment
- External providers allowed but explicit, user-controlled, and optional during onboarding
- Sensitive categories (`personal profile`, `relationships`) blocked from external processing by default
- UI, API, and MCP endpoints bind to localhost by default unless the user explicitly opts into broader exposure
- Ingestion acknowledgement: $P95 \le 1\text{ s}$ for uploads up to 5 MB
- Search/retrieval: $P95 \le 2\text{ s}$ on datasets up to 100k stored items
- Zero loss for acknowledged raw archive items across restart/reboot when persisted volumes remain intact
- Daily backups, 30-day retention, restore within 15 minutes
- Chrome/Chromium latest support, keyboard-only support for core workflows, WCAG 2.1 AA for core workflows
- 90-day access-event retention

## 9. Edge cases and exception handling
- Provider unavailable: local storage, browsing, keyword search, and basic local processing remain usable
- Processing failure: bounded auto-retries before final failure and manual retry
- Duplicate or contradictory facts remain reviewable with provenance
- Sensitive-category external processing blocked unless explicitly overridden
- Restore and audit workflows are first-class user-visible functions

## 10. Dependencies, assumptions, and risks
- Dependencies: PostgreSQL with FTS and `pgvector`, processing pipeline, local web stack, MCP-compatible interface
- Assumptions: single-user local-first product, Docker deployment, watched-folder import, configuration-driven audit detail
- Risks: false memories, sensitive-data over-capture, context overload, stale contradictions, trust erosion, agent over-querying, redundant memory pollution

## 11. Open questions
- None remaining

## 12. Acceptance criteria
- See [docs/requirements/features/platform-v1/acceptance-criteria.md](../../requirements/features/platform-v1/acceptance-criteria.md) for product and cross-cutting `Given / When / Then` criteria

## 13. Files created or updated
- [docs/requirements/README.md](../../requirements/README.md) — requirements index and decision log
- [docs/requirements/product-overview.md](../../requirements/product-overview.md) — product purpose, scope, goals, and baseline decisions
- [docs/requirements/glossary.md](../../requirements/glossary.md) — shared domain vocabulary
- [docs/requirements/nfr.md](../../requirements/nfr.md) — measurable cross-cutting constraints
- [docs/requirements/assumptions-and-risks.md](../../requirements/assumptions-and-risks.md) — assumptions, risks, dependencies, and resolved open-question state
- [docs/requirements/features/platform-v1/overview.md](../../requirements/features/platform-v1/overview.md) — v1 capability baseline
- [docs/requirements/features/platform-v1/workflows.md](../../requirements/features/platform-v1/workflows.md) — primary workflows
- [docs/requirements/features/platform-v1/rules-and-edge-cases.md](../../requirements/features/platform-v1/rules-and-edge-cases.md) — rule and failure handling
- [docs/requirements/features/platform-v1/acceptance-criteria.md](../../requirements/features/platform-v1/acceptance-criteria.md) — implementation-ready acceptance criteria
- [docs/operational/requirements-reviews/recalium-v1-review-handoff.md](../../operational/requirements-reviews/recalium-v1-review-handoff.md) — reviewer handoff package

## 14. Validation result
- 15-point checklist passed: Yes
- Notes: Acceptance criteria are in `Given / When / Then` form, terminology is consistent with the glossary, and no product-scope open questions remain.

## 15. Reviewer ask
Please review these requirements for completeness, logical consistency, ambiguity, missing edge cases, traceability, and implementation readiness.
