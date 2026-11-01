# 0002 — PostgreSQL constraints and triggers as the final guard

Date: 2026-11-01 (recorded from the implementation)

Status: Accepted

## Context

Service checks alone cannot protect records from accidental ORM writes or competing requests.

## Decision

Use model constraints for uniqueness and valid fields. Reversible migration SQL adds immutable identity, same-branch membership, transfer, report and audit guards.

## Consequences

Tests require PostgreSQL, never SQLite. Schema changes must account for triggers. A database owner can disable guards; see [security](../security.md).

## Alternatives considered

Only Python validation is simpler but bypassable. Database-specific guards are accepted because PostgreSQL 16 is fixed.
