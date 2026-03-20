# Artifact Storage

## v1 architecture decision
Use a dual-layer artifact model:
- authoritative artifact metadata in PostgreSQL
- authoritative raw artifact/blob bytes in an application-managed local storage volume through a storage adapter

## Rationale
- keeps PostgreSQL focused on relational metadata and indexes
- handles large or binary artifacts without overloading relational storage patterns
- maps cleanly to future object storage in a sellable service profile

## Authoritative metadata
PostgreSQL stores:
- artifact ID
- source linkage
- content type
- storage path or storage key
- size
- checksum/hash
- ingestion timestamp
- deletion/redaction state
- export eligibility flags where applicable

## Authoritative blob storage
Application-managed storage volume stores:
- uploaded files
- imported binary assets
- archive export assets
- any raw artifact bytes not represented as inline text

## Consistency rules
- metadata write and blob persistence must be coordinated so orphaned metadata or orphaned blobs can be detected and repaired
- checksum/hash must be recorded for integrity verification
- backup and restore must include both metadata and blob storage
- export packaging must resolve assets through the same storage adapter

## Reconciliation ownership
The `artifact-storage` module owns artifact consistency checks, while `operations` owns scheduling and operator visibility for reconciliation runs.

Minimum reconciliation triggers:
- startup or health verification
- pre-backup validation
- post-restore validation
- on-demand operator-triggered repair check

Minimum reconciliation outcomes:
- orphaned metadata detected
- orphaned blobs detected
- checksum mismatch detected
- repairable vs non-repairable status reported to the operator

## Restore and deletion implications
- tombstones govern whether restored artifact metadata or blobs are active
- future backups/exports exclude tombstoned data
- old backups may still contain removed blobs and must be flagged accordingly

## Future-service compatibility
The storage layer should be abstracted behind a storage adapter so a future hosted/service deployment can swap the local volume for object storage without changing domain semantics.
