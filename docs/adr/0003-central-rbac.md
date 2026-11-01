# 0003 — Central RBAC matrix and scoped querysets

Date: 2026-11-01 (recorded from the implementation)

Status: Accepted

## Context

Five business roles have different actions and branch access; Super Admin must not approve finance reports.

## Decision

Use accounts/permissions.py plus the default-deny route registry. Filter querysets before lookup, and recheck permissions in services. Do not use Django groups or admin permission flags.

## Consequences

The generated [matrix](../permissions.md) and route tests expose permission changes. Foreign branch IDs return 404; role denials return 403.

## Alternatives considered

Scattered role checks can drift. Django model permissions do not directly express these branch and workflow rules.
