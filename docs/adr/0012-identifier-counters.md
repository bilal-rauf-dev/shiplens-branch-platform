# 0012 — Locked counters for human-readable identifiers

Date: 2026-11-01 (recorded from the implementation)

Status: Accepted

## Context

Branch codes and yearly member/application references must stay unique under concurrent creation.

## Decision

Use core.ids.next_value inside the caller transaction: get_or_create the named counter, select_for_update it, then increment. Format IDs in the creating service.

## Consequences

Rollback restores the counter. Separate city/year/branch keys limit contention. IDs remain readable; scoped queries provide access control.

## Alternatives considered

MAX(id)+1 races. UUIDs are less convenient for receipts. Raw SQL upserts are unnecessary because ORM savepoints handle the first-row race.
