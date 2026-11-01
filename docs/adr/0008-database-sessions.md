# 0008 — Database session cookies instead of JWT

Date: 2026-11-01 (recorded from the implementation)

Status: Accepted

## Context

The browser uses same-origin forms, and staff access must be revocable.

## Decision

Use Django database sessions with CSRF-protected forms. Session middleware enforces idle and absolute expiry. Password reset and deactivation revoke sessions.

## Consequences

No browser token storage or refresh protocol. Production uses secure Host-prefixed cookies; see [security](../security.md). Session reads use the shared database.

## Alternatives considered

JWT is useful for independent API clients, which this application does not have. Stateless tokens complicate immediate revocation.
