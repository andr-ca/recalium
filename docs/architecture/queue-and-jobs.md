# Queue and Jobs

## v1 architecture decision
Use a PostgreSQL-backed durable job queue for v1.

## Rationale
- preserves a simple local Docker deployment
- shares durability guarantees with the primary data store
- avoids introducing a separate queue service in v1
- keeps a clean path to a future queue adapter if a hosted/service profile needs it later

## Core model
Jobs are stored in PostgreSQL with fields such as:
- job ID
- job type
- payload reference or payload body
- status
- created timestamp
- available-at timestamp
- attempt count
- max attempts
- last error summary
- correlation IDs for source item or ingest request

## Transaction boundary
For ingest:
1. raw archive record is written
2. lightweight metadata is written
3. required job records are inserted
4. transaction commits

Acknowledged ingest must happen only after raw archive persistence and required downstream job inserts commit successfully.

## Worker pickup model
- workers poll eligible jobs
- job claiming uses row-level locking semantics appropriate for PostgreSQL
- only one worker may claim a job at a time
- claimed jobs move through explicit status transitions

## Retry model
- bounded automatic retries
- exponential or stepped retry backoff
- terminal failure state after max attempts
- dead-letter or terminal-failure view for operator review

## Recovery model
- pending/available jobs survive restart because queue state is durable in PostgreSQL
- in-progress jobs older than a recovery threshold may be re-queued on worker restart logic
- duplicate side effects are minimized by idempotent job handlers where required

## Observability
At minimum track:
- queue depth by job type
- oldest pending job age
- retry counts
- terminal failures
- worker claim latency

## Future-service compatibility
The queue interface should be adapter-based so a future service profile can swap PostgreSQL-backed jobs for another queue implementation without changing domain behavior.
