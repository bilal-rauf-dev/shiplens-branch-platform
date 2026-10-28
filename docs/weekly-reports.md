# Weekly reports

Report code lives in finance's report_fields, report_forms, report_selectors and
report_services modules. REPORT_FIELDS is the single narrative registry: adding
one entry adds both the form field and the validation used by services.

week_bounds accepts Karachi business dates or aware timestamps, converting the
latter before choosing Monday–Sunday. Drafts are created idempotently for Active
branches from the opening week through this week. A missing opening date produces
no drafts rather than inventing historical dates. Run generate_weekly_drafts to
create missing weeks for all Active branches; page loads will use the same service.

Live aggregates use current non-voided collections. Unsent at week end uses the
recorded transfer date; active_members_end follows BR-083's explicit current-status
approximation. Later dashboard approved figures must use current-revision report
lines, never live collections. Revision lines remain separate rather than replaced.

Database constraints enforce week boundaries, uniqueness, status and lock fields.
Locked report rows reject updates/deletes. Line triggers also reject inserts into
a locked report and moving lines to or from one, and take a parent share lock to
serialize against approval.

## Transitions and snapshots

One transition function checks permissions, state and expected review revision.
It locks the branch before the report, matching collection writes and branch close.
Submit/resubmit validates the shared narrative form, increments revision, inserts
new revision lines and hashes canonical JSON containing the aggregates, narrative
and copied lines. Old revision rows remain unchanged. Narrative-only saves are
allowed in Draft/Returned and audited separately without increasing revision.

Return needs a configured-length comment. Approve first records Approved, then
sets Locked and records the automatic system lock, in the same transaction.
The system event keeps the HTTP request context when approval came from a view.
An audit failure at either stage rolls everything back. Submitted/Resubmitted/
Approved/Locked weeks block collection writes; Returned weeks reopen, subject to
the original seven-day lock. Submitted/Resubmitted/Returned reports block closing
the branch. Current-week submission is configurable; future weeks remain blocked.

## Screens and permissions

The scoped report list lazily creates drafts only for a Branch Lead's Active
branches. Finance and Super Admin read all reports. Branch, status and week-start
date filters preserve their values when moving between pages of 25 reports.
Finance's review queue contains Submitted/Resubmitted reports, oldest submission
first. Super Admin has read access through the list, with no review controls.

Draft/Returned details show live figures and an editable narrative for the assigned
lead. Submitted/Resubmitted details show pending snapshot figures and a finance
review panel carrying expected_revision. Locked details show approved figures,
approver and Karachi time. The shared history partial shows each report's audit
events and review comments. All successful form posts redirect back to detail
with a translated message; validation errors return 400 and state conflicts 409.
Navigation, forms, headings and feedback have English/Urdu translations.

## Acceptance checks

test_t_rpt_lifecycle drives the six-event draft/submit/return/resubmit/approve/lock
sequence through HTTP with real request UUIDs, checks actor roles and verifies the
audit chain. Other acceptance tests check old and new revision amounts, direct SQL
update/delete guards, exactly one winner during concurrent approval, closed-week
collection create/edit/void refusals and branch-close blockers.

P7's explicit requirements resolve three older wording differences in the plan:
revision lines are retained in their own rows (rather than kept only in audit
before data), return comments go in audit metadata, and the lifecycle's sample
comment is longer than "fix" to satisfy BR-087's five-character minimum. System
draft and lock events use the existing null user/blank role and "system" label;
HTTP-triggered system events keep the same request UUID as the triggering request.
