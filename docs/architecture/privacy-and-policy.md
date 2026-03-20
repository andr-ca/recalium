# Privacy and Policy

## Default posture
- local-first storage
- localhost-first exposure
- explicit opt-in for external providers
- conservative extraction behavior

## Sensitive-content policy
Sensitive categories include at least:
- personal profile
- relationships

Sensitive detection uses:
1. user-declared sensitivity
2. local rule-based pre-classification

If content is unknown or low-confidence, external processing is blocked by default.

## Policy hooks needed in v1
Even though v1 is single-user, the architecture should keep explicit policy decision points for:
- external provider eligibility
- retrieval suppression
- deletion/redaction propagation
- network exposure mode
- future service/tenant policies
- configured exclusion from embedding and indexing by category or source

## Deletion and redaction policy
- derived summaries, facts, embeddings, and search visibility are immediately suppressed
- canonical entries with removed sources remain but require review and source-removed marking
- future backups/exports exclude removed data
- old backups/exports must be flagged as potentially containing removed data

The enforceable mechanism for this behavior is a durable tombstone/deletion-ledger model. See [deletion-and-tombstones.md](deletion-and-tombstones.md).
