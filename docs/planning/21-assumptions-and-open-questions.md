# 21 — Assumptions for Approval and Open Questions

Approve, reject or amend each line. Rejected items change the referenced docs.

| ID | Assumption | Where used | If you disagree |
|---|---|---|---|
| ASSUMPTION-01 | Deadline is 2 Nov 2026 23:59 PKT (**confirmed by you**) | 01, 19 | — |
| ASSUMPTION-02 | **No official sample data exists** (entrant checked 24 Oct). We author fictional CSV sample data in `sample_data/`; its hand-calculated values are the "expected values"; README says so; question logged on the Discussion tab | 09 | If organisers publish data later: load via importer + mapping, add `T-DASH-SAMPLE` |
| ASSUMPTION-03 | Stack: Django 5.2 LTS, server-rendered, PostgreSQL 16 (depends on your Python comfort, Q-04) | 10 | Fallback Next.js plan (+1 day, PDF via Playwright) |
| ASSUMPTION-04 | One role per user | 05, 08 | Many-to-many roles: +2 h |
| ASSUMPTION-05 | Branch Lead and HR Lead are scoped via assignments (BL normally 1 branch; HR 1+) | 05 | Global HR: matrix change |
| ASSUMPTION-06 | Only Super Admin creates users, branches, cities, roles | 05 | — |
| ASSUMPTION-07 | Segregation of duties: SA can't approve reports or decide applications | 05 | Allow SA: matrix change |
| ASSUMPTION-08 | Finance Reviewer sees all financial data but no applicant/member PII; cannot edit figures | 05 | — |
| ASSUMPTION-09 | Content Editor has no operational data access; SA keeps CMS rights as fallback | 05 | — |
| ASSUMPTION-10 | Branch code `BR-{CITY}-{NN}`; member ID `M-{YYYY}-{NNNNN}` global yearly; app ref `APP-{YYYY}-{NNNNN}` | 07 | Format change trivial |
| ASSUMPTION-11 | Collection lock = `created_at` + 7 days (exact instant); configurable; **no unlock**; corrections via adjustment entries | 03, 07 | Lock from collection date: one-line change |
| ASSUMPTION-12 | Collection date must be within the last 7 days and not in future | 07 | — |
| ASSUMPTION-13 | "Sent to main account" = Branch Lead records a Transfer (bank ref) covering whole collections; no partial transfers | 03, 07 | Finance confirmation: OPT-04 |
| ASSUMPTION-14 | Week = Mon–Sun Asia/Karachi; drafts created lazily + by command (no paid cron); submit only after week ends | 03, 06 | — |
| ASSUMPTION-15 | Submitted/approved week closes collections for that week; returned reopens | 07 | — |
| ASSUMPTION-16 | APPROVED and LOCKED are separate states set in one transaction (two audit events) | 06 | Merge into one state |
| ASSUMPTION-17 | Branch status effects per AMB-12 table (Forming accepts applicants, only Active logs collections, Closed hidden) | 03 | — |
| ASSUMPTION-18 | Teams per branch (HR managed); volunteer roles global (SA managed) | 03 | — |
| ASSUMPTION-19 | Public form collects DOB (min age 16, guardian consent < 18); **no CNIC** | 07 | Add CNIC (masked) if sample data requires |
| ASSUMPTION-20 | You have ~10 focused hours/day until 2 Nov | 19 | Fewer hours → apply cut-line earlier |
| ASSUMPTION-21 | Urdu font: Noto Naskh Arabic; Western digits in both locales | 12 | Nastaliq: font swap + line-height tuning |
| ASSUMPTION-22 | Operational data (names, notes) not translated; CMS and UI are | 12 | — |
| ASSUMPTION-23 | No contact form, no email sending, no file uploads in MVP | 03, 11 | OPT-02/03 |
| ASSUMPTION-24 | Placeholder org name "Ujala Volunteer Network" until brand pack | 16 | Use brand pack |
| ASSUMPTION-25 | Paid Render (~$13 for one month) during judging window recommended; otherwise free + keep-warm | 15 | Free tier with documented caveats |
| ASSUMPTION-26 | Django admin disabled in production | 05, 11 | — |
| ASSUMPTION-27 | **Changed 2026-10-29:** dashboard default period = the current month if it has any collections, otherwise the latest month that has collections; the page states which month is shown and why. Judges opening the live site in November see October 2026 (the sample data) instead of an empty month | 09 | Default to the current month only |
| ASSUMPTION-28 | Merge-commit strategy (no squash) to preserve commit count | 15 | — |
| ASSUMPTION-29 | Planning docs committed to the public repo (shows originality) and declared in AI-USAGE | 01 | Keep them private: exclude `docs/planning` |
| ASSUMPTION-30 | Exports audited and rate-limited | 13 | — |

## Open questions (defaults applied)
| # | Question | Default |
|---|---|---|
| Q-02 | ~~Official sample data / brand material?~~ **None published** — own CSV dataset + own brand. | — |
| Q-03 | Official organisation name/logo? | "Ujala Volunteer Network" |
| Q-04 | Python or TypeScript — which can you explain more confidently? | Python/Django |
| Q-05 | OK to spend ~USD 13 on Render for 2–30 Nov? | Yes |
| Q-06 | Hours per day available? | ~10 |
| Q-07 | Nastaliq or Naskh? | Naskh |
| Q-08 | Allow Super Admin to approve/decide? | No |
