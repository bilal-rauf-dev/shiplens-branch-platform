# Implemented business rules

This catalogue traces [planning/07](planning/07-business-rules.md) to the current
implementation. A source reference names a file and function/class; migration
references name database enforcement. Test references name existing pytest tests,
not proposed test IDs. Read [permissions](permissions.md), [security](security.md)
and [audit](audit.md) for cross-cutting details.

Public field validation is authoritative in ApplicationForm; submit_application
accepts its cleaned data and separately rechecks branch/consent. The table does
not imply that every public field validator is repeated in that service.

| Rule | Actual behavior / implementation status | Enforced in file:function | Tested by test name |
| --- | --- | --- | --- |
| BR-001 | Per-city BR-{CITY}-{NN} branch codes, widening beyond 99. | apps/branches/services.py:create_branch | tests/branches/test_register.py:test_t_brn_code_format |
| BR-002 | Branch codes cannot change; closed branches retain them. | apps/branches/services.py:update_branch; apps/branches/migrations/0004_complete_register.py | tests/branches/test_register.py:test_t_brn_code_immutable |
| BR-003 | M-{YYYY}-{NNNNN} IDs use the Karachi acceptance year and a yearly counter. | apps/volunteers/services.py:accept_application | tests/volunteers/test_decisions.py:test_t_mem_id_format_and_accept_fields |
| BR-004 | Application, collection and transfer references use separate locked counters. | apps/volunteers/services.py:submit_application; apps/finance/services.py:create_collection/create_transfer | tests/volunteers/test_public.py:test_t_app_submit_ok_and_consent; tests/finance/test_create.py:test_t_col_create; tests/finance/test_transfers.py:test_transfer_total_and_audit |
| BR-005 | City codes are three unique uppercase ASCII letters. | apps/branches/services.py:create_city; apps/branches/models.py:City.Meta | tests/branches/test_register.py:test_t_city_code |
| BR-010 | Branch state/action pairs follow BRANCH_TRANSITIONS; Closed is terminal. | apps/branches/services.py:transition | tests/branches/test_lifecycle.py:test_t_brn_transitions |
| BR-011 | Unsent money and Submitted/Resubmitted/Returned reports block closing. | apps/branches/services.py:close_blockers | tests/finance/test_scope_and_close.py:test_branch_close_blocked_until_sent; tests/finance/test_report_acceptance.py:test_branch_close_blocked_by_open_report |
| BR-012 | English branch names are case-insensitively unique within a city. | apps/branches/models.py:Branch.Meta | tests/branches/test_register.py:test_t_brn_name_unique |
| BR-013 | Only Forming, Active and Paused branches appear publicly. | apps/branches/selectors.py:public_branches | tests/branches/test_screens.py:test_t_pub_branch_visibility |
| BR-014 | New lead assignments cannot target Closed branches; existing links remain. | apps/accounts/services.py:assign_branch | tests/branches/test_lifecycle.py:test_t_assign_closed_keeps_history_and_rejects_new_assignments |
| BR-040 | Trim/collapse name whitespace; allow Unicode letters/marks and specified punctuation, 3–100 characters. | apps/volunteers/forms.py:ApplicationForm.clean_full_name | tests/volunteers/test_validation.py:test_t_app_validation_name |
| BR-041 | Validate email (max 254) and store lowercase. | apps/volunteers/forms.py:ApplicationForm.clean_email | tests/volunteers/test_validation.py:test_form_normalises_email_and_keeps_only_explicit_fields |
| BR-042 | Normalize Pakistani mobile formats, stripping spaces/dashes, to +923 plus nine digits. | apps/volunteers/forms.py:ApplicationForm.clean_phone | tests/volunteers/test_validation.py:test_t_app_validation_phone |
| BR-043 | Completed-birthday age must be 16–100 by default; use Karachi today and configured bounds. | apps/volunteers/forms.py:ApplicationForm.clean | tests/volunteers/test_validation.py:test_t_app_validation_age |
| BR-044 | Guardian consent is required below 18. | apps/volunteers/forms.py:ApplicationForm.clean | tests/volunteers/test_validation.py:test_t_app_validation_age |
| BR-045 | Application branch must exist and be Active/Forming; there is no separate city input. | apps/volunteers/services.py:submit_application | tests/volunteers/test_public.py:test_service_rechecks_branch_and_consent |
| BR-046 | PARTIAL: required interests and max five are validated, but choices are static INTERESTS, not published Program slugs. | apps/volunteers/forms.py:ApplicationForm.clean_interests; apps/volunteers/constants.py:INTERESTS | tests/volunteers/test_validation.py:test_t_app_validation_interests |
| BR-047 | Require at least one availability from the three declared values. | apps/volunteers/forms.py:ApplicationForm | tests/volunteers/test_validation.py:test_t_app_validation_required_choices |
| BR-048 | Motivation is trimmed plain text, 20–1000 characters. | apps/volunteers/forms.py:ApplicationForm.clean_motivation | tests/volunteers/test_validation.py:test_t_app_validation_motivation |
| BR-049 | Preferred language is en/ur and defaults to the current interface language. | apps/volunteers/forms.py:ApplicationForm.__init__ | tests/volunteers/test_public.py:test_urdu_form_defaults_to_urdu |
| BR-050 | Require privacy consent and store consent_at. | apps/volunteers/services.py:submit_application | tests/volunteers/test_public.py:test_t_app_submit_ok_and_consent |
| BR-051 | Honeypot and signed timing produce fake success without an application; hourly/daily IP limits and CSRF apply. | apps/volunteers/services.py:spam_reason/application_rate_limited/discard_spam | tests/volunteers/test_public.py:test_t_app_spam_honeypot/test_t_app_spam_timing/test_t_app_spam_rate |
| BR-052 | Flag a matching Pending application or non-Left member without revealing duplicates publicly. | apps/volunteers/services.py:submit_application; apps/volunteers/selectors.py:duplicate_application/duplicate_member | tests/volunteers/test_public.py:test_t_app_dup_flag_and_no_enum |
| BR-053 | Accept/decline/reassign only Pending applications under row lock; decline reason is 5–500 characters. | apps/volunteers/services.py:_lock_pending_application/decline_application | tests/volunteers/test_decisions.py:test_t_app_terminal |
| BR-054 | Acceptance creates exactly one member, links both records and records two events in one transaction. | apps/volunteers/services.py:accept_application | tests/volunteers/test_decisions.py:test_t_app_accept_atomic |
| BR-055 | Non-Left member email is unique ignoring case, including reinstatement races. | apps/volunteers/models.py:Member.Meta; apps/volunteers/services.py:transition_member | tests/volunteers/test_models.py:test_t_mem_email_unique_and_immutable_id |
| BR-056 | Member team must belong to their branch; composite FK also protects direct writes. | apps/volunteers/services.py:accept_application/update_member; apps/volunteers/migrations/0003_member_integrity.py | tests/volunteers/test_management.py:test_t_mem_team_branch_service_and_raw_sql |
| BR-057 | Team names are unique ignoring case within a branch. | apps/volunteers/services.py:_validate_team_name; apps/volunteers/models.py:Team.Meta | tests/volunteers/test_management.py:test_t_team_unique_service_and_rename |
| BR-058 | Member state changes use MEMBER_TRANSITIONS; leaving date is required and cannot precede joining. | apps/volunteers/services.py:transition_member; apps/volunteers/models.py:Member.Meta | tests/volunteers/test_member_detail.py:test_t_mem_status_every_state_action |
| BR-059 | Scoped case-insensitive member search, normalized phone search and AND-combined filters. | apps/volunteers/selectors.py:search_members | tests/volunteers/test_member_search.py:test_t_mem_search_each_field/test_t_mem_search_combined_filters |
| BR-060 | Positive finite Decimal amount, maximum 10,000,000 and at most two decimal places. | apps/finance/services.py:validated_values | tests/finance/test_create.py:test_t_col_amount_rejected/test_t_col_amount_boundaries |
| BR-061 | Cash, Cheque and Bank deposit only; no online payments. | apps/finance/services.py:validated_values; apps/finance/models.py:Collection.Meta | tests/finance/test_create.py:test_t_col_method |
| BR-062 | Collection date is between Karachi today minus configured lock days and today, inclusive. | apps/finance/services.py:validated_values | tests/finance/test_create.py:test_t_col_date_range_pkt |
| BR-063 | Receipt has 1–30 allowed characters and is unique per branch. | apps/finance/services.py:validated_values/create_collection; apps/finance/models.py:Collection.Meta | tests/finance/test_create.py:test_t_col_receipt_unique |
| BR-064 | At created_at plus configured lock days, edit and void are denied for every role; no unlock exists. | apps/finance/models.py:Collection.lock_at/save; apps/finance/services.py:assert_editable | tests/finance/test_lock.py:test_t_col_lock_before_and_at/test_t_col_lock_config |
| BR-065 | Submitted/Resubmitted/Approved/Locked weeks block create/edit/void; Returned reopens subject to the original age lock. | apps/finance/services.py:assert_editable/validated_values; apps/finance/report_selectors.py:week_is_closed | tests/finance/test_report_acceptance.py:test_t_rpt_snapshot_and_t_col_week_closed/test_t_col_week_closed_create_and_void |
| BR-066 | New collections require an Active branch. | apps/finance/services.py:create_collection | tests/finance/test_create.py:test_t_col_branch_active |
| BR-067 | NOT IMPLEMENTED: adjustment columns and DB checks are reserved; no adjustment service, form or route implements reasons/date rules. See [correcting a mistake](finance.md#correcting-a-mistake) for current limits and escalation. | — | — (no adjustment workflow test) |
| BR-068 | Void retains the row, needs a 5–300 character reason and removes it from live totals and unsent. | apps/finance/services.py:_change_collection; apps/finance/selectors.py:branch_unsent_totals | tests/finance/test_lock.py:test_t_col_void_and_edit_diff |
| BR-069 | Transfer selects whole non-voided unsent collections from one branch; compute exact total and validate date under locks. | apps/finance/services.py:create_transfer | tests/finance/test_transfers.py:test_t_xfer_rules |
| BR-070 | Sent financial fields and all transfers are immutable; there is no edit route for transfers. | apps/finance/services.py:assert_editable; apps/finance/migrations/0002_transfer_guards.py | tests/finance/test_transfers.py:test_t_xfer_immutable_raw_sql |
| BR-071 | Unsent means transfer is null and voided_at is null; age uses collection_date. | apps/dashboard/kpis.py:k4/l1; apps/finance/selectors.py:branch_unsent_totals | tests/dashboard/test_t_dash_seed.py:test_t_dash_seed_l1_unsent_rows |
| BR-080 | Weeks are fixed Monday–Sunday in Karachi; week_start_day is not a supported settings-page override. | apps/finance/report_selectors.py:week_bounds; apps/finance/models.py:WeeklyReport.Meta | tests/finance/test_reports.py:test_t_rpt_week |
| BR-081 | Exactly one report per branch/week. | apps/finance/models.py:WeeklyReport.Meta | tests/finance/test_reports.py:test_t_rpt_unique |
| BR-082 | Draft missing weeks at every production startup, on Branch Lead Reports-list access or by command, idempotently for Active branches with an opening date. | apps/finance/report_services.py:ensure_drafts | tests/finance/test_reports.py:test_t_rpt_autodraft_idempotent; tests/seed/test_startup_drafts.py:test_t_rpt_autodraft_startup_after_seed |
| BR-083 | Live weekly non-voided sums, methods, transfer-date unsent balance and member/application counts; active-member history uses current status. | apps/finance/report_selectors.py:report_aggregates | tests/finance/test_reports.py:test_t_rpt_aggregates_spanning_months/test_report_member_and_application_counts |
| BR-084 | REPORT_FIELDS defines activities, volunteer_hours and issues with shared form/service validation. | apps/finance/report_forms.py:ReportNarrativeForm; apps/finance/report_fields.py:REPORT_FIELDS | tests/finance/test_reports.py:test_t_rpt_field_registry |
| BR-085 | Submit after week end unless current-week submission is enabled; future weeks remain blocked. | apps/finance/report_services.py:transition | tests/finance/test_report_acceptance.py:test_submit_current_week_refused |
| BR-086 | Submit/resubmit copies totals, narrative and lines, increments revision and hashes canonical JSON. Older line revisions remain. | apps/finance/report_services.py:transition | tests/finance/test_report_transitions.py:test_report_service_lifecycle_and_frozen_revisions |
| BR-087 | Return requires a trimmed 5–1000 character comment. | apps/finance/report_services.py:transition | tests/finance/test_report_acceptance.py:test_stale_review_and_empty_return_comment |
| BR-088 | Approve/return requires reviewable state and matching expected_revision under row lock. | apps/finance/report_services.py:transition | tests/finance/test_report_acceptance.py:test_t_rpt_concurrent_review |
| BR-089 | Locked reports/lines reject changes; line insertion and parent moves are protected too. | apps/finance/migrations/0004_report_immutability.py; apps/finance/report_services.py:transition | tests/finance/test_report_acceptance.py:test_t_rpt_locked_immutable |
| BR-090 | Approved totals use Locked reports and current revision lines, filtered by line date. | apps/dashboard/kpis.py:k2 | tests/dashboard/test_t_dash_seed.py:test_t_dash_seed_october_reference_values |
| BR-120 | Slugs derive from English title if omitted; 3–80 lowercase letters/digits/hyphens and unique per content type. | apps/cms/services.py:create; apps/cms/models.py:ContentItem.Meta | tests/cms/test_services.py:test_t_cms_slug/test_slug_is_unique_per_type |
| BR-121 | Publishing needs English title/body plus Urdu title; Urdu body can fall back visibly. Updates require both locales. | apps/cms/services.py:transition/update; apps/cms/selectors.py:localize | tests/cms/test_services.py:test_t_cms_publish_guard/test_urdu_empty_body_falls_back_with_note |
| BR-122 | Events require start/end with end >= start; selectors separate past events using the clock. | apps/cms/services.py:_validate; apps/cms/models.py:ContentItem.Meta; apps/publicsite/selectors.py:event_groups | tests/cms/test_services.py:test_t_cms_event_dates |
| BR-123 | Convert Markdown then allow-list with nh3 on save and render; links receive noopener. | apps/cms/sanitizing.py:from_markdown/sanitize; apps/cms/templatetags/cms.py:render_cms | tests/cms/test_services.py:test_t_sec_xss_cms |
| BR-130 | Domain service changes and audit commit together; framework auth signals use transaction wrappers. | apps/audit/services.py:record; apps/audit/signals.py | tests/audit/test_log.py:test_t_aud_atomic; tests/rbac/test_matrix.py |
| BR-131 | Reject audit UPDATE/DELETE/TRUNCATE with database triggers. Operator demo rebuild is a separate destructive boundary. | apps/audit/migrations/0002_immutable_audit.py | tests/audit/test_log.py:test_t_aud_immutable |
| BR-132 | SHA-256 chains canonical stored rows under one transaction advisory lock; reserved sequence ID is hashed. | apps/audit/services.py:record/verify_chain | tests/audit/test_log.py:test_t_aud_chain/test_t_aud_chain_concurrent_writers |
| BR-133 | Recursively redact password/token/secret keys in before/after/metadata and retain changed fields only. | apps/audit/services.py:redact/diff | tests/audit/test_log.py:test_t_aud_redact_and_diff |
| BR-140 | Store aware timestamps with USE_TZ; shared clock produces Karachi business dates. | apps/core/clock.py:now/today; config/settings/base.py | tests/core/test_clock.py:test_t_clock_pkt |
| BR-141 | Domain code uses the shared patchable clock; Ruff bans direct timezone.now/date.today outside clock.py. | pyproject.toml:tool.ruff.lint.flake8-tidy-imports.banned-api | tests/core/test_clock.py:test_clock_override_is_context_and_thread_local (clock); ruff check . (direct-call ban) |

## Dashboard range BR-100–BR-110

Planning/07 reserves this range and refers to planning/09, which labels formulas
K1–K10, TR1/TR2 and L1/L2 without assigning individual BR numbers. No individual
BR-100 through BR-110 definition is present, so this catalogue keeps the actual
KPI names rather than inventing a mapping. These formulas are implemented:

| Formula | Enforced in file:function | Tested by test name |
| --- | --- | --- |
| K1 (planning/09 §2) | apps/dashboard/kpis.py:k1 | tests/dashboard/test_t_dash_seed.py:test_t_dash_seed_october_reference_values |
| K2 (planning/09 §2) | apps/dashboard/kpis.py:k2 | tests/dashboard/test_t_dash_seed.py:test_t_dash_seed_october_reference_values |
| K3 (planning/09 §2) | apps/dashboard/kpis.py:k3 | tests/dashboard/test_t_dash_seed.py:test_t_dash_seed_october_reference_values |
| K4 (planning/09 §2) | apps/dashboard/kpis.py:k4 | tests/dashboard/test_t_dash_seed.py:test_t_dash_seed_october_reference_values |
| K5 (planning/09 §2) | apps/dashboard/kpis.py:k5 | tests/dashboard/test_t_dash_seed.py:test_t_dash_seed_october_reference_values |
| K6 (planning/09 §2) | apps/dashboard/kpis.py:k6 | tests/dashboard/test_t_dash_seed.py:test_t_dash_seed_october_reference_values |
| K7 (planning/09 §2) | apps/dashboard/kpis.py:k7 | tests/dashboard/test_t_dash_seed.py:test_t_dash_seed_october_reference_values |
| K8 (planning/09 §2) | apps/dashboard/kpis.py:k8 | tests/dashboard/test_t_dash_seed.py:test_t_dash_seed_october_reference_values |
| K9 (planning/09 §2) | apps/dashboard/kpis.py:k9 | tests/dashboard/test_t_dash_seed.py:test_t_dash_seed_october_reference_values |
| K10 (planning/09 §2) | apps/dashboard/kpis.py:k10 | tests/dashboard/test_t_dash_seed.py:test_t_dash_seed_october_reference_values |
| TR1/TR2: twelve zero-filled monthly points | apps/dashboard/kpis.py:tr1/tr2 | tests/dashboard/test_t_dash_seed.py:test_t_dash_trends |
| L1: oldest unsent entries | apps/dashboard/kpis.py:l1 | tests/dashboard/test_t_dash_seed.py:test_t_dash_seed_l1_unsent_rows |
| L2: per-branch totals and latest report | apps/dashboard/kpis.py:l2 | tests/dashboard/test_t_dash_seed.py:test_t_dash_seed_l2_per_branch |

The dashboard uses the current month when populated, otherwise the latest month
with collections. An explicit empty month remains empty. as_of limits creation
and relevant event dates, but does not reconstruct historical statuses after
later changes. Unsent ages/compliance follow the current business date in UI.

## Differences from the earlier plan

- BR-046 uses fixed interest choices rather than published program slugs.
- BR-067 has schema support only; there is no correction/adjustment workflow.
- BR-080 remains Monday-based; changing a settings value cannot change week boundaries.
- Resubmission retains line revisions in rows, rather than only audit before data (planning/06).
- Return comments are audit metadata, and auto-lock has a system actor (planning/06 and planning/17).
- CMS event dates in sample_data/content.csv are fixed, not relative to import time (planning/09).
- Dashboard fallback follows the amended assumption in planning/21, rather than planning/09's original current-month-only default.
