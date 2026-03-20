# Backup and Restore

## Backup baseline
- daily scheduled backups
- 30-day retention
- local backup storage under user control

## Backup consistency decision
v1 backups should use a PostgreSQL-consistent backup mechanism coordinated with an artifact-storage snapshot or staged artifact copy under a single backup manifest.

The backup manifest should record:
- backup ID
- creation time
- database backup reference
- artifact snapshot/copy reference
- schema/version markers
- deletion/tombstone state assumptions

## Restore baseline
- restore any successful backup within 15 minutes
- restore must recover raw archive items, summaries, structured facts, canonical memory, provenance metadata, retained audit events, and required configuration for the dataset

Restored configuration should include dataset-operational configuration required to use the restored data model and workflows, but should exclude secrets and provider credentials that are intentionally operator-managed outside the dataset backup.

## Restore cutover decision
Restore should run in a staged restore area first:
1. restore database state
2. restore artifact/blob state
3. restore dataset configuration that is included in backup scope
4. validate integrity, tombstone/deletion suppression state, and dataset-operational readiness
5. present validation outcome to the operator, including any excluded secrets/provider credentials that must be re-supplied
6. activate the restored dataset through controlled cutover only after validation succeeds

Partially restored state must never become the active dataset.

## Data-removal behavior
- future backups exclude deleted/redacted content
- existing backups are not rewritten in v1
- existing backups must be flagged if they may contain removed content
- restored datasets must reapply deletion/redaction tombstones before activation so removed data does not resurface

## Architecture implications
- backup generation should run outside request-response critical paths
- restore should support integrity validation before activation
- backup metadata should include versioning and compatibility markers for future import/restore evolution
- restore should use a controlled cutover so partially restored data is not exposed as active state
- backup creation should have a consistency method appropriate to PostgreSQL-backed recovery rather than relying on ad hoc file copies

## UI and operator flows
- restore should have an operator-visible flow in the web UI with keyboard-operable initiation, status visibility, validation results, and cutover confirmation
- backup inventory and deleted-data warnings should be visible through an operations-oriented review surface

## Restore validation profile
The 15-minute restore target should be validated against the same local deployment baseline used by published v1 performance targets, with a representative backup containing the required dataset artifact set and associated blob storage for that profile.

## Portability reference
Operational backup is distinct from portability export. See [portability-and-export.md](portability-and-export.md).

Deletion/redaction continuity is defined in [deletion-and-tombstones.md](deletion-and-tombstones.md).
