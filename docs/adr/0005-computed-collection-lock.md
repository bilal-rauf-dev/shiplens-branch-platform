# 0005 — Compute collection locks from entry creation time

Date: 2026-11-01 (recorded from the implementation)

Status: Accepted

## Context

Backdating a collection must not extend the edit period; sleeping hosting cannot depend on cron.

## Decision

Compute lock_at from created_at plus rules.get("collection_lock_days"), default seven days. At equality, edit and void are refused. There is no unlock action.

## Consequences

Rule changes apply immediately. Sent and closed-week guards can block sooner. Adjustment fields exist, but an adjustment workflow is not implemented; see BR-067 in [rules](../business-rules.md).

## Alternatives considered

Locking from collection_date trusts user input. A scheduled status update can run late or be missed.
