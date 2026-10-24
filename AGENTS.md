# AGENTS.md — rules for AI coding agents in this repository

This repository is a solo entry for the ShipLens 1.0 build challenge. The human owner must be able to **explain every line** to judges. Follow these rules on every task.

## 1. Source of truth
- The plan lives in `docs/planning/`. Read the files named in your task before writing code. If code and plan disagree, follow the plan and mention the conflict in your summary.
- Key files: `05-rbac-matrix.md` (permissions), `06-state-machines.md`, `07-business-rules.md` (BR-xxx), `08-data-model.md`, `09-dashboard-and-seed-data.md`, `10-architecture-and-stack.md`, `11-security.md`, `17-test-strategy.md`.
- Do not invent features that aren't in the plan. If something is ambiguous, pick the simplest option that fits the plan and list it under "Assumptions" in your summary.

## 2. Git — strictly forbidden
- **Do not run `git commit`, `git push`, `git merge`, `git rebase`, `git tag`, or create branches or pull requests.** The owner does all git operations.
- Do not add AI attribution or co-author lines anywhere.
- Work in **steps**. At the end of each step, stop and print the step summary (section 7) so the owner can review and commit. Don't start the next step until asked.

## 3. Stack (fixed — do not substitute)
Python 3.12 · Django 5.2 LTS · PostgreSQL 16 · psycopg 3 · server-rendered Django templates (no SPA, no React, no HTMX, no Tailwind/Bootstrap) · hand-written CSS using **logical properties only** · gunicorn · WhiteNoise · django-axes · django-ratelimit · django-csp · argon2-cffi · dj-database-url · markdown + nh3 · WeasyPrint · openpyxl · Chart.js 4 (vendored file, dashboard only) · pytest, pytest-django, pytest-cov, factory-boy, time-machine, polib, pytest-playwright · ruff.
- Pin exact versions in `requirements.in` → `requirements.txt` (pip-tools, `--generate-hashes`). Use only versions that really exist; prefer the latest stable patch release.
- Don't add any other dependency without saying why in the step summary.

## 4. Code style (explainability first)
- Boring, explicit code. Prefer plain functions and Django class-based views without deep mixin chains. No metaprogramming, no clever one-liners, no premature abstraction.
- Layering: `urls → views (thin: permission + form + call service) → services (business rules, transaction.atomic, audit.record) → models (fields + DB constraints)`. Read-only queries go in `selectors.py` / `kpis.py`.
- Views never call `.save()` on domain models or use `Model.objects.get()` directly. They go through services, and object lookups use scoped querysets (`scope_queryset`).
- Every state change happens in a service, inside `transaction.atomic()`, using `select_for_update()` where races are possible, and calls `audit.record(...)` in the same transaction.
- Time: never call `timezone.now()` / `date.today()` in domain code. Use `apps.core.clock.now()` / `clock.today()` (Asia/Karachi business dates).
- Business constants (lock days, rate limits, min age, …) come from `apps.core.rules.get(name)`, never inline literals.
- Money is `Decimal` / `models.DecimalField(max_digits=12, decimal_places=2)`. Never float.
- Every user-facing string is wrapped for translation (`{% translate %}`, `gettext_lazy`).
- Short docstrings on services and non-obvious functions, written as a person would write them. Reference rule IDs (`# BR-064`) where a rule is enforced.
- Format and lint with ruff; code must pass `ruff check` and `ruff format --check`.

## 5. Security non-negotiables
No `csrf_exempt`. No `|safe` except the one sanitised-CMS template filter. No raw SQL outside migrations. No secrets in code (read from env). `DEBUG=False` in prod settings. Forms list `fields` explicitly; never bind `status`, `branch`, codes or `created_by` from user input. No hard deletes of domain data.

## 6. Tests
- Write tests **in the same step** as the code. Use pytest + pytest-django against **PostgreSQL** (never SQLite).
- Name tests after the IDs in `docs/planning/17-test-strategy.md` where one exists (e.g. `test_t_col_lock_at_boundary`).
- Time-based tests use the clock fixture. Concurrency tests use `TransactionTestCase` / `transaction=True` with threads.
- Before ending a step, run `ruff check .`, `ruff format --check .` and `pytest` and paste the result counts and the coverage total.

## 7. Step summary format (print at the end of every step)
```
STEP <n> DONE — <title>
Files changed: <list>
What it does: <3–6 plain-English bullets>
How to explain it to a judge: <2–4 bullets: the key idea and why>
Tests: <passed/failed counts, coverage %>
Assumptions: <list or "none">
Suggested commit message: <conventional commit from the task>
```
