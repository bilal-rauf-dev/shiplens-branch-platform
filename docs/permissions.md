# Permissions

Generated — do not edit by hand. Run `python manage.py export_permissions`.
Source: `apps/accounts/permissions.py`; plan: `docs/planning/05-rbac-matrix.md` §3.

Legend: GLOBAL = allowed globally; ASSIGNED = assigned branches only;
own = caller's own account; — = denied. Unknown actions are denied.
SA = Super Admin; FR = Finance Reviewer; CE = Content Editor;
BL = Branch Lead; HR = HR Lead; ANON = anonymous.

## 3.1 Public & account

| Action | ANON | SA | FR | CE | BL | HR |
|---|---|---|---|---|---|---|
| `public.view` | GLOBAL | GLOBAL | GLOBAL | GLOBAL | GLOBAL | GLOBAL |
| `application.submit` | GLOBAL | GLOBAL | GLOBAL | GLOBAL | GLOBAL | GLOBAL |
| `account.login` | GLOBAL | — | — | — | — | — |
| `account.logout` | — | GLOBAL | GLOBAL | GLOBAL | GLOBAL | GLOBAL |
| `account.change_password` | — | own | own | own | own | own |
| `account.set_language` | GLOBAL | own | own | own | own | own |

## 3.2 Administration

| Action | ANON | SA | FR | CE | BL | HR |
|---|---|---|---|---|---|---|
| `user.list` | — | GLOBAL | — | — | — | — |
| `user.view` | — | GLOBAL | — | — | — | — |
| `user.create` | — | GLOBAL | — | — | — | — |
| `user.update` | — | GLOBAL | — | — | — | — |
| `user.reset_password` | — | GLOBAL | — | — | — | — |
| `assignment.manage` | — | GLOBAL | — | — | — | — |
| `city.manage` | — | GLOBAL | — | — | — | — |
| `volunteer_role.manage` | — | GLOBAL | — | — | — | — |
| `settings.view` | — | GLOBAL | — | — | — | — |
| `settings.update` | — | GLOBAL | — | — | — | — |

## 3.3 Branches

| Action | ANON | SA | FR | CE | BL | HR |
|---|---|---|---|---|---|---|
| `branch.list` | — | GLOBAL | GLOBAL | — | ASSIGNED | ASSIGNED |
| `branch.view` | — | GLOBAL | GLOBAL | — | ASSIGNED | ASSIGNED |
| `branch.create` | — | GLOBAL | — | — | — | — |
| `branch.update` | — | GLOBAL | — | — | — | — |
| `branch.transition` | — | GLOBAL | — | — | — | — |

## 3.4 Applications & members

| Action | ANON | SA | FR | CE | BL | HR |
|---|---|---|---|---|---|---|
| `application.list` | — | GLOBAL | — | — | — | ASSIGNED |
| `application.view` | — | GLOBAL | — | — | — | ASSIGNED |
| `application.accept` | — | — | — | — | — | ASSIGNED |
| `application.decline` | — | — | — | — | — | ASSIGNED |
| `application.reassign_branch` | — | GLOBAL | — | — | — | ASSIGNED |
| `member.list` | — | GLOBAL | — | — | ASSIGNED | ASSIGNED |
| `member.view` | — | GLOBAL | — | — | ASSIGNED | ASSIGNED |
| `member.update` | — | GLOBAL | — | — | — | ASSIGNED |
| `member.reinstate` | — | GLOBAL | — | — | — | — |
| `team.list` | — | GLOBAL | — | — | ASSIGNED | ASSIGNED |
| `team.manage` | — | GLOBAL | — | — | — | ASSIGNED |
| `member.export_csv` | — | GLOBAL | — | — | — | ASSIGNED |

## 3.5 Collections & transfers

| Action | ANON | SA | FR | CE | BL | HR |
|---|---|---|---|---|---|---|
| `collection.list` | — | GLOBAL | GLOBAL | — | ASSIGNED | — |
| `collection.view` | — | GLOBAL | GLOBAL | — | ASSIGNED | — |
| `collection.create` | — | — | — | — | ASSIGNED | — |
| `collection.update` | — | — | — | — | ASSIGNED | — |
| `collection.void` | — | — | — | — | ASSIGNED | — |
| `collection.adjust` | — | — | — | — | ASSIGNED | — |
| `transfer.create` | — | — | — | — | ASSIGNED | — |
| `transfer.list` | — | GLOBAL | GLOBAL | — | ASSIGNED | — |
| `transfer.view` | — | GLOBAL | GLOBAL | — | ASSIGNED | — |
| `collection.export_csv` | — | GLOBAL | GLOBAL | — | ASSIGNED | — |

## 3.6 Weekly reports

| Action | ANON | SA | FR | CE | BL | HR |
|---|---|---|---|---|---|---|
| `report.list` | — | GLOBAL | GLOBAL | — | ASSIGNED | — |
| `report.view` | — | GLOBAL | GLOBAL | — | ASSIGNED | — |
| `report.edit_narrative` | — | — | — | — | ASSIGNED | — |
| `report.submit` | — | — | — | — | ASSIGNED | — |
| `report.resubmit` | — | — | — | — | ASSIGNED | — |
| `report.approve` | — | — | GLOBAL | — | — | — |
| `report.return` | — | — | GLOBAL | — | — | — |
| `report.export_pdf` | — | GLOBAL | GLOBAL | — | ASSIGNED | — |
| `report.export_csv` | — | GLOBAL | GLOBAL | — | ASSIGNED | — |

## 3.7 Dashboard, exports, audit

| Action | ANON | SA | FR | CE | BL | HR |
|---|---|---|---|---|---|---|
| `dashboard.head_office` | — | GLOBAL | GLOBAL | — | — | — |
| `dashboard.branch` | — | — | — | — | ASSIGNED | — |
| `dashboard.hr` | — | — | — | — | — | ASSIGNED |
| `summary.export_pdf` | — | GLOBAL | GLOBAL | — | — | — |
| `summary.export_csv` | — | GLOBAL | GLOBAL | — | — | — |
| `unsent.export_csv` | — | GLOBAL | GLOBAL | — | ASSIGNED | — |
| `audit.list` | — | GLOBAL | — | — | — | — |
| `audit.view` | — | GLOBAL | — | — | — | — |
| `audit.export_csv` | — | GLOBAL | — | — | — | — |
| `audit.verify_chain` | — | GLOBAL | — | — | — | — |
| `audit.entity_history` | — | GLOBAL | GLOBAL | GLOBAL | ASSIGNED | ASSIGNED |

## 3.8 Content manager

| Action | ANON | SA | FR | CE | BL | HR |
|---|---|---|---|---|---|---|
| `content.list` | — | GLOBAL | — | GLOBAL | — | — |
| `content.view` | — | GLOBAL | — | GLOBAL | — | — |
| `content.create` | — | GLOBAL | — | GLOBAL | — | — |
| `content.update` | — | GLOBAL | — | GLOBAL | — | — |
| `content.publish` | — | GLOBAL | — | GLOBAL | — | — |
| `content.unpublish` | — | GLOBAL | — | GLOBAL | — | — |
| `content.archive` | — | GLOBAL | — | GLOBAL | — | — |
| `content.restore` | — | GLOBAL | — | GLOBAL | — | — |

## 3.9 Ops

| Action | ANON | SA | FR | CE | BL | HR |
|---|---|---|---|---|---|---|
| `health` | GLOBAL | GLOBAL | GLOBAL | GLOBAL | GLOBAL | GLOBAL |
| `/admin/` | Disabled; no admin routes installed | | | | | |

## Scope rules and additional checks

- Only active authenticated users receive role permissions; there is no Super Admin bypass.
- Anonymous public access does not grant the same action to an authenticated role: login is anonymous only.
- `account.change_password` and authenticated `account.set_language` apply only to the caller. GLOBAL is the role grant; object/queryset checks enforce ownership.
- Branch queries filter `pk`; applications filter `preferred_branch_id`; members, teams, collections, transfers and reports filter `branch_id` by current assignments.
- Call `scope_queryset` before object lookup so out-of-scope objects return 404. `require` raises PermissionDenied at service boundaries.
- `audit.entity_history` receives the underlying entity (or its queryset), not audit rows. It requires permission to view that entity. FR is restricted to collections, transfers and reports; CE to content; BL/HR retain assigned-branch scope. Unknown entity types are denied.
- HR `application.reassign_branch` scopes the source application. The reassignment service must separately validate an open destination branch (destination need not be assigned).
- Assignments remain available for historical scope after branch closure; operational state restrictions belong in services.
- Last-active-Super-Admin, demo-account, DEMO_MODE and resource-state restrictions are additional service rules, not broader permission grants.
- `/health` is represented by the public `health` action and remains exempt from request authorization checks.
