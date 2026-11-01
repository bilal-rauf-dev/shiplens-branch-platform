# 0010 — Render hosting and migrations at startup

Date: 2026-11-01 (recorded from the implementation)

Status: Accepted

## Context

The demonstration needs reproducible hosting within the free-tier constraints.

## Decision

Use the Docker Blueprint in render.yaml. bin/start.sh runs the single-process startup command before Gunicorn: migrate, createcachetable, then seed_demo --if-empty in demo mode and generate_weekly_drafts in every mode.

## Consequences

Deployments retain demo changes after first seed. Free web cold starts and database expiry require operator attention. Multiple simultaneous deploy instances would need a migration strategy review; see the [runbook](../handover.md).

## Alternatives considered

Paid pre-deploy commands and paid database retention reduce operational constraints. A separate migration service adds coordination.
