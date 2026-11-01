# 0004 — Atomic, append-only, hash-chained audit history

Date: 2026-11-01 (recorded from the implementation)

Status: Accepted

## Context

A change without its history would undermine accountability; concurrent writes must share one chain.

## Decision

Call audit.record in the business transaction. Serialize appends with a PostgreSQL advisory lock and hash canonical row JSON with the previous hash. Reject UPDATE, DELETE and TRUNCATE with triggers.

## Consequences

Rollback removes both change and event. Audit writes serialize. A retained external chain tip is needed against privileged tail removal; details in [audit](../audit.md).

## Alternatives considered

Signals alone cannot cover all service decisions. Plain log files do not commit atomically with database changes.
