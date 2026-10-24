# 00 — Executive Summary (ShipLens 1.0 · solo · plan dated 2026-10-24)

## What we're building
One bilingual (English/Urdu, RTL) web platform that is both the organisation's public website (7 pages + volunteer form) and a secure back office. Branches log members and offline collections there; weekly reports are drafted automatically, then submitted, reviewed, approved and locked; and head office sees approved figures live. Every change goes into a tamper-resistant audit trail.

## Key facts
- **Deadline:** Mon 2 Nov 2026 23:59 PKT (confirmed). Internal target is 2 Nov 18:00. Feature freeze is 31 Oct.
- **Stack:** Django 5.2 LTS + PostgreSQL 16, server-rendered templates, WeasyPrint for PDFs (shapes Urdu correctly), Docker on Render, GitHub Actions.
- **Gates:** each gate has a named automated test: `T-DASH-SEED` (G1), `T-RPT-LIFECYCLE` (G2), `T-RBAC-MATRIX`/`-SCOPE`/`-ROUTES` (G3), and CI plus `/health` (G4).
- **Sample data:** the organisers published none (checked 24 Oct), so we author it ourselves as CSV files in `sample_data/`, loaded by `import_sample_data`. Its hand-calculated expected values (Oct 2026: collected Rs 73,250.50, approved Rs 43,250.50, unsent Rs 35,250.50 across 6 entries) go into the README and are asserted by `T-DASH-SEED`. The brand is ours too ("Ujala Volunteer Network", placeholder).
- **Git:** about 55 commits, 17 PRs merged with merge commits, commits on 10 distinct days, final commit tagged `v1.0.0`.

## File index
| File | Contents |
|---|---|
| 01 | Compliance matrix (submission items, rules, deliverables, gates, cadence) |
| 02 | Requirements REQ-001…161, traceability to scoring rows and gates, success criteria |
| 03 | Ambiguity & gap register (AMB-01…24) + batched questions |
| 04 | Personas & journeys (6 users, failure paths) |
| 05 | RBAC permission table (final-doc quality) + enforcement & tests |
| 06 | State machines (branch, application, report, collection, content, member) |
| 07 | Business rules BR-001…141 with enforcement point and test |
| 08 | Data model (ER, tables, constraints, triggers, audit tamper resistance) |
| 09 | Dashboard KPIs, seed dataset, hand-calculated expected values |
| 10 | Stack decision matrix, libraries, C4, modules, scheduler-free design, ADR list |
| 11 | OWASP Top 10 mapping, controls, threat model, audit design |
| 12 | i18n / RTL |
| 13 | CSV / PDF exports |
| 14 | Performance, accessibility, SEO, Lighthouse CI |
| 15 | Docker, /health, CI workflows, Render, git workflow, day-by-day commits/PRs |
| 16 | Sitemap, design system, screen inventory, wireframes, public content |
| 17 | Test strategy, mandatory suites, traceability REQ→BR→Test |
| 18 | Docs folder, README, AI-USAGE template, video script, judge Q&A |
| 19 | WBS (Plan A), Plan B line, MoSCoW, cut-line, points-at-risk, final checklist |
| 20 | Risk register, twist-readiness checklist |
| 21 | Assumptions for approval + open questions |

## Self-review results
| Check | Result |
|---|---|
| Every §1.6 scoring row maps to REQs | ✓ (02 §17) |
| Every §1.7 gate maps to REQs, tests and demo steps | ✓ (02 §18, 01 §5, 18 §5) |
| Every REQ maps to a task and a test | ✓. Test IDs are grouped into families in 17 §3.4. |
| Every role is exercised by tests | ✓ (17 §5) |
| Every rule in §1.2 / submission item is in the compliance matrix | ✓ (01 §2–3) |
| **Gaps found** | (1) G1 can't be checked against the **official** sample data until it arrives (R-14). (2) Brand material is missing (placeholder brand used). (3) The CI Lighthouse run can't check the HTTPS audit, so Best Practices on HTTPS gets a manual check on the live site. (4) The audit triggers can be dropped by the DB owner role on Render; this is documented as a limitation. (5) REQ-095 (branch dashboard) is an *Assumed* requirement but only a *Could* in MoSCoW, so it's the first thing cut if time runs short. (6) "Real time" means fresh data on every page load, not push updates. That's documented. |

## (a) Top 10 decisions most affecting success
1. **Django monolith, server-rendered.** It gives the fastest safe path, the best Urdu PDFs, the easiest Lighthouse 90+, and code I can explain.
2. **One permission matrix in code**, with generated docs, parametrised tests, a route registry, and scoped querysets that return 404 for out-of-scope records. This covers Gate 3.
3. **Audit writes inside the same transaction, in an append-only table with a hash chain.** This covers the "every change" requirement and part of the security score.
4. **Snapshot plus copied line items at submit, and a DB trigger once locked.** Approved figures can't change afterwards. This covers Gate 2 and the integrity of the dashboard.
5. **The 7-day lock is computed from `created_at`.** It's configurable, needs no cron, and has no unlock.
6. **Weekly drafts are created lazily and idempotently**, so the free Render tier works without workers.
7. **The seed dataset has hand-calculated expected values, a fixed `as_of` date in tests, and a period selector.** This covers Gate 1. An importer for the official data is planned.
8. **Walking skeleton deployed on day 1**, with CI, Docker, Render and `/health` in place from the start. This covers Gate 4 and the Docker score.
9. **Merge-commit PRs every day** to meet 25+ commits over 7+ days with 3+ PRs, with plenty of margin.
10. **Urdu from day 2 via wrapped strings, CSS logical properties, a Naskh subset font loaded only on `/ur/`, and zero JS on public pages.** This covers the bilingual and Lighthouse targets.

## (b) Assumptions needing your approval
All 30 are in `21-assumptions-and-open-questions.md`. The most consequential: **03** (Django, since it depends on you being stronger in Python), **07** (Super Admin can't approve), **11** (lock counted from entry time, no unlock), **13** (transfer model), **14** (lazy drafts, submit only after the week ends), **19** (no CNIC), **20** (10 h/day), **25** (paid Render during judging).

## (c) First three actions today (Sat 24 Oct)
1. **Post one question on the event's Discussion tab:** "Will official sample data be released, or should entrants author their own fictional dataset?" Screenshot it. That puts on record that no data was provided, and costs nothing if nobody answers.
2. **Create the public GitHub repo and push the first commit** (MIT licence, README stub, AI-USAGE.md with today's entry). Then open PR #1 with these planning docs:
   - Branch: `docs/planning`
   - Commit 1: `docs(planning): add project plan, requirements and compliance matrix`
   - Commit 2: `docs(planning): add data model, RBAC matrix and state machines`
   - PR title: `docs: project plan and architecture decisions`
   - PR body: "Adds the full planning set under docs/planning (requirements, RBAC, state machines, data model, dashboard expected values, architecture, security, test strategy, delivery plan). Planning was AI-assisted (declared in AI-USAGE.md); all decisions reviewed by me."
3. **Build and deploy the walking skeleton** (W-02…W-05): Django scaffold, `/health`, Dockerfile, CI, `render.yaml`, live URL. Merge it as PR #2 `chore: walking skeleton — Django, Docker, CI, Render, /health`, then turn on branch protection and merge-commit-only.
