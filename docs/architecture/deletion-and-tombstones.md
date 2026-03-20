# Deletion, Redaction, and Tombstones

## v1 architecture decision
Use explicit deletion/redaction tombstones and a deletion ledger so removed content cannot silently reappear after restore, reindex, or import.

## Core model
For any deleted or redacted source item, persist durable removal metadata including:
- source item ID
- removal type: delete or redact
- removal timestamp
- removing user/client identity where applicable
- reason or policy note where applicable
- suppression scope

## Live-state behavior
When a source item is removed:
- linked derived summaries, facts, embeddings, and search visibility are immediately suppressed
- suppression state is represented in durable records
- canonical entries tied to the source remain but move into source-removed review-required state

## Restore behavior
During restore:
- tombstones are restored with the dataset
- any restored artifacts linked to tombstoned sources remain suppressed
- post-restore consistency verification must reapply suppression guarantees before the dataset is activated

## Export/import behavior
- future exports exclude removed data
- export manifests record deletion-state assumptions
- import logic must honor tombstones where present and must not reactivate removed items accidentally

## Reprocessing behavior
- reprocessing must consult deletion/redaction tombstones before regenerating derived outputs
- tombstoned sources are not eligible for normal derived-memory regeneration unless explicitly restored through a supported future workflow

## Audit linkage
Removal events and resulting suppression actions must be auditable.

## Future-service compatibility
A durable tombstone model is required so deletion semantics remain enforceable across local, hosted, and migration scenarios.
