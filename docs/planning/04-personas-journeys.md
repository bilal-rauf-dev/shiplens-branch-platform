# 04 — Personas and Journeys

All names are fictional and match the demo seed accounts (`*.demo@shiplens.test`).

## P1 Super Admin — "Sana Mirza", head-office operations manager
- **Goals:** one trusted picture of all branches; onboard branches and staff safely; prove accountability to donors/board.
- **Tasks:** create branches and users, assign leads, change branch status, watch the dashboard, read the audit trail, export summaries, configure business rules.
- **Pains solved:** no more copy-pasting WhatsApp numbers; "who changed this?" is answerable; new branches don't need a new spreadsheet.

| # | Journey | Steps | Failure paths |
|---|---|---|---|
| J1.1 | Open a new branch | Branches → New → choose city "Multan", name EN/UR, address → Save → code `BR-MUX-01` generated, status Forming → later "Activate" | City missing → Super Admin adds city with 3-letter code; duplicate branch name in same city → validation error. |
| J1.2 | Onboard a Branch Lead | Users → New → email, name, role Branch Lead, assign `BR-MUX-01` → temporary password shown once → user forced to change on first login | Email already used → error; assigning Branch Lead to a Closed branch → blocked. |
| J1.3 | Close a branch | Branch detail → "Close branch" → system checks guards → confirm with reason → status Closed, hidden publicly | Unsent collections exist → error lists them with link; open report exists → error. |
| J1.4 | Investigate a change | Audit log → filter entity "Collection" + branch KHI + date range → open entry → see before/after diff, actor, IP | Hash chain check fails → banner "Audit integrity check failed at #n" (should never happen; visible). |
| J1.5 | Monthly summary | Dashboard → period Oct 2026 → "Export PDF" | Branch with no data → shows 0 rows, not an error. |

## P2 Finance Reviewer — "Bilal Qureshi", head-office finance
- **Goals:** approve only correct numbers; know where cash is that hasn't reached the main account.
- **Tasks:** review queue, compare snapshot vs line items, approve or return with comment, monitor unsent list, export.

| # | Journey | Steps | Failure paths |
|---|---|---|---|
| J2.1 | Approve a report | Review queue → "BR-LHE-01 · week 12–18 Oct · Submitted" → open → check lines & totals → Approve → status Approved → Locked | Report changed state meanwhile (another reviewer) → "This report is no longer awaiting review" (optimistic check on status+revision). |
| J2.2 | Return a report | Open → Return → comment required ("Receipt 1043 amount differs from slip") → status Returned; Branch Lead sees comment | Empty comment → validation error. |
| J2.3 | Chase unsent cash | Dashboard → Unsent collections → sort by age → export CSV → follow up with branch | None. |
| J2.4 | Attempt to edit figures | No edit control exists; direct POST to edit URL → 403 + audit `permission.denied` | — |

## P3 Branch Lead — "Ayesha Khan", Karachi Central branch
- **Goals:** log money quickly and correctly; submit the weekly report without re-typing numbers.
- **Tasks:** log collections, void mistakes within 7 days, record transfers, review auto-drafted report, add narrative, submit, fix and resubmit when returned.

| # | Journey | Steps | Failure paths |
|---|---|---|---|
| J3.1 | Log a collection | Collections → New → date, amount, method, receipt no. → Save → appears as Open (locks in 7 days, countdown shown) | Future date / older than 7 days → error; duplicate receipt no. in branch → error; branch Paused → form disabled with explanation. |
| J3.2 | Fix a mistake | Open collection (within 7 days) → Edit amount → Save (audited) or Void with reason | Locked → edit/void buttons absent; direct request → 409 "Entry locked on 14 Oct 14:02". Week already submitted → "Week closed for reporting". |
| J3.3 | Submit weekly report | Reports → current/previous week Draft (auto-created) → review computed totals → fill activities, volunteer hours → Submit → snapshot taken | Required narrative missing → validation; zero collections → allowed with confirmation "No collections this week". |
| J3.4 | Resubmit after return | Notification badge "1 returned" → open → read comment → fix collection (if still open) or explain in narrative → Resubmit (rev 2) | Collection already locked → must explain in narrative; adjustment entry (Should). |
| J3.5 | Record transfer to main account | Collections → filter Unsent → tick entries → "Mark as sent" → bank ref + date → Save → entries Sent | No entries selected → error; entry voided meanwhile → rejected, list refreshes. |

## P4 HR Lead — "Usman Tariq", HR for Karachi & Lahore
- **Goals:** respond to applicants fast; keep member records tidy.
- **Tasks:** review applications, accept/decline, assign team/role, update member status, search members, export members.

| # | Journey | Steps | Failure paths |
|---|---|---|---|
| J4.1 | Accept applicant | Applications → Pending (KHI, LHE only) → open → see "possible duplicate" flag if any → Accept → choose team + role → member `M-2026-00013` created | Two HR leads accept same application simultaneously → second gets "Already decided". |
| J4.2 | Decline applicant | Open → Decline → reason (required, internal) → status Declined | — |
| J4.3 | Find a member | Members → search "0300" or name → filter team "Teaching", status Active → open → edit status Inactive (audited) | Out-of-scope member id in URL → 404. |
| J4.4 | Manage teams | Teams → New "Ration Drive" for KHI → assign members | Duplicate team name in branch → error. |

## P5 Content Editor — "Hina Baig", communications volunteer
- **Goals:** keep the public site fresh in both languages without a developer.
- **Tasks:** create programs/events/page sections, preview, publish, archive.

| # | Journey | Steps | Failure paths |
|---|---|---|---|
| J5.1 | Publish an event | Content → New Event → EN tab, UR tab, date/location → Save draft → Preview → Publish → appears on /en/events and /ur/events | Urdu title missing → "Add Urdu title before publishing"; end before start → error. |
| J5.2 | Edit live content safely | Edit published program → Save → badge "Unpublished changes"; site still shows old version → Publish changes | — |
| J5.3 | Archive past event | Archive → disappears from public list | — |
| J5.4 | Attempt operational access | Types `/app/collections/` → 403 page | — |

## P6 Public visitor — "Ali", university student in Lahore
- **Goals:** understand the organisation, find a nearby branch, apply.
- **Tasks:** browse pages, switch to Urdu, find branch, submit application.

| # | Journey | Steps | Failure paths |
|---|---|---|---|
| J6.1 | Learn and apply | Home → Programs → Get Involved → fill form → submit → confirmation with reference `APP-2026-00009` | Invalid phone → inline message in current language; under 16 → error; too many submissions from IP → "Please try again later" (429). |
| J6.2 | Find a branch | Branches → filter city → see address, status badge, contact | Closed branch not listed. |
| J6.3 | Use Urdu | Click "اردو" → same page mirrored RTL → form labels and errors in Urdu | — |
| J6.4 | Bot submission | Honeypot filled or submitted in < 3 s → silently discarded with generic success page; logged | — |
