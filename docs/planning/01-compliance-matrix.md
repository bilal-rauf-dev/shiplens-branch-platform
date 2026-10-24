# 01 — Competition Compliance Matrix

> Source: the ShipLens 1.0 brief (event page screenshot, 2026-10-24) and the prompt §1.2–§1.7.
> Owner of every row: **me (solo)**. "Date" = target completion date in PKT (UTC+5).
> A row is only "done" when its **Verification** has been performed and ticked in `docs/planning/19-work-plan-plan-a-and-b.md` §Daily checklist.

## 1. Brief facts confirmed from the screenshot

| Fact | Overview text | Sidebar text | Plan position |
|---|---|---|---|
| Task opens | 12 Oct 2026 | 2026-10-19 23:59 | Irrelevant to us: first commit is **2026-10-24**, after both. |
| Submission deadline | **26 Oct 2026, 11:59 PM PKT** | **2026-11-02 23:59** | **CONFLICT.** Plan A = 2 Nov; Plan B = 26 Oct. See below. |
| Results | 9 Nov 2026 | 2026-11-16 23:59 | Keep Render live and DB alive until **≥ 2026-11-30** (live-demo round + appeals). |
| Team | solo or pair | 1–2 members | Solo. |
| Data | "sample data and brand material are released when the task opens" | — | **Not yet in my possession** → Q-01, Q-02. |
| Commit rule | "Commits before 12 October make the submission invalid" | — | No commit exists yet; all commits will be ≥ 2026-10-24. |

### 1.1 Deadline conflict — **RESOLVED 2026-10-24: deadline is 2 Nov 2026 23:59 PKT** (confirmed by me, the entrant)

The analysis below is kept for the record. Plan B is now an **internal checkpoint** (26 Oct EOD = minimum submittable product), not a deadline.

The rule "≥ 25 commits across ≥ 7 days" cannot be satisfied by 26 Oct if the first commit is made on 24 Oct (24, 25, 26 = **3 days**). Therefore:

- **Plan A (2 Nov)** is the only plan that can pass the gate check. 24 Oct → 2 Nov = 10 calendar days.
- **Plan B (26 Oct)** produces a working, deployable minimum, but it **will fail the commit-history gate** unless organisers confirm 2 Nov or relax the rule. Plan B exists only as insurance if organisers say "26 Oct is final, submit what you have" — partial credit/certificate may still be possible.
- **Action today (A-01):** message organisers (info@echolens.digital / WhatsApp on the page / Discussion tab) asking which deadline applies. Screenshot the reply and keep it in `docs/evidence/` (gitignored if it contains personal data; reference it in README).

Regardless of the answer, **commit every day from today**, so that if 2 Nov is confirmed nothing is lost.

## 2. Submission items

| ID | Item | Action | Date | Verification |
|---|---|---|---|---|
| C-01 | Public GitHub repo | Create repo `shiplens-branch-platform` (public from day 1 — keeps timestamps transparent). | 24 Oct | Open repo URL in a logged-out browser. |
| C-02 | MIT licence | `LICENSE` (MIT, year 2026, my name) in the very first commit. GitHub detects "MIT". | 24 Oct | Repo sidebar shows "MIT license". |
| C-03 | Live link on Render | Render Docker web service + Render Postgres via `render.yaml` Blueprint. | 24 Oct (skeleton), final 2 Nov | Incognito: `/en/` loads, `/health` returns `{"status":"ok","db":"ok"}`. |
| C-04 | Final commit hash | Tag `v1.0.0` on `main` after the final merge; copy full 40-char SHA from `git rev-parse v1.0.0`. | 2 Nov | SHA in submission form == SHA deployed (shown in `/health` `version` field) == SHA of green CI run. |
| C-05 | Walkthrough video ≤ 5 min, own voice | Script in `18-docs-demo-video-qa.md`; record with OBS; upload unlisted YouTube/Drive. | 1–2 Nov | Duration ≤ 4:50; link opens logged-out. |
| C-06 | README | Structure in `18-…` §2. | 1 Nov | Checklist in `18-…` §2 ticked. |
| C-07 | `AI-USAGE.md` | Created in the first commit; appended **every working day** (running log). | 24 Oct → 2 Nov | ≥ 1 dated entry per working day; every AI-assisted file listed. |
| C-08 | Test login per role | 5 seeded demo accounts (`*.demo@shiplens.test`) + table in README. | 29 Oct | Log in as each on the live site in incognito; each lands on its role home. |

## 3. Rules

| ID | Rule | Action | Date | Verification |
|---|---|---|---|---|
| C-10 | Build window | No commit before 2026-10-24. Do not copy any older local project into the repo. | always | `git log --reverse --format='%ad' | head -1` ≥ 2026-10-24. |
| C-11 | Original work, no templates | No starter kits (no cookiecutter-django, no admin themes). Django `startproject` output is a framework scaffold, not a template project — declare it in README "Credits". | always | README §Credits lists every dependency + licence; `pip-licenses` output attached to `docs/credits.md`. |
| C-12 | Credit open-source libraries | `docs/credits.md` generated with `pip-licenses --format=markdown`, plus vendored assets (Chart.js MIT, Noto fonts OFL). | 1 Nov | File exists; fonts' OFL text included in `static/fonts/LICENSE-OFL.txt`. |
| C-13 | AI allowed if declared + explainable | AI-USAGE.md log; every AI-assisted change reviewed line by line before commit; Q&A sheet in `18-…` §5. | always | I can explain any file chosen at random (self-test on 1 Nov). |
| C-14 | ≥ 25 commits | Plan has ~45–60 commits (`15-devops-ci-cd-git.md` §6). | 2 Nov | `git rev-list --count main` ≥ 25 (target ≥ 40 for margin). |
| C-15 | Across ≥ 7 days | Commit on **every** day 24 Oct – 2 Nov (10 days). | 2 Nov | `git log --format='%ad' --date=short main | sort -u | wc -l` ≥ 7 (target 10). |
| C-16 | ≥ 3 merged PRs | ~10 feature PRs, each a real feature branch, merged with **merge commit** (not squash, which would collapse commits). | from 24 Oct | `gh pr list --state merged | wc -l` ≥ 3 (target ≥ 8). |
| C-17 | Pairs both commit/speak | N/A (solo). README states "Solo entry". | — | — |
| C-18 | Only provided sample data, no real personal data | Seed uses obviously fictional names, `@example.org`/`.test` emails, `+92 300 0000xxx` style phones. If organisers' sample data arrives, import only that. | always | `grep` for real-looking CNICs/phones in repo = none; seed file reviewed. |
| C-19 | Similarity checks | Own design docs, daily commits, decision log (ADRs) = evidence of originality. | always | ADRs dated; commit history granular. |
| C-20 | Fees non-refundable | Informational. | — | — |
| C-21 | Gate check: repo, live link, video, commit history | Rows C-01…C-16. | 2 Nov | Final checklist `20-risks.md` §3 / `19-…` §8. |
| C-22 | Appeals 48 h | Keep evidence (CI runs, deploy logs, screenshots) until results + 48 h. | 9–18 Nov | Folder `docs/evidence/` (non-sensitive only). |
| C-23 | Live demo with questions | Q&A prep sheet `18-…` §5; keep Render + DB alive through **30 Nov**. | 2 Nov → 30 Nov | Calendar reminder to check `/health` every few days. |

## 4. Deliverables list (§1.5) → action

| ID | Deliverable | Plan doc | Day | Verification |
|---|---|---|---|---|
| D-01 | 7 public pages | 16, 14 | 30 Oct | E2E `E2E-01` visits all 7 in en + ur; Lighthouse ≥ 90. |
| D-02 | Volunteer form, full validation | 07 §BR-040…, 11 | 26 Oct | `T-APP-*` validation tests (each field, each rule). |
| D-03 | Login, 5 roles, documented permission table | 05 | 25 Oct | `docs/permissions.md` exists; `T-RBAC-MATRIX` green. |
| D-04 | Branch register, auto codes, lifecycle | 06, 07, 08 | 26 Oct | `T-BRN-*`. |
| D-05 | Application approval → member auto IDs | 06, 07 | 26 Oct | `T-APP-ACCEPT-*`, concurrency test. |
| D-06 | Member records, search, filters | 16 | 27 Oct | `T-MEM-*`. |
| D-07 | Collections lock after 7 days | 07 BR-060… | 27 Oct | `T-COL-LOCK-*` with frozen clock. |
| D-08 | Weekly report workflow | 06 | 28 Oct | `T-RPT-LIFECYCLE` (Gate 2). |
| D-09 | Dashboard KPIs, trends, unrouted list | 09 | 29 Oct | `T-DASH-SEED` (Gate 1). |
| D-10 | CSV + PDF export | 13 | 29 Oct | `T-EXP-*`. |
| D-11 | Content manager draft/publish | 06, 16 | 30 Oct | `T-CMS-*`. |
| D-12 | Audit trail of all changes | 11 §audit | 25 Oct onward | `T-AUD-COVERAGE` (every mutating route writes ≥ 1 audit row). |
| D-13 | English + Urdu, RTL | 12 | 31 Oct | `T-I18N-PARITY`, E2E checks `dir="rtl"`. |
| D-14 | ≥ 60 % backend coverage | 17 | continuous | CI `--cov-fail-under=60` (raise to 70 on 31 Oct). |
| D-15 | GitHub Actions CI | 15 | 24 Oct | Green badge on README; branch protection requires it. |
| D-16 | Dockerfile + health endpoint | 15 | 24 Oct | CI job runs container and curls `/health`. |
| D-17 | Public repo, MIT, 25/7/3 | §3 | 2 Nov | C-14…C-16. |
| D-18 | Render + PostgreSQL | 15 | 24 Oct | C-03. |
| D-19 | Docs folder: ADRs, API docs, permission table, handover | 18 | 1 Nov | Files exist: `docs/adr/*.md`, `docs/api.md` + `docs/openapi.yaml`, `docs/permissions.md`, `docs/handover.md`. |
| D-20 | One test login per role | C-08 | 29 Oct | C-08. |
| D-21 | README + AI-USAGE | C-06, C-07 | 1 Nov | — |
| D-22 | Video ≤ 5 min | C-05 | 1–2 Nov | — |

## 5. Acceptance gates (§1.7) → proof

| Gate | Proof artefact | Demo step |
|---|---|---|
| G1 Dashboard correct with sample data | `T-DASH-SEED` asserts every value in `09-…` §4; `seed_demo` command; if organisers' sample data arrives, `T-DASH-SAMPLE` with their expected values. | Video 1:00–1:40 |
| G2 Report lifecycle fully audited | `T-RPT-LIFECYCLE` (draft→submit→return→resubmit→approve→lock, asserts 6 audit rows in order); audit viewer filtered by report. | Video 1:40–2:50 |
| G3 No role exceeds permissions, tests prove it | `T-RBAC-MATRIX` (parametrised from the single matrix), `T-RBAC-SCOPE` (IDOR), `T-RBAC-ROUTES` (no unregistered route). | Video 2:50–3:20 (show CI test names) |
| G4 Live link works + CI green on main | Branch protection, Render auto-deploy "after CI checks pass", README badge, `/health` with commit SHA. | Video 0:00–0:20 & 4:30 |

## 6. Commit / PR cadence (summary — full schedule in `15-…` §6)

- Every PR comes from a `feat/…`, `fix/…`, `docs/…`, `chore/…` branch, has a real description from the PR template, a green CI run, and is merged with **"Create a merge commit"**.
- Commits are small and meaningful (Conventional Commits). No empty commits, no whitespace-only commits, no "update" commits.
- Target: ≥ 4 commits/day × 10 days ≈ 40–60 commits; ~10 merged PRs.

## 7. AI-USAGE.md discipline

Created in commit #1 with the template from `18-…` §3. At the end of every working day, append: date, tool, purpose, files touched, what I changed after review, what I verified. This planning session is the first entry ("Claude Code — planning documents in docs/planning; no application code generated").
