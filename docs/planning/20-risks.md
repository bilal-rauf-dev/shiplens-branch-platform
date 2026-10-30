# 20 — Risk Register, Twist-Readiness Checklist

## 1. Risk register
P = probability, I = impact (1 low – 5 high).

| ID | Risk | P | I | Mitigation | Trigger / early signal |
|---|---|---|---|---|---|
| R-01 | Ambiguous brief interpreted differently by judges | 4 | 3 | Assumptions explicit in README "Interpretations" section; configurable rules; ADRs | Organiser clarifications on Discussion tab |
| R-02 | Deadline conflict | — | — | **Closed**: 2 Nov confirmed | — |
| R-03 | Twist task lands late / large | 3 | 2 | Twist-readiness design (§2); 3 h reserved on 1–2 Nov | Announcement |
| R-04 | Render cold start during judging | 4 | 3 | Starter plan for judging window or keep-warm ping; README note | `/health` response > 5 s |
| R-05 | Render free DB expiry (30 days) before live demo | 4 | 5 | Upgrade DB (~$6) or recreate 1 Nov; calendar reminder 18 Nov | Render dashboard expiry banner |
| R-06 | Urdu PDF shaping broken | 2 | 3 | WeasyPrint (HarfBuzz) + embedded Naskh; test + visual check day 8 | Disconnected letters in PDF |
| R-07 | Lighthouse < 90 from fonts/images/TTFB | 3 | 3 | System font EN, subset UR font only on /ur/, no JS, LHCI on CI, warm measurement | LHCI < 0.9 |
| R-08 | Solo capacity / illness | 3 | 5 | Walking skeleton first; Plan B line; buffer day; cut-line | > 1 day behind on Thu 29 |
| R-09 | Scope creep (optional features) | 3 | 3 | MoSCoW; freeze 31 Oct; OPT list only after gates | Starting an OPT item before CP checks |
| R-10 | Timezone/lock bugs | 3 | 4 | Single clock module, UTC storage, boundary tests, ruff banned-api for `timezone.now` | Failing boundary tests |
| R-11 | CI flakiness (E2E/LHCI) | 3 | 3 | Fixed clock, health-checked services, LHCI median of 3, advisory until stable | Intermittent red on main |
| R-12 | Similarity-check false positive | 2 | 5 | Original design docs, daily granular commits, ADRs, no templates, credits listed | — |
| R-13 | Can't explain AI-assisted code in live demo | 2 | 5 | Line-by-line review before commit, Q&A sheet, self-quiz 1 Nov, boring patterns | Any file I can't explain → rewrite it |
| R-14 | Sample data arrives in unexpected format / differs from seed | 3 | 5 | Tolerant importer + mapping YAML; keep KPI functions pure; 2 h reserved | First look at file |
| R-15 | Demo vandalism on public live site (public SA password) | 3 | 3 | No hard deletes, demo-account protections, operator-only `seed_demo --reset`, seed on first deploy | Odd data on live |
| R-16 | Coverage under 60 % late in the week | 2 | 4 | Tests alongside features; gate from day 1 | CI coverage trend |
| R-17 | WeasyPrint system deps bloat image / fail to install | 2 | 3 | Validate on day 1 in Dockerfile (install libs early) | Docker build failures |
| R-18 | DB triggers complicate tests/migrations | 2 | 2 | Triggers added via RunSQL with reverse; tested explicitly | Migration errors |
| R-19 | Running out of time for video | 2 | 5 | Script ready; record Sun 1 evening; re-record Mon if needed | — |
| R-20 | Commit-history rule mis-count (squash merges) | 2 | 5 | Merge-commit only; count check daily | Count < plan |

## 2. Twist-readiness checklist (decide now; absorb a twist in 2–3 h)
- [ ] All business constants in `BUSINESS_RULES` + `system_settings` (lock days, week start, min age, rate limits, allowed submit timing, code formats).
- [ ] Permission matrix is data; tests parametrised from it; docs generated from it.
- [ ] Role enum in one place; scopes expressed as functions (`GLOBAL`, `ASSIGNED_BRANCHES`) → a "Regional Lead" is a new scope over a new assignment set.
- [ ] Transition tables per entity; audit event names derived from action names.
- [ ] Report fields from `REPORT_FIELDS` registry (JSONB) — new field = 1 entry + 2 translations.
- [ ] KPI functions pure and independent; dashboard template iterates a KPI registry.
- [ ] Exporter registry: `{code: (queryset_fn, columns, renderer)}`; renderers CSV/PDF generic.
- [ ] `LANGUAGES` list + per-locale `.po`; CMS translations keyed by locale; templates use `LANGUAGE_BIDI`.
- [ ] Services emit domain events (`on_commit` hooks) → notifications or webhooks pluggable.
- [ ] Importer framework (mapping YAML) reusable for bulk member import.
- [ ] Seed & expected-values tests make regressions visible within minutes after a twist change.

## 3. Final pre-submission checklist
See `19-work-plan-plan-a-and-b.md` §8 (single source to avoid divergence).
