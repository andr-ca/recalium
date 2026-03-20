# Architect Response to Review Feedback

## Status
- Feedback reviewed by architect: Yes
- Blocking findings accepted: Yes
- Architecture revision required: Yes

## Review inputs
- [recalium-v1-architecture-review.md](recalium-v1-architecture-review.md)
- [recalium-v1-return-to-architect.md](recalium-v1-return-to-architect.md)
- [../../architecture/architect-handoff.md](../../architecture/architect-handoff.md)

## Architect assessment
The reviewer feedback is valid. The current architecture package is directionally sound but under-specified in the exact areas that determine implementation safety: module boundaries, security/identity, portability/export design, and performance traceability.

The architecture should be revised before resubmission.

## Response to blocking issues

### 1. Component and runtime boundaries are too abstract
Accepted.

Planned response:
- define concrete module ownership for ingest, archive, derived memory, canonical memory, policy, retrieval, audit, operations, and export/restore
- define internal contracts and dependency direction rules
- add at least two end-to-end sequence flows:
  - ingest to processing to review
  - retrieval with policy, ranking, audit, and trimming
- clarify runtime responsibilities across `api`, `worker`, `postgres`, `backup`, and `import-watcher`

Target docs to update:
- [../../architecture/system-context.md](../../architecture/system-context.md)
- [../../architecture/container-topology.md](../../architecture/container-topology.md)
- [../../architecture/processing-pipeline.md](../../architecture/processing-pipeline.md)
- new component-boundaries appendix expected

### 2. Security architecture for non-localhost exposure and MCP identity is missing
Accepted.

Planned response:
- define localhost-only mode versus exposed mode
- define authentication expectations for UI/API/MCP when exposure is broadened
- define session handling model for UI access
- define client identity propagation into audit events for MCP/API calls
- define transport protection assumptions for exposed mode

Target docs to update:
- [../../architecture/container-topology.md](../../architecture/container-topology.md)
- [../../architecture/api-and-mcp.md](../../architecture/api-and-mcp.md)
- [../../architecture/audit-and-provenance.md](../../architecture/audit-and-provenance.md)
- new security appendix expected

### 3. Portability/export architecture is not covered
Accepted.

Planned response:
- define export/import flows for JSON bundle and Markdown-plus-assets zip
- define archive versioning and compatibility markers
- define ownership boundaries between operational backups and portable exports
- define restore interaction versus import interaction

Target docs to update:
- [../../architecture/backup-and-restore.md](../../architecture/backup-and-restore.md)
- [../../architecture/api-and-mcp.md](../../architecture/api-and-mcp.md)
- [../../architecture/privacy-and-policy.md](../../architecture/privacy-and-policy.md)
- new portability appendix expected

### 4. Performance architecture does not trace to the stated targets
Accepted.

Planned response:
- define queue durability and job backpressure model
- define indexing/query tactics supporting FTS, vector retrieval, and hybrid search
- define workload assumptions for the 100k-item dataset baseline
- define a benchmark and validation approach tied to the published $P95$ targets

Target docs to update:
- [../../architecture/storage-and-indexing.md](../../architecture/storage-and-indexing.md)
- [../../architecture/processing-pipeline.md](../../architecture/processing-pipeline.md)
- [../../architecture/retrieval-and-ranking.md](../../architecture/retrieval-and-ranking.md)
- new performance appendix expected

## Response to minor issues
- `import-watcher` should be added to the default topology or explicitly described as an optional profile component.
- backup/restore needs explicit consistency and restore cutover behavior.
- UI architecture should mention keyboard-critical and restore workflows at an architectural level.

## Revision plan
1. Add component boundaries and sequence flows.
2. Add security and identity appendix.
3. Add portability/export appendix.
4. Add performance/operability appendix.
5. Resolve minor topology, restore, and UI-architecture gaps.
6. Resubmit architecture package for review.

## Resubmission condition
The architecture package should be resubmitted only after all four blocking areas are covered explicitly in architecture docs, not just implied across multiple files.
