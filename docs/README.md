# Documentation index

Current implementation guides are listed first. Planning files retain historical
decisions and proposals; follow the implementation references and explicit gaps
in business-rules.md when checking delivered behavior.

## Guides and references

- [api.md](api.md) — Route reference.
- [architecture.md](architecture.md) — Architecture.
- [audit.md](audit.md) — Audit log.
- [branch-register.md](branch-register.md) — Branch register foundation.
- [business-rules.md](business-rules.md) — Implemented business rules.
- [ci.md](ci.md) — Continuous integration.
- [credits.md](credits.md) — Credits.
- [design-system.md](design-system.md) — ShipLens design system.
- [exports.md](exports.md) — CSV and PDF exports.
- [finance.md](finance.md) — Offline collections and transfers.
- [handover.md](handover.md) — Handover and operations.
- [i18n-glossary.md](i18n-glossary.md) — Urdu interface glossary.
- [openapi.yaml](openapi.yaml) — OpenAPI contract for the health endpoint only.
- [performance.md](performance.md) — Performance verification.
- [permissions.md](permissions.md) — Permissions.
- [public-website.md](public-website.md) — Public website and content workflow.
- [README.md](README.md) — Index of every file in this documentation pack.
- [security.md](security.md) — Security self-review.
- [testing.md](testing.md) — Browser journeys and accessibility.
- [volunteer-applications.md](volunteer-applications.md) — Public volunteer applications.
- [weekly-reports.md](weekly-reports.md) — Weekly reports.

## Architecture decisions

- [adr/0001-django-monolith.md](adr/0001-django-monolith.md) — 0001 — Django monolith with server-rendered templates.
- [adr/0002-postgresql-guards.md](adr/0002-postgresql-guards.md) — 0002 — PostgreSQL constraints and triggers as the final guard.
- [adr/0003-central-rbac.md](adr/0003-central-rbac.md) — 0003 — Central RBAC matrix and scoped querysets.
- [adr/0004-audit-chain.md](adr/0004-audit-chain.md) — 0004 — Atomic, append-only, hash-chained audit history.
- [adr/0005-computed-collection-lock.md](adr/0005-computed-collection-lock.md) — 0005 — Compute collection locks from entry creation time.
- [adr/0006-lazy-report-drafts.md](adr/0006-lazy-report-drafts.md) — 0006 — Lazy weekly report drafting instead of cron.
- [adr/0007-report-snapshots.md](adr/0007-report-snapshots.md) — 0007 — Report snapshots and revision line items.
- [adr/0008-database-sessions.md](adr/0008-database-sessions.md) — 0008 — Database session cookies instead of JWT.
- [adr/0009-urdu-pdf-fonts.md](adr/0009-urdu-pdf-fonts.md) — 0009 — Noto Naskh Arabic and WeasyPrint for Urdu PDFs.
- [adr/0010-render-startup.md](adr/0010-render-startup.md) — 0010 — Render hosting and migrations at startup.
- [adr/0011-transition-tables.md](adr/0011-transition-tables.md) — 0011 — Explicit transition tables instead of an FSM library.
- [adr/0012-identifier-counters.md](adr/0012-identifier-counters.md) — 0012 — Locked counters for human-readable identifiers.
- [adr/0013-material-you-css.md](adr/0013-material-you-css.md) — 0013 — Adapt Material You to handwritten logical CSS.
- [adr/0014-operator-demo-rebuild.md](adr/0014-operator-demo-rebuild.md) — 0014 — Keep demo rebuild an operator-only command.
- [adr/0015-raw-sql-exceptions.md](adr/0015-raw-sql-exceptions.md) — 0015 — Limit raw SQL to reviewed infrastructure exceptions.

## Screenshots and artwork

- [screenshots/dashboard-en.png](screenshots/dashboard-en.png) — Fresh local October 2026 head-office dashboard.
- [screenshots/dashboard-ur.png](screenshots/dashboard-ur.png) — The same October 2026 dashboard in Urdu.
- [assets/readme-banner.svg](assets/readme-banner.svg) — Original purple README banner; vector artwork, not an application screenshot.
- [screenshots/export-report-en.png](screenshots/export-report-en.png) — English R7 weekly-report PDF first page.
- [screenshots/export-report-ur.png](screenshots/export-report-ur.png) — Urdu R7 weekly-report PDF first page.
- [screenshots/home-en.png](screenshots/home-en.png) — English public home with the supplied illustrations and original diya mark.
- [screenshots/home-ur.png](screenshots/home-ur.png) — Urdu public home captured from the local authored seed.

## Planning archive

- [planning/00-executive-summary.md](planning/00-executive-summary.md) — 00 — Executive Summary (ShipLens 1.0 · solo · plan dated 2026-10-24).
- [planning/01-compliance-matrix.md](planning/01-compliance-matrix.md) — 01 — Competition Compliance Matrix.
- [planning/02-requirements.md](planning/02-requirements.md) — 02 — Requirements Catalogue.
- [planning/03-ambiguity-register.md](planning/03-ambiguity-register.md) — 03 — Ambiguity & Gap Register.
- [planning/04-personas-journeys.md](planning/04-personas-journeys.md) — 04 — Personas and Journeys.
- [planning/05-rbac-matrix.md](planning/05-rbac-matrix.md) — 05 — Permission Model (RBAC) — documented permission table.
- [planning/06-state-machines.md](planning/06-state-machines.md) — 06 — State Machines.
- [planning/07-business-rules.md](planning/07-business-rules.md) — 07 — Business Rules Catalogue.
- [planning/08-data-model.md](planning/08-data-model.md) — 08 — Data Model (PostgreSQL 16).
- [planning/09-dashboard-and-seed-data.md](planning/09-dashboard-and-seed-data.md) — 09 — Dashboard Specification, Seed Dataset and Expected Values (Gate 1).
- [planning/10-architecture-and-stack.md](planning/10-architecture-and-stack.md) — 10 — Stack Decision and System Architecture.
- [planning/11-security.md](planning/11-security.md) — 11 — Security Plan (OWASP Top 10) and Audit Design.
- [planning/12-i18n-rtl.md](planning/12-i18n-rtl.md) — 12 — Internationalisation and RTL Plan.
- [planning/13-exports.md](planning/13-exports.md) — 13 — Exports Plan (CSV and PDF).
- [planning/14-performance-a11y-seo.md](planning/14-performance-a11y-seo.md) — 14 — Performance, Accessibility and SEO (Lighthouse 90+).
- [planning/15-devops-ci-cd-git.md](planning/15-devops-ci-cd-git.md) — 15 — DevOps, CI/CD and Git Workflow.
- [planning/16-ux-design-screens.md](planning/16-ux-design-screens.md) — 16 — UX: Information Architecture, Design System, Screens, Public Content.
- [planning/17-test-strategy.md](planning/17-test-strategy.md) — 17 — Test Strategy.
- [planning/18-docs-demo-video-qa.md](planning/18-docs-demo-video-qa.md) — 18 — Documentation, Demo Video and Judge Q&A.
- [planning/19-work-plan-plan-a-and-b.md](planning/19-work-plan-plan-a-and-b.md) — 19 — Work Plan: Plan A, Plan B, MoSCoW and Cut-line.
- [planning/20-risks.md](planning/20-risks.md) — 20 — Risk Register, Twist-Readiness Checklist.
- [planning/21-assumptions-and-open-questions.md](planning/21-assumptions-and-open-questions.md) — 21 — Assumptions for Approval and Open Questions.
- [planning/22-codex-prompts.md](planning/22-codex-prompts.md) — 22 — Codex Prompts (development only).
- [planning/23-handbook-reconciliation.md](planning/23-handbook-reconciliation.md) — 23 — Participant Handbook Reconciliation (2026-10-27).
- [planning/24-design-system.md](planning/24-design-system.md) — 24 — Design System: Material You (MD3), adapted to our stack.
