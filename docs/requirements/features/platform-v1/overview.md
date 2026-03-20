# Platform v1 Overview

## Objective
Deliver a first useful version of Recalium that lets a single local user ingest conversations and related artifacts, preserve raw sources, derive searchable and reviewable memory layers, retrieve compact source-backed context, and curate trusted canonical memory through a local web UI and MCP-compatible interfaces.

## Deployment model
v1 is deployed as a local Docker-based service. The primary review client is a localhost web UI running against the local Recalium backend and supporting services under the user's control.

## Processing provider model
v1 may call external providers for summarization, extraction, and embeddings. This does not change the local-first storage model, but it means the first release is not constrained to fully local AI processing.

## Storage and retrieval implementation baseline
v1 should use PostgreSQL as the primary local data store, PostgreSQL full-text search for keyword search, and `pgvector` for semantic search. Hybrid search and retrieval ranking should be composed in the application layer.

## Actors
- Primary user
- Local web UI client
- MCP-compatible agent or tool client
- Processing pipeline components

## Capability areas
1. Ingestion
2. Processing pipeline
3. Layered memory storage
4. Search and retrieval
5. Review and curation UI
6. Machine-consumable APIs and MCP integration
7. Provenance and access auditability

## Ingestion baseline
v1 must support:
- manual paste import
- JSON or Markdown file upload
- direct text submission into Recalium
- MCP-accessible ingestion
- a watched import folder as the first low-friction local workflow

Each ingested item must preserve source system, conversation or session identifier when available, timestamp, raw content, import method, and attribution metadata.

For MCP-compatible ingestion, requests must include raw content, source metadata, client identity, import method, idempotency key where available, sensitivity hints, project hint, and requested processing mode.

## Memory layers
- Raw archive
- Summaries
- Structured facts
- Embeddings / semantic index
- Curated canonical memory

These layers must remain distinguishable at all times.

## Retrieval baseline
The system must support free-text, prompt-context, task-description, project, profile, and time-bounded retrieval inputs. It must return concise contextual summaries, ranked source-backed facts, relevant excerpts, and filtered bundles while respecting configurable context budgets.

For MCP-compatible retrieval, v1 responses must include returned items, source links, item type, rank score, provenance metadata, conflict labels where applicable, budget or trimming reason, and retrieval-mode metadata.

## UI baseline
The local web UI is a core product surface and must support ingestion review, raw archive browsing, summaries, extracted facts, duplicate or overlap review, canonical memory management, search and retrieval testing, disputed or stale review, and access-audit visibility.

For duplicate and overlap cleanup, v1 should provide a dedicated review queue that groups similar facts and supports comparison actions.

The first navigation model should be a left-nav application with top-level sections for Ingest, Archive, Facts, Canonical, Search, Review Queue, Audit, and Settings.

Audit visibility should be configuration-driven. The standard v1 configuration should show a basic event list plus per-event detail drawer, while configuration may enable fuller audit detail and broader event payload visibility.

Human-readable exports should use a hybrid zip structure with a top-level index, type-based folders, and manifest metadata preserving provenance and source/session links.

## Deferred scope
- fully automated connectors
- advanced permissions and per-agent scoping
- knowledge graph visualization
- advanced autonomous conflict resolution
- automatic decay or confidence-based freshness logic
- multi-user support
- enterprise policy management
