# Security and Identity

## Exposure modes
### Localhost-only mode
Default v1 posture:
- UI, API, and MCP bind to localhost only
- no remote network reachability is assumed
- local operator trust is simplified but audit still records client identity where available

### Exposed mode
If the user explicitly enables broader exposure:
- each exposed interface must require authentication
- UI requires authenticated session handling
- API/MCP require authenticated client identity
- transport protection is mandatory
- audit events must record the authenticated identity used for the call

## Identity model
### Human user identity
In localhost-only mode:
- a single local operator identity may be assumed for UI actions
- mutation and restore actions should still record the acting identity as local user/operator

In exposed mode:
- authenticated user identity must be explicit
- session identifiers must map to user identity in audit

### MCP/API client identity
- each MCP or API client must present a stable client identity in exposed mode
- in localhost-only mode, configured local client identifiers may be accepted for auditability
- identity must flow from transport boundary into audit and provenance metadata where applicable

## Session handling
For UI in exposed mode:
- authenticated session required
- session expiration and renewal policy required
- state-changing operations should require an authenticated session context

## Restore and secrets boundary
- restored datasets may require the operator to re-supply secrets or provider credentials that are intentionally excluded from backup scope
- restore flows must clearly distinguish restored configuration from operator-managed secrets

## Transport protection
For exposed mode:
- encrypted transport is required for remote access
- plaintext remote exposure is not acceptable

## Security decision points
- whether an interface is localhost-only or exposed
- whether a client identity is sufficient for requested operation
- whether a provider call is allowed for the content
- whether a retrieval result must suppress certain items due to policy

## Audit linkage
Every authenticated or locally identified call should propagate:
- user/client identity
- interface used
- operation type
- success/failure outcome
- relevant policy decision reason when limited or blocked
