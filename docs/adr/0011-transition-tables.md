# 0011 — Explicit transition tables instead of an FSM library

Date: 2026-11-01 (recorded from the implementation)

Status: Accepted

## Context

Workflow decisions must be readable and changes easy to explain.

## Decision

Use plain tables for branch, member, report and content transitions. Services lock rows, check permission/state and apply guards. Application decisions use explicit Pending checks; collection state is computed.

## Consequences

No FSM dependency or hidden hooks. Each service owns its audit events and error behavior. The implementation does not force every entity into one generic transition engine.

## Alternatives considered

An FSM package reduces some repetition but obscures flow. Nested view conditionals would mix validation with persistence.
