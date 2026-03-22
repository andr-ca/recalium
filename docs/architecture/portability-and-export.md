# Portability and Export

## Goals
- preserve user ownership
- support re-importable machine-readable export
- support human-browsable archive export
- keep operational backup separate from portability export

## Export types
### Machine-readable export
Format:
- JSON bundle

Contents:
- raw archive records
- summaries
- structured facts
- canonical memory
- provenance metadata
- retained audit metadata included by export policy; default v1 policy includes audit metadata within the active retention window while allowing redaction of sensitive transport/session details
- manifest with export version and compatibility metadata

### Human-readable export
Format:
- zip archive containing Markdown plus assets

Structure:
- top-level index
- type-based folders
- manifest metadata preserving provenance and source/session links
- assets folder for any exported binary or linked material

## Import flow
1. import manifest is validated
2. export version compatibility is checked
3. preview/validation reports issues before commit where feasible
4. import is routed through normalized ingest/import services rather than ad hoc writes

## Versioning
Both export formats require:
- schema/version marker
- producer version marker
- compatibility notes or migration path indicator

## Ownership boundaries
### Backup vs export
Backups:
- operational recovery artifacts
- optimized for restore fidelity
- may include operational state required for system recovery

Exports:
- user portability artifacts
- optimized for re-import and inspection
- should remain stable across deployment profiles where possible
- default audit inclusion should follow the portability export policy, not backup fidelity rules

## Deletion/redaction interaction
- future exports exclude deleted/redacted content
- prior exports are flagged as potentially containing removed content
- export manifests should record export time and deletion-state assumptions

## Architecture implications
- export generation should read stable domain models rather than raw table dumps
- import should use version-aware adapters
- portability contracts should survive future hosted/service profiles without bespoke conversions
