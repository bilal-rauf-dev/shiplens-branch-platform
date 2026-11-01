# 0015 — Limit raw SQL to reviewed infrastructure exceptions

Date: 2026-11-01 (recorded from the implementation)

Status: Accepted

## Context

The ORM cannot express PostgreSQL trigger functions, an advisory transaction lock, sequence reservation or a connection-level readiness probe.

## Decision

Keep integrity triggers/composite-FK DDL in reversible migrations. audit/services.py uses fixed parameterized SQL for pg_advisory_xact_lock and pg_get_serial_sequence/nextval. core/selectors.py uses literal SELECT 1 on a copied, short-timeout connection. seed/services.py uses only a fixed quoted table list for transactional trigger DDL and TRUNCATE during guarded CLI rebuild.

## Consequences

No HTTP input becomes SQL syntax. The audit lock prevents chain forks; reserved IDs are hashed before insert. Health reads no application data. Demo rebuild disables USER triggers only and rolls back data, sequences and DDL on failure. A DB owner can still bypass protections; see [security](../security.md) and [audit](../audit.md). Test mutation/cleanup SQL is test-only.

## Alternatives considered

A blanket SQL ban cannot implement these guarantees. General raw-query helpers would widen the reviewed surface. Dropping/recreating the public schema was planned but is not used.
