# 0006 — Lazy weekly report drafting instead of cron

Date: 2026-11-01 (recorded from the implementation)

Status: Accepted

## Context

Free hosting sleeps and has no required worker or scheduler.

## Decision

Call ensure_drafts for an Active branch on Branch Lead Reports-list access; offer generate_weekly_drafts for operators. Lock the branch and use get_or_create with a unique branch/week constraint.

## Consequences

Missing weeks since opening are filled once, including the current week. Paused/Closed branches get no new drafts. There is no internal HTTP generation endpoint.

## Alternatives considered

Cron or Celery requires extra operations. Drafting only the current week would leave gaps after inactivity.
