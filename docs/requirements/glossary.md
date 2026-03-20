# Glossary

## Recalium
The product being defined: a local-first, MCP-enabled personal memory platform.

## Local-first
The default operating model in which user data is stored locally under the user's control, with no hidden third-party sharing.

## MCP
Model Context Protocol or equivalent MCP-compatible interface used by agents and tools to consume memory services.

## Raw archive
Original ingested content stored as captured, immutable by default except through deletion or redaction workflows.

## Summary
A derived representation of a raw conversation, session, or document, linked to source content and versioned when regenerated.

## Structured fact
A normalized extracted memory item such as a preference, project detail, decision, milestone, or relationship.

## Canonical memory
User-approved durable memory that has higher retrieval priority than system-extracted memory and requires explicit user action to create or promote.

## Extracted memory
System-derived memory created by the processing pipeline from ingested content. It remains distinct from canonical memory.

## Embedding / semantic index
Vectorized representation of source items or chunks used for semantic retrieval.

## Provenance
Source and process history for a stored memory item, including origin, timestamps, and derivation path.

## Retrieval
The process of returning the smallest useful source-backed context set for a given query, task, project, profile request, or time-bounded request.

## Context budget
A configurable limit on how much memory is returned for a retrieval operation. v1 supports minimal, normal, and expanded modes.

## Duplicate / overlap review
A workflow for reviewing likely duplicate, near-duplicate, or semantically overlapping extracted facts so that redundant memory does not proliferate.

## Lifecycle status
The state of a memory item. Minimum v1 statuses are active, disputed, stale, archived, and deleted.

## Access event
An auditable machine-client or agent interaction with memory, such as search, retrieve, read, update, or delete.
