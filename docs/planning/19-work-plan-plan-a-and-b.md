# 19 — Work Plan: Plan A, Plan B, MoSCoW and Cut-line

> **Update 2026-10-25:** coding starts Sun 25 Oct, so every task moves one day later. The day-by-day calendar in `22-codex-prompts.md` takes precedence over the "Day" column below and over `15-…` §6.2. Feature freeze is now **Sun 1 Nov 12:00**; the buffer is Mon 2 Nov morning; still 9 commit days.

**Deadline (confirmed):** Mon **2 Nov 2026 23:59 PKT**. **Internal submission target:** 2 Nov 18:00 PKT.
**Feature freeze:** Sat **31 Oct 23:59** (after that: only fixes, tests, docs, performance, twist).
**Buffer:** Mon 2 Nov fully reserved (+ ~4 h slack spread over 1 Nov).
**Capacity assumption:** ~10 focused hours/day (ASSUMPTION-20) → ~92 h available 24 Oct–1 Nov; plan uses ~84 h.

## 1. Walking-skeleton order
1 Repo/licence/CI/Docker/Render/health → 2 Auth/RBAC/audit → 3 Branches/applications/members → 4 Collections/reports → 5 Dashboard/seed → 6 Public site/CMS → 7 i18n/RTL → 8 Exports → 9 Hardening/perf/docs/video.
(Exports moved before public site in the calendar because they reuse finance data while it's fresh in mind; i18n strings are wrapped from step 2, so step 7 is translation + RTL polish.)

## 2. WBS (Plan A)

| ID | Task | Day | h | Depends | Definition of done | Risk | Commit / PR |
|---|---|---|---|---|---|---|---|
| W-00 | Ask nothing more of organisers (deadline confirmed); **download sample data + brand pack**; create GitHub repo, Render account | Sat 24 | 0.5 | — | Files in hand or confirmed absent | Data format surprise | — |
| W-01 | Init repo: MIT LICENSE, README stub, AI-USAGE.md, .gitignore, `.env.example`; commit planning docs | Sat 24 | 0.5 | — | Public repo, MIT detected | — | initial commit, PR #1 |
| W-02 | Django project, split settings, `core.clock`, `core.rules`, request-id middleware, base templates/CSS skeleton | Sat 24 | 2 | W-01 | `runserver` shows placeholder home in /en/ | — | PR #2 |
| W-04 | Dockerfile (multi-stage, non-root, HEALTHCHECK), compose, `/health` + tests | Sat 24 | 1.5 | W-02 | `docker compose up` healthy; tests pass | WeasyPrint deps size | PR #2 |
| W-03 | CI: lint, test (pg service, coverage 60), security, docker smoke; Dependabot; CodeQL | Sat 24 | 1.5 | W-04 | All green on PR #2 | YAML fiddling | PR #2 |
| W-05 | `render.yaml`, deploy, env vars, branch protection, merge-commit-only setting | Sat 24 | 1 | W-03 | Live `/health` OK with SHA | Render first deploy issues | PR #2 merged |
| W-10 | Custom User, login/logout, axes lockout, password validators, Argon2, force-change | Sun 25 | 2.5 | W-02 | Tests T-AUTH-*, T-SEC-LOCKOUT green | — | PR #3 |
| W-11 | Permission matrix, `can()`, `scope_queryset`, mixin, route registry, matrix tests scaffold | Sun 25 | 3 | W-10 | T-RBAC-ROUTES green; matrix test harness works | Over-engineering | PR #3 |
| W-13 | AuditLog model, `audit.record`, triggers, hash chain, auth signals, tests | Sun 25 | 3 | W-10 | T-AUD-IMMUTABLE/CHAIN/ATOMIC green | Advisory lock subtlety | PR #3 |
| W-12 | User admin screens (SA): create, assign branches, reset temp password | Sun 25 | 1.5 | W-11, W-13 | Audited; tests | — | PR #3 |
| W-20 | Cities, branches, code generator (counter table), lifecycle + guards, screens, tests | Mon 26 | 3.5 | W-11, W-13 | T-BRN-* incl. race green | — | PR #4 |
| W-30 | Public application form (validation, spam guards, ref), thanks page | Mon 26 | 3 | W-20 | T-APP-VALIDATION/SPAM green | Unicode name regex | PR #5 |
| W-31 | HR review list/detail, accept (atomic, member ID) / decline / reassign, duplicate flag | Mon 26 | 3 | W-30 | T-APP-ACCEPT-ATOMIC/RACE green | — | PR #5 |
| **CP-1** | **Checkpoint 26 Oct EOD = Plan B baseline** (see §4) | | | | | | |
| W-32 | Teams, volunteer roles, member list search/filters/pagination, member edit + status SM | Tue 27 | 3.5 | W-31 | T-MEM-* green | — | PR #6 |
| W-40 | Collections: form, list, computed lock, void, week-closed rule (stub until reports), tests with frozen clock | Tue 27 | 4 | W-20 | T-COL-LOCK-* green | TZ bugs | PR #7 |
| W-41 | Transfers (mark sent), immutability trigger, tests | Tue 27 | 2 | W-40 | T-XFER-* green | — | PR #7 |
| W-42 | Weekly reports: registry, lazy drafts, aggregates, transitions, snapshot, lock trigger, screens per state, lifecycle test | Wed 28 | 8 | W-40, W-41 | **T-RPT-LIFECYCLE green (G2)** | Biggest single task | PR #8 |
| W-14 | Audit viewer + per-entity history panel + CSV | Wed 28 | 1.5 | W-13 | T-AUD-VIEWER | — | PR #8 |
| W-50 | Author `sample_data/*.csv` from `09-…` §3; `import_sample_data` (one load path, replays report transitions for audit); `seed_demo` wrapper (demo users, `DEMO_PASSWORD`); `reset demo` | Thu 29 | 3.5 | W-42 | T-SEED-* green; live login works for 5 roles; CSV totals reconcile with §4 | Typos in CSV → caught by T-DASH-SEED | PR #9 |
| W-51 | KPIs (pure functions), dashboard views, Chart.js trends, unsent list, branch dashboard; `T-DASH-SEED` | Thu 29 | 4 | W-50 | **T-DASH-SEED green (G1)** | Formula disagreement | PR #9 |
| W-55 | CSV exports (BOM, guard, scope, audit) | Thu 29 | 1.5 | W-51 | T-EXP-CSV-* | — | PR #10 |
| W-56 | PDF exports (report, monthly summary) EN; Urdu later | Thu 29 | 2 | W-55 | T-EXP-PDF-* | WeasyPrint in Docker | PR #10 |
| W-61 | CMS models, editor (EN/UR tabs), publish snapshot, sanitising, tests | Fri 30 | 4 | W-11 | T-CMS-* | — | PR #11 |
| W-60 | 7 public pages from CMS + branch directory, privacy page, CMS seed | Fri 30 | 3.5 | W-61 | E2E-01 (EN) | Copywriting time | PR #11 |
| W-62 | SEO: meta, hreflang, sitemap, robots, OG | Fri 30 | 1 | W-60 | T-PUB-SEO | — | PR #11 |
| W-70 | Urdu: .po translation, RTL CSS pass, font subset, Urdu PDF, parity test | Sat 31 | 5 | W-60, W-56 | T-I18N-* green; visual check | Translation volume | PR #12 |
| W-85 | E2E smoke (Playwright + axe), Lighthouse CI, coverage → 70 | Sat 31 | 3.5 | W-70 | e2e + lighthouse jobs green | LHCI flakiness | PR #13 |
| **FREEZE** | **Feature freeze 31 Oct 23:59** | | | | | | |
| W-80 | Security hardening: CSP, headers, cookies `__Host-`, error pages, rate limits on exports, `check --deploy`, gitleaks; self-review vs `11-…` | Sun 1 | 2.5 | all | T-SEC-* green; check --deploy clean | CSP breaks Chart.js | PR #14 |
| W-81 | Performance & a11y fixes from LHCI/axe; image optimisation | Sun 1 | 1.5 | W-85 | ≥ 90 ×4 on 5 pages | Font weight | PR #14 |
| W-91 | Docs: ADRs, api.md (+ test), permissions.md generation, handover, architecture, credits, screenshots | Sun 1 | 3 | all | `docs/` complete | Time squeeze | PR #15 |
| W-90 | README final + AI-USAGE complete | Sun 1 | 1 | W-91 | Checklist §2 of 18 ticked | — | PR #15 |
| W-88 | **Twist task** (when revealed) | TBD | 3 | — | PR with tests | Unknown | PR #16 |
| W-95 | Video: rehearse, record, upload | Sun 1 eve / Mon 2 am | 2 | W-80 | ≤ 5 min, link works | Cold start | — |
| W-99 | Release: final checks, tag v1.0.0, verify live, submit form | Mon 2 | 2 | all | Final checklist (§8) ticked; form submitted by 18:00 | — | PR #17 + tag |
| — | Buffer | Mon 2 | 4–6 | | | | |

Hours by day: Sat 24 ≈ 8 · Sun 25 ≈ 10 · Mon 26 ≈ 9.5 · Tue 27 ≈ 9.5 · Wed 28 ≈ 9.5 · Thu 29 ≈ 10.5 · Fri 30 ≈ 8.5 · Sat 31 ≈ 8.5 · Sun 1 ≈ 11.5 (incl. video) · Mon 2 ≈ 2 + buffer.

## 3. Daily routine (each day)
1. Pull, branch. 2. Build feature with tests alongside (not after). 3. Commit at each green step (≥ 3/day). 4. Push, open PR, wait CI, merge (merge commit). 5. Check Render deploy + `/health`. 6. Append AI-USAGE.md. 7. Tick the day's items below.

## 4. Plan B — minimum submittable scope (checkpoint / emergency cut)
Originally for a 26 Oct deadline (now moot). Use it as the **"never fall below" line**: if by **Thu 29 Oct EOD** the project is behind by > 1 day, cut down to Plan B and spend the remaining days on quality.

| Keep (Plan B) | Simplified | Dropped |
|---|---|---|
| Skeleton, CI, Docker, Render, `/health` | Public pages: static templates with CMS only for Programs/Events | Adjustment entries |
| Auth, 5 roles, matrix + tests (G3) | Urdu: UI strings + RTL; CMS Urdu optional | Monthly summary PDF (keep report PDF) |
| Audit (append-only; chain optional) | Member filters: branch, status, search only | Hash chain verification UI |
| Branches (codes, lifecycle) | Dashboard charts: one trend chart | Audit CSV export |
| Applications → members (auto IDs) | Exports: collections CSV + report PDF | Reassign branch, duplicate flag |
| Collections + 7-day lock + transfers | | Lighthouse CI gate (verify manually) |
| Weekly report lifecycle (G2) | | Branch-scoped dashboard |
| Dashboard KPIs + unsent list (G1), seed | | |
| README, AI-USAGE, docs minimum (ADRs ×4, permissions, api routes, handover) | | |

## 5. MoSCoW weighted by score

| Item | Score rows touched (pts) | MoSCoW |
|---|---|---|
| G1–G4 artefacts (dashboard seed test, lifecycle, RBAC tests, live + CI) | gate (reject if missing) | **Must** |
| CI with coverage ≥ 60 % | Testing 15 | **Must** |
| Dockerfile + health + Render | Docker 10 | **Must** |
| RBAC + audit | Roles/audit 10, Security 15 | **Must** |
| Collections, reports, branches, applications, members | HO features 15 | **Must** |
| CMS draft/publish, Urdu RTL, Lighthouse 90 | 10 | **Must** |
| OWASP controls (CSP, lockout, headers, CSRF, rate limits) | Security 15 | **Must** |
| CSV + PDF exports | HO features | **Must** (deliverable) |
| Docs folder + README + video | Docs 5 + gate | **Must** |
| Audit hash chain + verify | Security, Roles/audit | **Should** |
| E2E smoke | Testing | **Should** |
| Lighthouse CI gate | Perf | **Should** (manual check is Must) |
| Urdu PDF | Bilingual | **Should** |
| Adjustment entries | HO features | **Should** |
| Duplicate flag, reassign | HO features | **Could** |
| Branch-scoped dashboard, HR overview | HO | **Could** |
| CodeQL, gitleaks | Security | **Could** (cheap — do it) |
| Email notifications, Finance confirm transfer, scheduled publishing, dark mode, MFA | — | **Won't (MVP)** → optional list |

### Cut-line (drop in this order, top first)
1. Dark mode / scheduled publishing / email (already Won't)
2. HR overview, branch dashboard → (Could)
3. Duplicate flag & reassign
4. Monthly summary PDF (keep weekly report PDF)
5. Audit CSV export & chain-verify UI (keep chain in DB + command)
6. Adjustment entries (document workaround)
7. E2E beyond `E2E-01` and `E2E-04`
8. Lighthouse CI as a required check (keep manual verification)
**Never cut:** gates, coverage gate, CI green, Render live, RBAC tests, audit, Lighthouse ≥ 90 manual check, docs minimum, video.

### Points-at-risk estimate (if cut-line reached step 8)
| Row | Max | Expected (full plan) | Expected (cut to step 8) |
|---|---|---|---|
| Architecture & code quality | 15 | 12–14 | 11–13 |
| HO features end-to-end | 15 | 13–15 | 11–13 |
| Roles, permissions, audit | 10 | 9–10 | 8–9 |
| Security OWASP | 15 | 12–14 | 11–13 |
| Testing + CI | 15 | 13–15 | 12–14 |
| Docker + deployment | 10 | 9–10 | 9–10 |
| CMS, bilingual, perf | 10 | 8–10 | 7–9 |
| Twist | 5 | 3–5 | 2–4 |
| Docs + demo | 5 | 4–5 | 4–5 |
| **Total** | 100 | **83–98** | **75–90** |

## 6. Optional enhancements (only after freeze criteria met; none may endanger gates/coverage/CI/Lighthouse)
| ID | Enhancement | Cost | Benefit |
|---|---|---|---|
| OPT-01 | TOTP MFA for SA/FR | 3 h | Security points, but demo friction |
| OPT-02 | Contact form with inbox | 2 h | Realism; adds PII + spam surface |
| OPT-03 | Email notifications (returned/approved/accepted) | 2 h + SMTP | UX; no SMTP on free tier |
| OPT-04 | Finance confirms transfer receipt | 2 h | Stronger accountability |
| OPT-05 | Scheduled publishing | 1.5 h | CMS polish |
| OPT-06 | GH Actions cron → draft generation endpoint | 1 h | "Automatic" literalness |
| OPT-07 | Nastaliq headings | 1 h | Urdu authenticity; perf cost |
| OPT-08 | Dark mode | 3 h | Little |
| OPT-09 | Member bulk import from Excel | 3 h | Real migration path from spreadsheets |
| OPT-10 | pg_trgm fuzzy member search | 1 h | UX |

## 7. Daily checklist (tick in PR descriptions)
- [ ] ≥ 3 meaningful commits today · [ ] PR merged with green CI · [ ] `/health` on Render shows today's SHA · [ ] AI-USAGE.md row added · [ ] new strings wrapped for i18n · [ ] audit events for new mutations · [ ] permission matrix + rbac_expected.yaml updated for new routes

## 8. Final pre-submission checklist (Mon 2 Nov)
- [ ] Repo public; MIT licence detected; no secrets (`gitleaks` clean), no real personal data
- [ ] `git rev-list --count main` ≥ 25 · distinct commit days ≥ 7 · merged PRs ≥ 3 (`gh pr list --state merged`)
- [ ] First commit date ≥ 2026-10-24 (after task open)
- [ ] CI green on `main` at tagged commit; coverage ≥ 60 % (actual: __ %)
- [ ] Render URL works in **incognito**; `/health` = ok + matching SHA; all 7 public pages in en + ur
- [ ] Each of 5 test logins works on live; lands on correct home
- [ ] Gate 1: dashboard Oct 2026 values match table · Gate 2: lifecycle performed on live after demo reset · Gate 3: RBAC tests listed in CI · Gate 4: link + CI
- [ ] Lighthouse ≥ 90 ×4 on measured pages (warm) — screenshots saved
- [ ] `docs/` complete (ADRs, api, permissions, handover); README complete with logins; AI-USAGE complete
- [ ] Video ≤ 5:00 uploaded, link opens logged-out
- [ ] Tag `v1.0.0` pushed; full SHA copied; submission form filled (repo, live link, SHA, video, logins) — screenshot of confirmation saved
- [ ] Render web + DB plan upgraded or expiry reminder set for ≤ 20 Nov; demo reset before judging window
