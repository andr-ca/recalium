# Performance and Operability

## Target traceability
### Ingest target
- acknowledgement: $P95 \le 1\text{ s}$ for paste import and file upload up to 5 MB under normal local conditions

### Retrieval/search target
- $P95 \le 2\text{ s}$ on datasets up to 100k stored items

### Restore target
- restore any successful backup within 15 minutes for the standard local deployment baseline and representative backed-up dataset profile

## Capacity assumptions
- single-user workstation deployment
- no concurrent multi-user traffic
- 100k stored items across raw, summary, fact, and searchable chunk records participating in active search/retrieval

## Design tactics
### Ingest path
- keep synchronous path minimal
- persist raw archive and lightweight metadata only
- enqueue all heavy work asynchronously
- use idempotency keys to avoid duplicate heavy processing after retries
- use transactional raw-write plus job-insert semantics so acknowledgement implies durable downstream work scheduling

### Job durability and backpressure
- jobs must be durably recorded before acknowledgment-dependent asynchronous processing begins
- worker concurrency must be bounded
- queue backlog must be observable
- terminal failure and retry counts must be explicit

See [queue-and-jobs.md](queue-and-jobs.md) for the selected PostgreSQL-backed durable queue model.

### Search/retrieval performance
- maintain FTS indexes for keyword paths
- maintain vector indexes for semantic paths
- use metadata filters to reduce candidate sets early
- apply retrieval precedence and budget trimming after candidate generation
- keep canonical-memory lookups cheap and deterministic

### Reprocessing performance
- support batched reprocessing
- isolate reprocessing from foreground request performance
- provide operational visibility into backlog size and job age

## Benchmark approach
Minimum architecture expectation:
- benchmark ingest acknowledgment under the published local profile
- benchmark keyword search and hybrid retrieval on the 100k-item dataset profile
- test degraded mode separately from provider-enabled mode
- measure queue backlog impact on foreground APIs
- validate restore duration against a representative backup containing the required dataset artifact set, associated blob storage, and restored dataset configuration within the standard local deployment baseline

## Operational signals
- ingest latency
- search latency
- retrieval latency
- restore duration
- queue depth
- retry counts
- terminal job failures
- backup success/failure

## Architecture implication
Performance targets are achieved primarily through:
- minimal synchronous ingest
- durable asynchronous job handling
- explicit indexing strategy
- bounded worker concurrency
- retrieval candidate narrowing before response assembly
