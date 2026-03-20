# Audit and Provenance

## Provenance minimum fields
For summaries, facts, and canonical items:
- source item ID
- source system
- captured timestamp
- derivation process
- derivation timestamp
- session or conversation ID where available
- import method
- source excerpt or hash
- modifying user or client identity where applicable

## Audit-event minimum fields
- timestamp
- client or agent identity
- operation type
- result count
- target or query summary
- retrieval mode
- success or failure status
- touched source or item IDs where applicable
- policy decision reason when access is limited

## Retention
- minimum 90-day access-event retention in v1

## Export policy baseline
By default, portability exports should include audit metadata retained within the active 90-day retention window, subject to export policy redaction of sensitive transport/session details where required.

Operational backups remain the authoritative recovery path for full audit fidelity.

## Visibility model
- default UI shows event list plus detail drawer
- configuration may enable deeper visibility
- provenance and audit must remain linked to review surfaces
