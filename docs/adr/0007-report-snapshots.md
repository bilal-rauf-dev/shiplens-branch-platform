# 0007 — Report snapshots and revision line items

Date: 2026-11-01 (recorded from the implementation)

Status: Accepted

## Context

A submitted figure must survive later receipt changes and review races.

## Decision

Submit/resubmit increments revision, hashes a snapshot and inserts copied lines. Retain older revision rows. Approval writes Approved then Locked with two audit events in one transaction.

## Consequences

Dashboard approval sums use only current-revision lines of Locked reports. Review checks expected_revision. Locked parent/line triggers reject mutation. Return comments live in audit metadata.

## Alternatives considered

Live sums would rewrite past approvals. Keeping older lines only in audit JSON would make revision queries harder.
