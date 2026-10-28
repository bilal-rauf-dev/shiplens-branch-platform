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
