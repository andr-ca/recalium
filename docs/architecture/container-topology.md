# Container Topology

## Default local deployment
Recommended v1 Docker profile:
1. `recalium-api` — primary application container
2. `recalium-worker` — background job processor
3. `recalium-postgres` — PostgreSQL with FTS and `pgvector`
4. `recalium-backup` — scheduled backup and restore helper
5. `recalium-import-watcher` — watched-folder ingestion helper when the watched-folder feature is enabled

The web UI may be:
- embedded into `recalium-api`, or
- served as a thin separate frontend container if that improves build and release ergonomics

## Network model
- All services bind to an internal Docker network
- User-facing endpoints bind to `localhost` by default
- Broader exposure is opt-in only
- If broader exposure is enabled, authentication, session handling, and transport protection are mandatory

## Persistence
Persisted Docker volumes should exist for:
- PostgreSQL data
- artifact/blob storage
- backup artifacts
- watched import folder, when managed by the deployment
- optional application-managed assets or export staging

## Operational notes
- acknowledged raw archive durability depends on persisted volumes remaining intact
- worker failure must not threaten persisted raw archive data
- backup scheduling must be isolated from request-response paths
- `import-watcher` should reuse the same normalized ingest contract used by UI/API/MCP ingestion rather than writing directly to storage

## Security reference
See [security-and-identity.md](security-and-identity.md) for localhost-only and exposed-mode controls.
