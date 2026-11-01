# 0006 — Lazy weekly report drafting instead of cron

Date: 2026-11-01 (recorded from the implementation)

Status: Accepted

## Context

Free hosting sleeps and has no required worker or scheduler.

## Decision

Run generate_weekly_drafts at every production start, after migrations, cache-table creation and any demo seed. It also runs outside demo mode; an empty database needs no drafts. Keep Branch Lead Reports-list access as a trigger for a process that stays running across Monday 00:00 PKT. Both paths use the unchanged ensure_drafts service, which locks the branch and uses get_or_create with a unique branch/week constraint.

## Consequences

Missing weeks since opening are filled once, including the current week. Paused, Closed and Forming branches get no new drafts. Repeated runs add no duplicate rows or report.drafted events; the command counts only newly created reports.

Draft rows change neither K8's awaiting/returned counts nor K9's submitted-week compliance. L2's latest-report column does change: once drafting runs, an Active branch shows the current week's Draft, rather than the older R10 listed for Karachi in planning/09. Historical report states and money remain unchanged.

## Alternatives considered

A dashboard GET trigger would row-lock every Active branch on every dashboard load without changing K8/K9. The optional OPT-06 bearer-token endpoint would need a csrf_exempt path for its non-browser caller, contrary to AGENTS.md §5; no such endpoint is added. Render cron is paid. Startup plus the existing Reports-list trigger avoids those costs and access-boundary changes. Drafting only the current week would leave gaps after inactivity.
