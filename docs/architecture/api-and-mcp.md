# API and MCP

## Local surface areas
- ingestion API
- search API
- retrieval API
- fetch-by-id API
- canonical-memory create/update API
- delete/suppress API
- MCP-compatible tools exposing equivalent capabilities

## MCP ingestion minimum contract
Requests include:
- raw content
- source metadata
- client identity
- import method
- idempotency key where available
- sensitivity hints
- project hint
- requested processing mode

## MCP retrieve minimum contract
Responses include:
- returned items
- source links
- item type
- rank score
- provenance metadata
- conflict labels where applicable
- budget or trimming reason
- retrieval-mode metadata

## Interface posture
- local-first and localhost-first by default
- broader exposure is optional and requires security controls
- API and MCP contracts should remain stable enough to survive a future move to a sellable service profile

## Contract stability rules
- version API and MCP contracts explicitly
- define a stable error taxonomy for validation, policy denial, unavailable capability, and internal failure cases
- support pagination or bounded result envelopes for list/search surfaces where payload growth is possible
- keep request/response semantics backward-compatible within a v1 contract line

## Identity and security reference
See [security-and-identity.md](security-and-identity.md) for authentication, session, transport, and MCP/client identity propagation expectations.

## Portability reference
Export/import contracts and versioning expectations are covered in [portability-and-export.md](portability-and-export.md).
