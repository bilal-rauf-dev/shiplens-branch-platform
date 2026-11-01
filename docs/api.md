# Route reference

Generated — do not edit by hand. Run `python manage.py export_routes`.
Sources: Django URL resolver, `apps/core/routes.py` and
`apps/accounts/permissions.py`. See [permissions](permissions.md) for
the action matrix and [architecture](architecture.md) for request flow.

Paths show typed resolver parameters, for example `<int:pk>`; these are
database IDs, not sample labels such as R9. Both configured locales are
expanded. Static assets are served by WhiteNoise, outside this resolver.

Methods describe view dispatch after middleware checks. Class views include
inherited handlers (including PUT on Django FormView), automatic HEAD when
enabled, and OPTIONS when enabled. Function require_GET accepts GET only.
The framework sitemap has no view method restriction; CSRF still applies
to unsafe requests. Public means no route-registry role check; it does not
bypass CSRF, form validation or state rules. Public entries have no mapped
permission action. Login redirects already signed-in users; language
switching changes only the caller's preference.

GLOBAL means a role grant across branches; ASSIGNED means current assigned
branches only; OWN means the caller's account. Object lookups still apply
scope. Anonymous private requests redirect to login (302); disallowed roles
and CSRF failures get 403; missing/out-of-scope objects get 404. Pages and
downloads normally return 200, successful forms normally redirect (302),
invalid forms can return 200 or 400, state conflicts 409, limits 429 and
unsupported restricted methods 405. These are shared conventions, not a
promise of every status for every route. [Health OpenAPI](openapi.yaml)
describes the only machine endpoint. [Exports](exports.md) describes files.

| Path / parameters | Name | HTTP methods | Permission action | Roles and scope | Public |
| --- | --- | --- | --- | --- | --- |
| `/en/` | `home` | GET | — | Anonymous and all staff roles (public route) | Yes |
| `/en/about/` | `public-about` | GET | — | Anonymous and all staff roles (public route) | Yes |
| `/en/accounts/change-password/` | `account-change-password` | GET, POST, PUT, HEAD, OPTIONS | `account.change_password` | SUPER_ADMIN: OWN; FINANCE_REVIEWER: OWN; CONTENT_EDITOR: OWN; BRANCH_LEAD: OWN; HR_LEAD: OWN | No |
| `/en/accounts/login/` | `account-login` | GET, POST, PUT, HEAD, OPTIONS | — | Anonymous and all staff roles (public route) | Yes |
| `/en/accounts/logout/` | `account-logout` | POST | `account.logout` | SUPER_ADMIN: GLOBAL; FINANCE_REVIEWER: GLOBAL; CONTENT_EDITOR: GLOBAL; BRANCH_LEAD: GLOBAL; HR_LEAD: GLOBAL | No |
| `/en/app/applications/` | `application-list` | GET, HEAD, OPTIONS | `application.list` | SUPER_ADMIN: GLOBAL; HR_LEAD: ASSIGNED | No |
| `/en/app/applications/<int:pk>/` | `application-detail` | GET, HEAD, OPTIONS | `application.view` | SUPER_ADMIN: GLOBAL; HR_LEAD: ASSIGNED | No |
| `/en/app/applications/<int:pk>/accept/` | `application-accept` | POST | `application.accept` | HR_LEAD: ASSIGNED | No |
| `/en/app/applications/<int:pk>/decline/` | `application-decline` | POST | `application.decline` | HR_LEAD: ASSIGNED | No |
| `/en/app/applications/<int:pk>/reassign/` | `application-reassign` | POST | `application.reassign_branch` | SUPER_ADMIN: GLOBAL; HR_LEAD: ASSIGNED | No |
| `/en/app/audit/` | `audit-list` | GET, HEAD, OPTIONS | `audit.list` | SUPER_ADMIN: GLOBAL | No |
| `/en/app/audit/<int:pk>/` | `audit-detail` | GET, HEAD, OPTIONS | `audit.view` | SUPER_ADMIN: GLOBAL | No |
| `/en/app/audit/verify/` | `audit-verify` | POST | `audit.verify_chain` | SUPER_ADMIN: GLOBAL | No |
| `/en/app/branches/` | `branch-list` | GET, HEAD, OPTIONS | `branch.list` | SUPER_ADMIN: GLOBAL; FINANCE_REVIEWER: GLOBAL; BRANCH_LEAD: ASSIGNED; HR_LEAD: ASSIGNED | No |
| `/en/app/branches/<int:branch_pk>/collections/new/` | `collection-create` | GET, POST, PUT, HEAD, OPTIONS | `collection.create` | BRANCH_LEAD: ASSIGNED | No |
| `/en/app/branches/<int:branch_pk>/teams/new/` | `team-create` | GET, POST, PUT, HEAD, OPTIONS | `team.manage` | SUPER_ADMIN: GLOBAL; HR_LEAD: ASSIGNED | No |
| `/en/app/branches/<int:branch_pk>/transfers/new/` | `transfer-create` | GET, POST, PUT, HEAD, OPTIONS | `transfer.create` | BRANCH_LEAD: ASSIGNED | No |
| `/en/app/branches/<int:pk>/` | `branch-detail` | GET, HEAD, OPTIONS | `branch.view` | SUPER_ADMIN: GLOBAL; FINANCE_REVIEWER: GLOBAL; BRANCH_LEAD: ASSIGNED; HR_LEAD: ASSIGNED | No |
| `/en/app/branches/<int:pk>/edit/` | `branch-edit` | GET, POST, PUT, HEAD, OPTIONS | `branch.update` | SUPER_ADMIN: GLOBAL | No |
| `/en/app/branches/create/` | `branch-create` | GET, POST, PUT, HEAD, OPTIONS | `branch.create` | SUPER_ADMIN: GLOBAL | No |
| `/en/app/cities/` | `city-list` | GET, HEAD, OPTIONS | `city.manage` | SUPER_ADMIN: GLOBAL | No |
| `/en/app/cities/<int:pk>/edit/` | `city-edit` | GET, POST, PUT, HEAD, OPTIONS | `city.manage` | SUPER_ADMIN: GLOBAL | No |
| `/en/app/cities/create/` | `city-create` | GET, POST, PUT, HEAD, OPTIONS | `city.manage` | SUPER_ADMIN: GLOBAL | No |
| `/en/app/collections/` | `collection-list` | GET, HEAD, OPTIONS | `collection.list` | SUPER_ADMIN: GLOBAL; FINANCE_REVIEWER: GLOBAL; BRANCH_LEAD: ASSIGNED | No |
| `/en/app/collections/<int:pk>/` | `collection-detail` | GET, HEAD, OPTIONS | `collection.view` | SUPER_ADMIN: GLOBAL; FINANCE_REVIEWER: GLOBAL; BRANCH_LEAD: ASSIGNED | No |
| `/en/app/collections/<int:pk>/edit/` | `collection-edit` | GET, POST, PUT, HEAD, OPTIONS | `collection.update` | BRANCH_LEAD: ASSIGNED | No |
| `/en/app/collections/<int:pk>/void/` | `collection-void` | GET, POST, PUT, HEAD, OPTIONS | `collection.void` | BRANCH_LEAD: ASSIGNED | No |
| `/en/app/content/` | `content-list` | GET, HEAD, OPTIONS | `content.list` | SUPER_ADMIN: GLOBAL; CONTENT_EDITOR: GLOBAL | No |
| `/en/app/content/<int:pk>/archive/` | `content-archive` | GET, POST, HEAD, OPTIONS | `content.archive` | SUPER_ADMIN: GLOBAL; CONTENT_EDITOR: GLOBAL | No |
| `/en/app/content/<int:pk>/edit/` | `content-edit` | GET, POST, PUT, HEAD, OPTIONS | `content.update` | SUPER_ADMIN: GLOBAL; CONTENT_EDITOR: GLOBAL | No |
| `/en/app/content/<int:pk>/preview/` | `content-preview` | GET, HEAD, OPTIONS | `content.view` | SUPER_ADMIN: GLOBAL; CONTENT_EDITOR: GLOBAL | No |
| `/en/app/content/<int:pk>/publish/` | `content-publish` | GET, POST, HEAD, OPTIONS | `content.publish` | SUPER_ADMIN: GLOBAL; CONTENT_EDITOR: GLOBAL | No |
| `/en/app/content/<int:pk>/restore/` | `content-restore` | GET, POST, HEAD, OPTIONS | `content.restore` | SUPER_ADMIN: GLOBAL; CONTENT_EDITOR: GLOBAL | No |
| `/en/app/content/<int:pk>/unpublish/` | `content-unpublish` | GET, POST, HEAD, OPTIONS | `content.unpublish` | SUPER_ADMIN: GLOBAL; CONTENT_EDITOR: GLOBAL | No |
| `/en/app/content/create/` | `content-create` | GET, POST, PUT, HEAD, OPTIONS | `content.create` | SUPER_ADMIN: GLOBAL; CONTENT_EDITOR: GLOBAL | No |
| `/en/app/dashboard/` | `dashboard-head-office` | GET, HEAD, OPTIONS | `dashboard.head_office` | SUPER_ADMIN: GLOBAL; FINANCE_REVIEWER: GLOBAL | No |
| `/en/app/hr/` | `dashboard-hr` | GET, HEAD, OPTIONS | `dashboard.hr` | HR_LEAD: ASSIGNED | No |
| `/en/app/members/` | `member-list` | GET, HEAD, OPTIONS | `member.list` | SUPER_ADMIN: GLOBAL; BRANCH_LEAD: ASSIGNED; HR_LEAD: ASSIGNED | No |
| `/en/app/members/<int:pk>/` | `member-detail` | GET, HEAD, OPTIONS | `member.view` | SUPER_ADMIN: GLOBAL; BRANCH_LEAD: ASSIGNED; HR_LEAD: ASSIGNED | No |
| `/en/app/members/<int:pk>/deactivate/` | `member-deactivate` | POST | `member.update` | SUPER_ADMIN: GLOBAL; HR_LEAD: ASSIGNED | No |
| `/en/app/members/<int:pk>/edit/` | `member-edit` | GET, POST, PUT, HEAD, OPTIONS | `member.update` | SUPER_ADMIN: GLOBAL; HR_LEAD: ASSIGNED | No |
| `/en/app/members/<int:pk>/mark-left/` | `member-mark-left` | POST | `member.update` | SUPER_ADMIN: GLOBAL; HR_LEAD: ASSIGNED | No |
| `/en/app/members/<int:pk>/reactivate/` | `member-reactivate` | POST | `member.update` | SUPER_ADMIN: GLOBAL; HR_LEAD: ASSIGNED | No |
| `/en/app/members/<int:pk>/reinstate/` | `member-reinstate` | POST | `member.reinstate` | SUPER_ADMIN: GLOBAL | No |
| `/en/app/my-branch/` | `dashboard-branch` | GET, HEAD, OPTIONS | `dashboard.branch` | BRANCH_LEAD: ASSIGNED | No |
| `/en/app/reports/` | `report-list` | GET, HEAD, OPTIONS | `report.list` | SUPER_ADMIN: GLOBAL; FINANCE_REVIEWER: GLOBAL; BRANCH_LEAD: ASSIGNED | No |
| `/en/app/reports/<int:pk>/` | `report-detail` | GET, HEAD, OPTIONS | `report.view` | SUPER_ADMIN: GLOBAL; FINANCE_REVIEWER: GLOBAL; BRANCH_LEAD: ASSIGNED | No |
| `/en/app/reports/<int:pk>/approve/` | `report-approve` | POST | `report.approve` | FINANCE_REVIEWER: GLOBAL | No |
| `/en/app/reports/<int:pk>/narrative/` | `report-save` | POST | `report.edit_narrative` | BRANCH_LEAD: ASSIGNED | No |
| `/en/app/reports/<int:pk>/resubmit/` | `report-resubmit` | POST | `report.resubmit` | BRANCH_LEAD: ASSIGNED | No |
| `/en/app/reports/<int:pk>/return/` | `report-return` | POST | `report.return` | FINANCE_REVIEWER: GLOBAL | No |
| `/en/app/reports/<int:pk>/submit/` | `report-submit` | POST | `report.submit` | BRANCH_LEAD: ASSIGNED | No |
| `/en/app/reports/review/` | `report-review-queue` | GET, HEAD, OPTIONS | `report.approve` | FINANCE_REVIEWER: GLOBAL | No |
| `/en/app/settings/` | `settings-view` | GET | `settings.view` | SUPER_ADMIN: GLOBAL | No |
| `/en/app/settings/update/` | `settings-update` | POST | `settings.update` | SUPER_ADMIN: GLOBAL | No |
| `/en/app/teams/` | `team-list` | GET, HEAD, OPTIONS | `team.list` | SUPER_ADMIN: GLOBAL; BRANCH_LEAD: ASSIGNED; HR_LEAD: ASSIGNED | No |
| `/en/app/teams/<int:pk>/deactivate/` | `team-deactivate` | POST | `team.manage` | SUPER_ADMIN: GLOBAL; HR_LEAD: ASSIGNED | No |
| `/en/app/teams/<int:pk>/edit/` | `team-edit` | GET, POST, PUT, HEAD, OPTIONS | `team.manage` | SUPER_ADMIN: GLOBAL; HR_LEAD: ASSIGNED | No |
| `/en/app/transfers/` | `transfer-list` | GET, HEAD, OPTIONS | `transfer.list` | SUPER_ADMIN: GLOBAL; FINANCE_REVIEWER: GLOBAL; BRANCH_LEAD: ASSIGNED | No |
| `/en/app/transfers/<int:pk>/` | `transfer-detail` | GET, HEAD, OPTIONS | `transfer.view` | SUPER_ADMIN: GLOBAL; FINANCE_REVIEWER: GLOBAL; BRANCH_LEAD: ASSIGNED | No |
| `/en/app/transfers/prepare/` | `transfer-prepare` | GET | `transfer.create` | BRANCH_LEAD: ASSIGNED | No |
| `/en/app/users/` | `user-list` | GET, HEAD, OPTIONS | `user.list` | SUPER_ADMIN: GLOBAL | No |
| `/en/app/users/<int:pk>/` | `user-detail` | GET, HEAD, OPTIONS | `user.view` | SUPER_ADMIN: GLOBAL | No |
| `/en/app/users/<int:pk>/assignments/` | `user-assign-branch` | POST | `assignment.manage` | SUPER_ADMIN: GLOBAL | No |
| `/en/app/users/<int:pk>/assignments/<int:branch_id>/remove/` | `user-remove-branch` | POST | `assignment.manage` | SUPER_ADMIN: GLOBAL | No |
| `/en/app/users/<int:pk>/deactivate/` | `user-deactivate` | POST | `user.update` | SUPER_ADMIN: GLOBAL | No |
| `/en/app/users/<int:pk>/edit/` | `user-edit` | GET, POST, PUT, HEAD, OPTIONS | `user.update` | SUPER_ADMIN: GLOBAL | No |
| `/en/app/users/<int:pk>/reactivate/` | `user-reactivate` | POST | `user.update` | SUPER_ADMIN: GLOBAL | No |
| `/en/app/users/<int:pk>/reset-password/` | `user-reset-password` | POST | `user.reset_password` | SUPER_ADMIN: GLOBAL | No |
| `/en/app/users/create/` | `user-create` | GET, POST, PUT, HEAD, OPTIONS | `user.create` | SUPER_ADMIN: GLOBAL | No |
| `/en/app/volunteer-roles/` | `volunteer-role-list` | GET, HEAD, OPTIONS | `volunteer_role.manage` | SUPER_ADMIN: GLOBAL | No |
| `/en/app/volunteer-roles/<int:pk>/deactivate/` | `volunteer-role-deactivate` | POST | `volunteer_role.manage` | SUPER_ADMIN: GLOBAL | No |
| `/en/app/volunteer-roles/<int:pk>/edit/` | `volunteer-role-edit` | GET, POST, PUT, HEAD, OPTIONS | `volunteer_role.manage` | SUPER_ADMIN: GLOBAL | No |
| `/en/app/volunteer-roles/new/` | `volunteer-role-create` | GET, POST, PUT, HEAD, OPTIONS | `volunteer_role.manage` | SUPER_ADMIN: GLOBAL | No |
| `/en/branches/` | `public-branches` | GET | — | Anonymous and all staff roles (public route) | Yes |
| `/en/branches/<int:pk>/<str:action>/` | `branch-transition` | POST | `branch.transition` | SUPER_ADMIN: GLOBAL | No |
| `/en/branches/<str:code>/` | `public-branch-detail` | GET | — | Anonymous and all staff roles (public route) | Yes |
| `/en/contact/` | `public-contact` | GET | — | Anonymous and all staff roles (public route) | Yes |
| `/en/events/` | `public-events` | GET | — | Anonymous and all staff roles (public route) | Yes |
| `/en/events/<slug:slug>/` | `public-event-detail` | GET | — | Anonymous and all staff roles (public route) | Yes |
| `/en/exports/audit.csv` | `export-audit-csv` | GET | `audit.export_csv` | SUPER_ADMIN: GLOBAL | No |
| `/en/exports/collections.csv` | `export-collections-csv` | GET | `collection.export_csv` | SUPER_ADMIN: GLOBAL; FINANCE_REVIEWER: GLOBAL; BRANCH_LEAD: ASSIGNED | No |
| `/en/exports/members.csv` | `export-members-csv` | GET | `member.export_csv` | SUPER_ADMIN: GLOBAL; HR_LEAD: ASSIGNED | No |
| `/en/exports/reports.csv` | `export-reports-csv` | GET | `report.export_csv` | SUPER_ADMIN: GLOBAL; FINANCE_REVIEWER: GLOBAL; BRANCH_LEAD: ASSIGNED | No |
| `/en/exports/reports/<int:pk>.pdf` | `export-report-pdf` | GET | `report.export_pdf` | SUPER_ADMIN: GLOBAL; FINANCE_REVIEWER: GLOBAL; BRANCH_LEAD: ASSIGNED | No |
| `/en/exports/summary.csv` | `export-summary-csv` | GET | `summary.export_csv` | SUPER_ADMIN: GLOBAL; FINANCE_REVIEWER: GLOBAL | No |
| `/en/exports/summary.pdf` | `export-summary-pdf` | GET | `summary.export_pdf` | SUPER_ADMIN: GLOBAL; FINANCE_REVIEWER: GLOBAL | No |
| `/en/exports/unsent.csv` | `export-unsent-csv` | GET | `unsent.export_csv` | SUPER_ADMIN: GLOBAL; FINANCE_REVIEWER: GLOBAL; BRANCH_LEAD: ASSIGNED | No |
| `/en/get-involved/` | `volunteer-apply` | GET, POST | — | Anonymous and all staff roles (public route) | Yes |
| `/en/get-involved/thanks/` | `volunteer-thanks` | GET | — | Anonymous and all staff roles (public route) | Yes |
| `/en/privacy/` | `public-privacy` | GET | — | Anonymous and all staff roles (public route) | Yes |
| `/en/programs/` | `public-programs` | GET | — | Anonymous and all staff roles (public route) | Yes |
| `/en/programs/<slug:slug>/` | `public-program-detail` | GET | — | Anonymous and all staff roles (public route) | Yes |
| `/health` | `health` | GET | — | Anonymous and all staff roles (public route) | Yes |
| `/i18n/set-language/` | `set_language` | POST | — | Anonymous and all staff roles (public route) | Yes |
| `/robots.txt` | `robots` | GET | — | Anonymous and all staff roles (public route) | Yes |
| `/sitemap.xml` | `sitemap` | Any (no view method restriction) | — | Anonymous and all staff roles (public route) | Yes |
| `/ur/` | `home` | GET | — | Anonymous and all staff roles (public route) | Yes |
| `/ur/about/` | `public-about` | GET | — | Anonymous and all staff roles (public route) | Yes |
| `/ur/accounts/change-password/` | `account-change-password` | GET, POST, PUT, HEAD, OPTIONS | `account.change_password` | SUPER_ADMIN: OWN; FINANCE_REVIEWER: OWN; CONTENT_EDITOR: OWN; BRANCH_LEAD: OWN; HR_LEAD: OWN | No |
| `/ur/accounts/login/` | `account-login` | GET, POST, PUT, HEAD, OPTIONS | — | Anonymous and all staff roles (public route) | Yes |
| `/ur/accounts/logout/` | `account-logout` | POST | `account.logout` | SUPER_ADMIN: GLOBAL; FINANCE_REVIEWER: GLOBAL; CONTENT_EDITOR: GLOBAL; BRANCH_LEAD: GLOBAL; HR_LEAD: GLOBAL | No |
| `/ur/app/applications/` | `application-list` | GET, HEAD, OPTIONS | `application.list` | SUPER_ADMIN: GLOBAL; HR_LEAD: ASSIGNED | No |
| `/ur/app/applications/<int:pk>/` | `application-detail` | GET, HEAD, OPTIONS | `application.view` | SUPER_ADMIN: GLOBAL; HR_LEAD: ASSIGNED | No |
| `/ur/app/applications/<int:pk>/accept/` | `application-accept` | POST | `application.accept` | HR_LEAD: ASSIGNED | No |
| `/ur/app/applications/<int:pk>/decline/` | `application-decline` | POST | `application.decline` | HR_LEAD: ASSIGNED | No |
| `/ur/app/applications/<int:pk>/reassign/` | `application-reassign` | POST | `application.reassign_branch` | SUPER_ADMIN: GLOBAL; HR_LEAD: ASSIGNED | No |
| `/ur/app/audit/` | `audit-list` | GET, HEAD, OPTIONS | `audit.list` | SUPER_ADMIN: GLOBAL | No |
| `/ur/app/audit/<int:pk>/` | `audit-detail` | GET, HEAD, OPTIONS | `audit.view` | SUPER_ADMIN: GLOBAL | No |
| `/ur/app/audit/verify/` | `audit-verify` | POST | `audit.verify_chain` | SUPER_ADMIN: GLOBAL | No |
| `/ur/app/branches/` | `branch-list` | GET, HEAD, OPTIONS | `branch.list` | SUPER_ADMIN: GLOBAL; FINANCE_REVIEWER: GLOBAL; BRANCH_LEAD: ASSIGNED; HR_LEAD: ASSIGNED | No |
| `/ur/app/branches/<int:branch_pk>/collections/new/` | `collection-create` | GET, POST, PUT, HEAD, OPTIONS | `collection.create` | BRANCH_LEAD: ASSIGNED | No |
| `/ur/app/branches/<int:branch_pk>/teams/new/` | `team-create` | GET, POST, PUT, HEAD, OPTIONS | `team.manage` | SUPER_ADMIN: GLOBAL; HR_LEAD: ASSIGNED | No |
| `/ur/app/branches/<int:branch_pk>/transfers/new/` | `transfer-create` | GET, POST, PUT, HEAD, OPTIONS | `transfer.create` | BRANCH_LEAD: ASSIGNED | No |
| `/ur/app/branches/<int:pk>/` | `branch-detail` | GET, HEAD, OPTIONS | `branch.view` | SUPER_ADMIN: GLOBAL; FINANCE_REVIEWER: GLOBAL; BRANCH_LEAD: ASSIGNED; HR_LEAD: ASSIGNED | No |
| `/ur/app/branches/<int:pk>/edit/` | `branch-edit` | GET, POST, PUT, HEAD, OPTIONS | `branch.update` | SUPER_ADMIN: GLOBAL | No |
| `/ur/app/branches/create/` | `branch-create` | GET, POST, PUT, HEAD, OPTIONS | `branch.create` | SUPER_ADMIN: GLOBAL | No |
| `/ur/app/cities/` | `city-list` | GET, HEAD, OPTIONS | `city.manage` | SUPER_ADMIN: GLOBAL | No |
| `/ur/app/cities/<int:pk>/edit/` | `city-edit` | GET, POST, PUT, HEAD, OPTIONS | `city.manage` | SUPER_ADMIN: GLOBAL | No |
| `/ur/app/cities/create/` | `city-create` | GET, POST, PUT, HEAD, OPTIONS | `city.manage` | SUPER_ADMIN: GLOBAL | No |
| `/ur/app/collections/` | `collection-list` | GET, HEAD, OPTIONS | `collection.list` | SUPER_ADMIN: GLOBAL; FINANCE_REVIEWER: GLOBAL; BRANCH_LEAD: ASSIGNED | No |
| `/ur/app/collections/<int:pk>/` | `collection-detail` | GET, HEAD, OPTIONS | `collection.view` | SUPER_ADMIN: GLOBAL; FINANCE_REVIEWER: GLOBAL; BRANCH_LEAD: ASSIGNED | No |
| `/ur/app/collections/<int:pk>/edit/` | `collection-edit` | GET, POST, PUT, HEAD, OPTIONS | `collection.update` | BRANCH_LEAD: ASSIGNED | No |
| `/ur/app/collections/<int:pk>/void/` | `collection-void` | GET, POST, PUT, HEAD, OPTIONS | `collection.void` | BRANCH_LEAD: ASSIGNED | No |
| `/ur/app/content/` | `content-list` | GET, HEAD, OPTIONS | `content.list` | SUPER_ADMIN: GLOBAL; CONTENT_EDITOR: GLOBAL | No |
| `/ur/app/content/<int:pk>/archive/` | `content-archive` | GET, POST, HEAD, OPTIONS | `content.archive` | SUPER_ADMIN: GLOBAL; CONTENT_EDITOR: GLOBAL | No |
| `/ur/app/content/<int:pk>/edit/` | `content-edit` | GET, POST, PUT, HEAD, OPTIONS | `content.update` | SUPER_ADMIN: GLOBAL; CONTENT_EDITOR: GLOBAL | No |
| `/ur/app/content/<int:pk>/preview/` | `content-preview` | GET, HEAD, OPTIONS | `content.view` | SUPER_ADMIN: GLOBAL; CONTENT_EDITOR: GLOBAL | No |
| `/ur/app/content/<int:pk>/publish/` | `content-publish` | GET, POST, HEAD, OPTIONS | `content.publish` | SUPER_ADMIN: GLOBAL; CONTENT_EDITOR: GLOBAL | No |
| `/ur/app/content/<int:pk>/restore/` | `content-restore` | GET, POST, HEAD, OPTIONS | `content.restore` | SUPER_ADMIN: GLOBAL; CONTENT_EDITOR: GLOBAL | No |
| `/ur/app/content/<int:pk>/unpublish/` | `content-unpublish` | GET, POST, HEAD, OPTIONS | `content.unpublish` | SUPER_ADMIN: GLOBAL; CONTENT_EDITOR: GLOBAL | No |
| `/ur/app/content/create/` | `content-create` | GET, POST, PUT, HEAD, OPTIONS | `content.create` | SUPER_ADMIN: GLOBAL; CONTENT_EDITOR: GLOBAL | No |
| `/ur/app/dashboard/` | `dashboard-head-office` | GET, HEAD, OPTIONS | `dashboard.head_office` | SUPER_ADMIN: GLOBAL; FINANCE_REVIEWER: GLOBAL | No |
| `/ur/app/hr/` | `dashboard-hr` | GET, HEAD, OPTIONS | `dashboard.hr` | HR_LEAD: ASSIGNED | No |
| `/ur/app/members/` | `member-list` | GET, HEAD, OPTIONS | `member.list` | SUPER_ADMIN: GLOBAL; BRANCH_LEAD: ASSIGNED; HR_LEAD: ASSIGNED | No |
| `/ur/app/members/<int:pk>/` | `member-detail` | GET, HEAD, OPTIONS | `member.view` | SUPER_ADMIN: GLOBAL; BRANCH_LEAD: ASSIGNED; HR_LEAD: ASSIGNED | No |
| `/ur/app/members/<int:pk>/deactivate/` | `member-deactivate` | POST | `member.update` | SUPER_ADMIN: GLOBAL; HR_LEAD: ASSIGNED | No |
| `/ur/app/members/<int:pk>/edit/` | `member-edit` | GET, POST, PUT, HEAD, OPTIONS | `member.update` | SUPER_ADMIN: GLOBAL; HR_LEAD: ASSIGNED | No |
| `/ur/app/members/<int:pk>/mark-left/` | `member-mark-left` | POST | `member.update` | SUPER_ADMIN: GLOBAL; HR_LEAD: ASSIGNED | No |
| `/ur/app/members/<int:pk>/reactivate/` | `member-reactivate` | POST | `member.update` | SUPER_ADMIN: GLOBAL; HR_LEAD: ASSIGNED | No |
| `/ur/app/members/<int:pk>/reinstate/` | `member-reinstate` | POST | `member.reinstate` | SUPER_ADMIN: GLOBAL | No |
| `/ur/app/my-branch/` | `dashboard-branch` | GET, HEAD, OPTIONS | `dashboard.branch` | BRANCH_LEAD: ASSIGNED | No |
| `/ur/app/reports/` | `report-list` | GET, HEAD, OPTIONS | `report.list` | SUPER_ADMIN: GLOBAL; FINANCE_REVIEWER: GLOBAL; BRANCH_LEAD: ASSIGNED | No |
| `/ur/app/reports/<int:pk>/` | `report-detail` | GET, HEAD, OPTIONS | `report.view` | SUPER_ADMIN: GLOBAL; FINANCE_REVIEWER: GLOBAL; BRANCH_LEAD: ASSIGNED | No |
| `/ur/app/reports/<int:pk>/approve/` | `report-approve` | POST | `report.approve` | FINANCE_REVIEWER: GLOBAL | No |
| `/ur/app/reports/<int:pk>/narrative/` | `report-save` | POST | `report.edit_narrative` | BRANCH_LEAD: ASSIGNED | No |
| `/ur/app/reports/<int:pk>/resubmit/` | `report-resubmit` | POST | `report.resubmit` | BRANCH_LEAD: ASSIGNED | No |
| `/ur/app/reports/<int:pk>/return/` | `report-return` | POST | `report.return` | FINANCE_REVIEWER: GLOBAL | No |
| `/ur/app/reports/<int:pk>/submit/` | `report-submit` | POST | `report.submit` | BRANCH_LEAD: ASSIGNED | No |
| `/ur/app/reports/review/` | `report-review-queue` | GET, HEAD, OPTIONS | `report.approve` | FINANCE_REVIEWER: GLOBAL | No |
| `/ur/app/settings/` | `settings-view` | GET | `settings.view` | SUPER_ADMIN: GLOBAL | No |
| `/ur/app/settings/update/` | `settings-update` | POST | `settings.update` | SUPER_ADMIN: GLOBAL | No |
| `/ur/app/teams/` | `team-list` | GET, HEAD, OPTIONS | `team.list` | SUPER_ADMIN: GLOBAL; BRANCH_LEAD: ASSIGNED; HR_LEAD: ASSIGNED | No |
| `/ur/app/teams/<int:pk>/deactivate/` | `team-deactivate` | POST | `team.manage` | SUPER_ADMIN: GLOBAL; HR_LEAD: ASSIGNED | No |
| `/ur/app/teams/<int:pk>/edit/` | `team-edit` | GET, POST, PUT, HEAD, OPTIONS | `team.manage` | SUPER_ADMIN: GLOBAL; HR_LEAD: ASSIGNED | No |
| `/ur/app/transfers/` | `transfer-list` | GET, HEAD, OPTIONS | `transfer.list` | SUPER_ADMIN: GLOBAL; FINANCE_REVIEWER: GLOBAL; BRANCH_LEAD: ASSIGNED | No |
| `/ur/app/transfers/<int:pk>/` | `transfer-detail` | GET, HEAD, OPTIONS | `transfer.view` | SUPER_ADMIN: GLOBAL; FINANCE_REVIEWER: GLOBAL; BRANCH_LEAD: ASSIGNED | No |
| `/ur/app/transfers/prepare/` | `transfer-prepare` | GET | `transfer.create` | BRANCH_LEAD: ASSIGNED | No |
| `/ur/app/users/` | `user-list` | GET, HEAD, OPTIONS | `user.list` | SUPER_ADMIN: GLOBAL | No |
| `/ur/app/users/<int:pk>/` | `user-detail` | GET, HEAD, OPTIONS | `user.view` | SUPER_ADMIN: GLOBAL | No |
| `/ur/app/users/<int:pk>/assignments/` | `user-assign-branch` | POST | `assignment.manage` | SUPER_ADMIN: GLOBAL | No |
| `/ur/app/users/<int:pk>/assignments/<int:branch_id>/remove/` | `user-remove-branch` | POST | `assignment.manage` | SUPER_ADMIN: GLOBAL | No |
| `/ur/app/users/<int:pk>/deactivate/` | `user-deactivate` | POST | `user.update` | SUPER_ADMIN: GLOBAL | No |
| `/ur/app/users/<int:pk>/edit/` | `user-edit` | GET, POST, PUT, HEAD, OPTIONS | `user.update` | SUPER_ADMIN: GLOBAL | No |
| `/ur/app/users/<int:pk>/reactivate/` | `user-reactivate` | POST | `user.update` | SUPER_ADMIN: GLOBAL | No |
| `/ur/app/users/<int:pk>/reset-password/` | `user-reset-password` | POST | `user.reset_password` | SUPER_ADMIN: GLOBAL | No |
| `/ur/app/users/create/` | `user-create` | GET, POST, PUT, HEAD, OPTIONS | `user.create` | SUPER_ADMIN: GLOBAL | No |
| `/ur/app/volunteer-roles/` | `volunteer-role-list` | GET, HEAD, OPTIONS | `volunteer_role.manage` | SUPER_ADMIN: GLOBAL | No |
| `/ur/app/volunteer-roles/<int:pk>/deactivate/` | `volunteer-role-deactivate` | POST | `volunteer_role.manage` | SUPER_ADMIN: GLOBAL | No |
| `/ur/app/volunteer-roles/<int:pk>/edit/` | `volunteer-role-edit` | GET, POST, PUT, HEAD, OPTIONS | `volunteer_role.manage` | SUPER_ADMIN: GLOBAL | No |
| `/ur/app/volunteer-roles/new/` | `volunteer-role-create` | GET, POST, PUT, HEAD, OPTIONS | `volunteer_role.manage` | SUPER_ADMIN: GLOBAL | No |
| `/ur/branches/` | `public-branches` | GET | — | Anonymous and all staff roles (public route) | Yes |
| `/ur/branches/<int:pk>/<str:action>/` | `branch-transition` | POST | `branch.transition` | SUPER_ADMIN: GLOBAL | No |
| `/ur/branches/<str:code>/` | `public-branch-detail` | GET | — | Anonymous and all staff roles (public route) | Yes |
| `/ur/contact/` | `public-contact` | GET | — | Anonymous and all staff roles (public route) | Yes |
| `/ur/events/` | `public-events` | GET | — | Anonymous and all staff roles (public route) | Yes |
| `/ur/events/<slug:slug>/` | `public-event-detail` | GET | — | Anonymous and all staff roles (public route) | Yes |
| `/ur/exports/audit.csv` | `export-audit-csv` | GET | `audit.export_csv` | SUPER_ADMIN: GLOBAL | No |
| `/ur/exports/collections.csv` | `export-collections-csv` | GET | `collection.export_csv` | SUPER_ADMIN: GLOBAL; FINANCE_REVIEWER: GLOBAL; BRANCH_LEAD: ASSIGNED | No |
| `/ur/exports/members.csv` | `export-members-csv` | GET | `member.export_csv` | SUPER_ADMIN: GLOBAL; HR_LEAD: ASSIGNED | No |
| `/ur/exports/reports.csv` | `export-reports-csv` | GET | `report.export_csv` | SUPER_ADMIN: GLOBAL; FINANCE_REVIEWER: GLOBAL; BRANCH_LEAD: ASSIGNED | No |
| `/ur/exports/reports/<int:pk>.pdf` | `export-report-pdf` | GET | `report.export_pdf` | SUPER_ADMIN: GLOBAL; FINANCE_REVIEWER: GLOBAL; BRANCH_LEAD: ASSIGNED | No |
| `/ur/exports/summary.csv` | `export-summary-csv` | GET | `summary.export_csv` | SUPER_ADMIN: GLOBAL; FINANCE_REVIEWER: GLOBAL | No |
| `/ur/exports/summary.pdf` | `export-summary-pdf` | GET | `summary.export_pdf` | SUPER_ADMIN: GLOBAL; FINANCE_REVIEWER: GLOBAL | No |
| `/ur/exports/unsent.csv` | `export-unsent-csv` | GET | `unsent.export_csv` | SUPER_ADMIN: GLOBAL; FINANCE_REVIEWER: GLOBAL; BRANCH_LEAD: ASSIGNED | No |
| `/ur/get-involved/` | `volunteer-apply` | GET, POST | — | Anonymous and all staff roles (public route) | Yes |
| `/ur/get-involved/thanks/` | `volunteer-thanks` | GET | — | Anonymous and all staff roles (public route) | Yes |
| `/ur/privacy/` | `public-privacy` | GET | — | Anonymous and all staff roles (public route) | Yes |
| `/ur/programs/` | `public-programs` | GET | — | Anonymous and all staff roles (public route) | Yes |
| `/ur/programs/<slug:slug>/` | `public-program-detail` | GET | — | Anonymous and all staff roles (public route) | Yes |
