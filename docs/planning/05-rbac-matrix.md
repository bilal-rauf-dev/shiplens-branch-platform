# 05 — Permission Model (RBAC) — documented permission table

> This file is written to final-documentation quality. At build time `docs/permissions.md` is **generated** from the code matrix (`apps/accounts/permissions.py`) by `manage.py export_permissions`; CI test `T-RBAC-DOC-SYNC` fails if the committed file differs from the generated one. So the doc can never drift from the code.

## 1. Principles

1. **Deny by default.** An action not listed for a role is forbidden. A route without a declared action is unreachable (`T-RBAC-ROUTES`).
2. **One role per user**, one matrix in code, enforced **server-side** on every request. UI hiding is cosmetic only.
3. **Two checks per request:** (a) *action check* — may this role perform `resource.action`? (b) *scope check* — is this object inside the user's scope? Objects outside scope return **404** (not 403) to avoid confirming existence.
4. **Segregation of duties:** the person who submits a report cannot approve it (different roles); Super Admin administers but does not approve reports or decide applications.
5. Every denial is logged (`permission.denied` audit event, rate-limited to avoid log flooding).

## 2. Roles and scope

| Code | Role | Scope | Typical count |
|---|---|---|---|
| `SUPER_ADMIN` | Super Admin | Global | 1–2 |
| `FINANCE_REVIEWER` | Finance Reviewer | Global (financial data) | 1–3 |
| `CONTENT_EDITOR` | Content Editor | CMS only | 1–3 |
| `BRANCH_LEAD` | Branch Lead | Assigned branches (`user_branch_assignments`) — normally one | 1 per branch |
| `HR_LEAD` | HR Lead | Assigned branches — one or many | 1 per 1–3 branches |
| `ANON` | Anonymous public | Public pages only | — |

Legend: **✓** allowed (global) · **S** allowed within assigned branches · **—** denied · **own** only own account.

## 3. Matrix

### 3.1 Public & account

| Action code | ANON | SA | FR | CE | BL | HR |
|---|---|---|---|---|---|---|
| `public.view` (7 pages, published content) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `application.submit` (public form) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `account.login` / `account.logout` | ✓ / — | — / ✓ | — / ✓ | — / ✓ | — / ✓ | — / ✓ |
| `account.change_password` | — | own | own | own | own | own |
| `account.set_language` | ✓ | own | own | own | own | own |

### 3.2 Administration

| Action code | ANON | SA | FR | CE | BL | HR |
|---|---|---|---|---|---|---|
| `user.list` / `user.view` | — | ✓ | — | — | — | — |
| `user.create` | — | ✓ | — | — | — | — |
| `user.update` (name, role, active) | — | ✓ (not self-demote last SA) | — | — | — | — |
| `user.reset_password` (issue temp password) | — | ✓ (not demo accounts) | — | — | — | — |
| `assignment.manage` (user↔branch) | — | ✓ | — | — | — | — |
| `city.manage` | — | ✓ | — | — | — | — |
| `volunteer_role.manage` | — | ✓ | — | — | — | — |
| `settings.view` / `settings.update` (lock days etc.) | — | ✓ | — | — | — | — |

### 3.3 Branches

| Action code | ANON | SA | FR | CE | BL | HR |
|---|---|---|---|---|---|---|
| `branch.list` / `branch.view` (internal detail) | — | ✓ | ✓ | — | S | S |
| `branch.create` | — | ✓ | — | — | — | — |
| `branch.update` (name, address, contact) | — | ✓ | — | — | — | — |
| `branch.transition` (activate/pause/resume/close) | — | ✓ | — | — | — | — |

### 3.4 Applications & members

| Action code | ANON | SA | FR | CE | BL | HR |
|---|---|---|---|---|---|---|
| `application.list` / `application.view` (PII) | — | ✓ | — | — | — | S |
| `application.accept` | — | — | — | — | — | S |
| `application.decline` | — | — | — | — | — | S |
| `application.reassign_branch` | — | ✓ | — | — | — | S (to any open branch) |
| `member.list` / `member.view` (PII) | — | ✓ | — | — | S (read) | S |
| `member.update` (team, role, status, contact) | — | ✓ | — | — | — | S |
| `member.reinstate` (Left → Active) | — | ✓ | — | — | — | — |
| `team.list` | — | ✓ | — | — | S | S |
| `team.manage` | — | ✓ | — | — | — | S |
| `member.export_csv` | — | ✓ | — | — | — | S |

### 3.5 Collections & transfers

| Action code | ANON | SA | FR | CE | BL | HR |
|---|---|---|---|---|---|---|
| `collection.list` / `collection.view` | — | ✓ | ✓ | — | S | — |
| `collection.create` | — | — | — | — | S | — |
| `collection.update` (open, unsent, week open) | — | — | — | — | S | — |
| `collection.void` (open, unsent, week open) | — | — | — | — | S | — |
| `collection.adjust` (Should: adjustment entry) | — | — | — | — | S | — |
| `transfer.create` (mark sent) | — | — | — | — | S | — |
| `transfer.list` / `transfer.view` | — | ✓ | ✓ | — | S | — |
| `collection.export_csv` | — | ✓ | ✓ | — | S | — |

### 3.6 Weekly reports

| Action code | ANON | SA | FR | CE | BL | HR |
|---|---|---|---|---|---|---|
| `report.list` / `report.view` | — | ✓ | ✓ | — | S | — |
| `report.edit_narrative` (Draft/Returned) | — | — | — | — | S | — |
| `report.submit` (Draft→Submitted) | — | — | — | — | S | — |
| `report.resubmit` (Returned→Resubmitted) | — | — | — | — | S | — |
| `report.approve` (→Approved→Locked) | — | — | ✓ | — | — | — |
| `report.return` (→Returned, comment) | — | — | ✓ | — | — | — |
| `report.export_pdf` / `report.export_csv` | — | ✓ | ✓ | — | S | — |

### 3.7 Dashboard, exports, audit

| Action code | ANON | SA | FR | CE | BL | HR |
|---|---|---|---|---|---|---|
| `dashboard.head_office` | — | ✓ | ✓ | — | — | — |
| `dashboard.branch` | — | — | — | — | S | — |
| `dashboard.hr` (applications pipeline counts) | — | — | — | — | — | S |
| `summary.export_pdf` / `summary.export_csv` | — | ✓ | ✓ | — | — | — |
| `unsent.export_csv` | — | ✓ | ✓ | — | S | — |
| `audit.list` / `audit.view` / `audit.export_csv` | — | ✓ | — | — | — | — |
| `audit.verify_chain` | — | ✓ | — | — | — | — |
| `audit.entity_history` (history panel on a record) | — | ✓ | ✓ (fin. records) | ✓ (content) | S | S |

### 3.8 Content manager

| Action code | ANON | SA | FR | CE | BL | HR |
|---|---|---|---|---|---|---|
| `content.list` / `content.view` (incl. drafts) | — | ✓ | — | ✓ | — | — |
| `content.create` / `content.update` | — | ✓ | — | ✓ | — | — |
| `content.publish` / `content.unpublish` | — | ✓ | — | ✓ | — | — |
| `content.archive` / `content.restore` | — | ✓ | — | ✓ | — | — |

> SA retains CMS rights as an operational fallback (one Content Editor on leave must not block the website). Remove if strict separation is preferred (Q-08).

### 3.9 Ops

| Action code | ANON | SA | FR | CE | BL | HR |
|---|---|---|---|---|---|---|
| `GET /health` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Django admin (`/admin/`) | disabled in production (`ENABLE_DJANGO_ADMIN=false`) | | | | | |

## 4. Row-level scope rules

| Resource | Scope predicate for BL/HR |
|---|---|
| Branch | `branch.id IN user.assigned_branch_ids` |
| Application | `application.preferred_branch_id IN assigned` |
| Member, Team | `branch_id IN assigned` |
| Collection, Transfer, Weekly report | `branch_id IN assigned` (BL only) |
| Audit entity history | user can `view` the entity |

Finance Reviewer: global for collections/transfers/reports/dashboard; **no access** to member/applicant PII rows.

## 5. Enforcement design (central, explainable)

```text
apps/accounts/permissions.py
  PERMISSIONS: dict[str, dict[Role, Scope]]   # "report.approve": {FINANCE_REVIEWER: GLOBAL}
  def can(user, action, obj=None) -> bool      # matrix + scope
  def scope_queryset(user, action, qs) -> qs   # filters by assigned branches

apps/core/views.py
  class PermissionRequiredMixin:  required_action = "report.approve"
       dispatch(): if not can(request.user, action): 403/redirect login
       get_queryset(): scope_queryset(...)   -> get_object_or_404 on scoped qs => 404 out of scope

apps/core/middleware.py
  RouteRegistryMiddleware: every resolved url_name must be in ROUTE_ACTIONS or PUBLIC_ROUTES -> else 404
```

- **Services re-check** the action (`service.approve_report(actor, report)` calls `require(actor, "report.approve", report)`) so business logic is safe even if called from a management command or a future API.
- State-dependent conditions (e.g. "collection is open") are **business rules**, not permissions; they return **409 Conflict** with a reason.

## 6. How it is tested (Gate 3)

| Test | What it proves |
|---|---|
| `T-RBAC-MATRIX` | Parametrised over **every action × every role (+ANON)** from `PERMISSIONS` itself plus a frozen copy `tests/rbac_expected.yaml` (so an accidental matrix edit fails review). For each cell, hits the route mapped to that action with a seeded in-scope object and asserts 2xx/3xx vs 403/302-to-login. |
| `T-RBAC-SCOPE-*` | BL of KHI requests LHE collection/report/member by id → 404; list endpoints never contain other-branch rows; exports contain only scoped rows. |
| `T-RBAC-ROUTES` | Walks Django URL resolver; every named route is in `ROUTE_ACTIONS` or `PUBLIC_ROUTES`; fails listing offenders. |
| `T-RBAC-SERVICE` | Calls services directly with wrong role → `PermissionDenied`. |
| `T-RBAC-DOC-SYNC` | Generated permission table == committed `docs/permissions.md`. |
| `T-AUD-DENIED` | Denials create `permission.denied` audit rows. |
