# Container Topology

## Default local deployment
v1 uses two containers:

### `recalium-app`
Single application container containing:
- FastAPI application server (Uvicorn)
- In-process background worker (asyncio task loop polling the PostgreSQL job queue)
- React UI served as static files via FastAPI
- Scheduled backup job (asyncio cron task inside the app process, writes to mounted volume)
- Import watcher (optional asyncio background task inside the app process when the watched-folder feature is enabled)

### `recalium-postgres`
PostgreSQL 16+ with `pgvector`:
- Primary data store
- FTS indexes
- Vector indexes
- Job queue tables
- Backup metadata

## Why two containers, not five
The prior architecture described five containers (api, worker, backup, import-watcher, postgres). For a personal-scale local product:

- **Worker** is co-located with the API inside `recalium-app`. An asyncio job loop polling PostgreSQL is sufficient for personal-scale processing. Extract to a separate container only when horizontal worker scaling is needed in a future service profile.
- **Backup** is a scheduled asyncio task inside the app process, not a separate service. It runs `pg_dump` plus artifact directory copy on a cron schedule and writes output to the backup volume.
- **Import watcher** is an optional background asyncio task inside the app process that monitors a mounted folder. It does not require its own container.

The correct time to split a process is when you need to scale it independently. Not before.

## Network model
- All services bind to an internal Docker network
- User-facing endpoints (`recalium-app`) bind to `localhost` by default
- Broader network exposure is opt-in only; authentication and transport protection are mandatory if enabled

## Persistent volumes
- PostgreSQL data: mounted into `recalium-postgres`
- Artifact/blob storage: mounted into `recalium-app`
- Backup output: mounted into `recalium-app`
- Watched import folder: optionally mounted into `recalium-app` when the feature is enabled

## Scaling path for future service profile
If a future hosted service profile requires independent worker scaling:
1. Extract the job loop into a separate `recalium-worker` container
2. Point it at the same PostgreSQL job queue
3. No domain logic changes required — the worker already operates through the queue interface

## Security reference
See [security-and-identity.md](security-and-identity.md) for localhost-only and exposed-mode controls.

## Tech stack reference
See [tech-stack.md](tech-stack.md) for the committed runtime, framework, and library choices used inside these containers.
