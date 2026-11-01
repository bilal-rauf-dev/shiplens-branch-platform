# 0014 — Keep demo rebuild an operator-only command

Date: 2026-11-01 (recorded from the implementation)

Status: Accepted

## Context

The handbook requires append-only audit history even for Super Admin; a reset button would undermine that boundary.

## Decision

Expose seed_demo --reset only as an operator management command. Require DEMO_MODE=true and a configured password. Rebuild only fictional data, then record demo.reset in the new history.

## Consequences

No HTTP route, action permission or button can reset data. Rebuild destroys changes, audit history, overrides and sessions. The operator must preserve needed evidence first; see [audit](../audit.md).

## Alternatives considered

A Super Admin reset route violates the handbook audit rule. Startup always resetting would erase judges' changes on redeploy.
