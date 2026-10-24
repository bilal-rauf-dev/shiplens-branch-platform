# 16 — UX: Information Architecture, Design System, Screens, Public Content

## 1. Sitemap

### 1.1 Public (`/{lang}/…`)
```text
/                 Home
/about/           About (story, mission, governance, how money is handled offline)
/programs/        Programs list  → /programs/<slug>/
/branches/        Branch directory (filter by city/status) → /branches/<code>/
/events/          Upcoming + past events → /events/<slug>/
/get-involved/    Volunteer form + donate-offline explanation → /get-involved/thanks/?ref=APP-…
/contact/         Head office details, branch directory link
/privacy/         Privacy notice (linked from form consent)
/accounts/login/  Staff login
```

### 1.2 Staff app (`/{lang}/app/…`) — navigation per role
| Nav item | SA | FR | CE | BL | HR |
|---|---|---|---|---|---|
| Dashboard (head office) | ✓ | ✓ | | | |
| My branch dashboard | | | | ✓ | |
| HR overview | | | | | ✓ |
| Branches | ✓ | ✓ (read) | | ✓ (own, read) | ✓ (own, read) |
| Applications | ✓ (read) | | | | ✓ |
| Members / Teams | ✓ | | | ✓ (read) | ✓ |
| Collections / Transfers | ✓ (read) | ✓ (read) | | ✓ | |
| Weekly reports | ✓ (read) | ✓ (review queue) | | ✓ | |
| Content | ✓ | | ✓ | | |
| Audit log | ✓ | | | | |
| Users / Cities / Roles / Settings | ✓ | | | | |
| Account (password, language) | ✓ | ✓ | ✓ | ✓ | ✓ |

Role home after login: SA/FR → Dashboard; BL → My branch; HR → Applications; CE → Content.

## 2. Design system

**Brand direction:** pending brand pack (Q-02). Placeholder: calm, trustworthy, civic — "lamp/light" motif for "Ujala".

| Token | Value | Use | Contrast |
|---|---|---|---|
| `--c-primary` | `#0B5D57` (deep teal) | buttons, links, header | white on it 7.4:1 ✓ |
| `--c-primary-ink` | `#073F3B` | hover | |
| `--c-accent` | `#E0A526` (lamp amber) | highlights, focus ring alt | on `#1A1A1A` 9:1; **never** as text on white (2.1:1) |
| `--c-text` | `#1A1A1A` | body | on white 17:1 ✓ |
| `--c-muted` | `#5A6470` | secondary text | on white 5.9:1 ✓ |
| `--c-bg` / `--c-surface` | `#FFFFFF` / `#F5F7F7` | | |
| `--c-border` | `#C9D1D3` | decorative dividers only | ~1.5:1 — too low for controls |
| `--c-input-border` | `#7A858C` | form control borders | ~3.9:1 vs white ✓ (≥ 3:1 for UI) |
| `--c-success` | `#1E6B3A` | Approved/Locked/Active | white 6.6:1 |
| `--c-warning` | `#8A5A00` | Returned/Paused | white 5.6:1 |
| `--c-danger` | `#B3261E` | Voided/errors/Closed | white 6.0:1 |
| `--c-info` | `#1F4E99` | Submitted/Forming | white 7.6:1 |
(Ratios to verify with a checker on day 8; adjust shades if any < 4.5.)

**Typography:** EN system stack 16px/1.5; scale 1.25 (h1 2.44rem → h4 1.25rem). UR Noto Naskh Arabic 17px/1.8.
**Spacing:** 4-pt scale (`--s-1` 4px … `--s-8` 48px). Radius 6px. Max content width 72rem.
**Components:** button (primary/secondary/danger, loading state), form field (label, hint, error, counter), select, checkbox group, date input, data table (sortable headers via links, sticky header, responsive "card" mode < 640px), filter bar (GET form), pagination, status badge (text + icon + colour), modal for confirm (native `<dialog>` with form — no JS needed for open via `:target`/details fallback, or tiny JS), toast (server flash messages, `role="status"`), empty state (icon, sentence, primary action), loading (server render → none; skeleton only on dashboard chart), error pages, timeline (audit history), KPI tile, chart card, tabs (EN/UR editor).
**Dark mode:** **No** for MVP — doubles contrast verification work, no scoring benefit. OPT-08.

## 3. Screen inventory

| # | Screen | Roles | Key data / components | Actions | Validation messages (examples) | Mobile |
|---|---|---|---|---|---|---|
| S01 | Public Home | all | hero (CMS), programs teaser, upcoming events, branch count, CTA | Apply, find branch | — | single column |
| S02 | About | all | CMS sections | — | — | |
| S03 | Programs list/detail | all | cards | — | — | |
| S04 | Branches directory/detail | all | filter city/status, cards with badge | — | — | |
| S05 | Events list/detail | all | upcoming/past tabs | — | — | |
| S06 | Get Involved (form) | all | form BR-040…050 | Submit | "Enter a Pakistani mobile number like 0300 1234567" | stacked fields |
| S07 | Thanks | all | reference number | — | — | |
| S08 | Contact / Privacy | all | static/CMS | — | — | |
| S09 | Login | anon | email, password | Sign in | "Email or password is incorrect." / "Too many attempts. Try again in 15 minutes." | |
| S10 | Change password | staff | | Save | "Use at least 12 characters." | |
| S11 | Head-office dashboard | SA, FR | period picker, K1–K10 tiles, TR1/TR2 charts, L1 unsent table, L2 branch table | export PDF/CSV | — | tiles 2-col, tables → cards |
| S12 | Branch dashboard | BL | own KPIs, returned reports alert, lock countdowns | — | — | |
| S13 | Branch list / detail / form | SA (+read others) | code, city, status, counts, history | create, edit, transition | "Close blocked: 3 unsent collections" | |
| S14 | Applications list | HR, SA | tabs Pending/Accepted/Declined, branch filter, duplicate flag | open | — | |
| S15 | Application review | HR | details, duplicate panel, history | accept (team, role), decline (reason), reassign | "Reason is required (5–500 characters)." | |
| S16 | Member list | HR, BL, SA | search, filters, table | export | — | |
| S17 | Member detail/edit | HR, SA | profile, status, history | edit, status change | | |
| S18 | Teams | HR | list per branch | add/rename/deactivate | "A team with this name already exists in this branch." | |
| S19 | Collections list | BL, FR, SA | filters (date, method, state), totals | new, edit, void, mark sent, export | | |
| S20 | Collection form | BL | date, amount, method, receipt, collector, note | save | "Date must be between 17 Oct and 24 Oct 2026." / "Receipt number already used in this branch." | |
| S21 | Transfer form | BL | selected unsent list + total, date, bank ref | save | "Select at least one collection." | |
| S22 | Reports list | BL, FR, SA | week, status, revision, total | open | | |
| S23 | Report detail (per state) | BL, FR, SA | header, status timeline, aggregates, lines, narrative form (BL draft/returned), review panel (FR submitted), review comment banner (returned), lock banner (locked) | submit/resubmit/approve/return/export PDF | "Add a comment explaining what to fix." | |
| S24 | Review queue | FR | submitted + resubmitted, oldest first | open | | |
| S25 | Audit log viewer | SA | filters, table, detail drawer | export, verify chain | | |
| S26 | Content list | CE, SA | type tabs, status badges, "unpublished changes" | new | | |
| S27 | Content editor | CE, SA | EN/UR tabs, markdown textarea, preview, event fields | save draft, publish, unpublish, archive | "Add an Urdu title before publishing." | |
| S28 | Users / Cities / Roles / Settings | SA | tables + forms | CRUD, reset password, reset demo | "Lock days must be between 1 and 30." | |
| S29 | Error pages 403/404/500/429 | all | localised | home link | | |

## 4. Low-fi wireframes

### 4.1 Public home (EN; Urdu mirrors)
```text
┌──────────────────────────────────────────────────────────────┐
│ [logo] Ujala Network   Home About Programs Branches Events    │
│                        Get Involved Contact     [اردو] [Login]│
├──────────────────────────────────────────────────────────────┤
│  HERO: "Light up your city — volunteer with us"              │
│  [Apply to volunteer]  [Find a branch]          (image)       │
├──────────────────────────────────────────────────────────────┤
│  Our programs:  [Education] [Ration Drive] [Health Camps]     │
├──────────────────────────────────────────────────────────────┤
│  Upcoming events: • 8 Nov Health camp, Lahore  • 15 Nov …     │
├──────────────────────────────────────────────────────────────┤
│  4 branches across Pakistan  →  Branch directory              │
├──────────────────────────────────────────────────────────────┤
│ Footer: contact · privacy · "Demo organisation" · © 2026      │
└──────────────────────────────────────────────────────────────┘
```

### 4.2 Volunteer form
```text
Get involved
[!] There are 2 problems with your application  (links to fields)
Full name*            [_____________________]
Email*                [_____________________]
Mobile number*        [0300 1234567_________]  hint: Pakistani mobile
Date of birth*        [dd/mm/yyyy]
  □ My parent/guardian agrees (shown if under 18)
Preferred branch*     [Karachi Central ▼]   (Active + Forming only)
Interests*            □ Education □ Ration Drive □ Health □ General
Availability*         □ Weekday mornings □ Weekday evenings □ Weekends
Why do you want to volunteer?* [textarea]  0/1000
Preferred language    (•) English ( ) اردو
□ I agree to the privacy notice*
[hidden honeypot] [signed timestamp]
[Submit application]
```

### 4.3 Branch register (SA)
```text
Branches                                    [+ New branch]
Filter: City [All▼] Status [All▼] [Apply]
┌──────────┬────────────────────┬──────┬──────────┬────────┬────────┐
│ Code     │ Name               │ City │ Status   │ Members│ Unsent │
├──────────┼────────────────────┼──────┼──────────┼────────┼────────┤
│BR-KHI-01 │ Karachi Central    │ KHI  │ ●Active  │ 4      │ 17,750 │
│BR-ISB-01 │ Islamabad G-9      │ ISB  │ ⏸Paused  │ 2      │ 2,500  │
│BR-QTA-01 │ Quetta Jinnah Road │ QTA  │ ✕Closed  │ 0      │ 0      │
└──────────┴────────────────────┴──────┴──────────┴────────┴────────┘
Detail: [Activate] [Pause] [Resume] [Close…]   History timeline ▸
```

### 4.4 Application review (HR)
```text
APP-2026-00008 · Pending · Karachi Central       ⚠ Possible duplicate
Name, email, phone, age 22, interests, availability, motivation
Duplicate panel: matches member M-2026-00009 (same email) [open]
[Accept…]  [Decline…]  [Reassign branch…]
Accept dialog: Team [Teaching▼] Role [Volunteer▼] [Confirm accept]
 → "Member M-2026-00013 created"
```

### 4.5 Member list
```text
Members (scoped: KHI, LHE)                     [Export CSV]
Search [name / ID / email / phone____] 
Branch [All▼] Team [All▼] Role [All▼] Status [Active▼] Joined [from][to] [Filter] [Reset]
│ M-2026-00010 │ Omar Farooq │ KHI │ Teaching │ Volunteer │ ●Active │ 06 Oct 2026 │
… 25 per page   « 1 2 »
```

### 4.6 Collection entry (BL)
```text
New collection — Karachi Central (BR-KHI-01)
Date*      [24/10/2026]  (allowed 17–24 Oct)
Amount*    Rs [_______.__]
Method*    (•) Cash ( ) Cheque ( ) Bank deposit
Receipt #* [_______]
Collected by [member ▼ optional]   Note [________]
ⓘ You can edit or void this entry until 31 Oct 2026 18:05. After that it is locked.
[Save]
List row states:  ●Open (locks in 3d)  🔒Locked  ✓Sent TRF-…  ✕Voided
```

### 4.7 Weekly report — per state
```text
DRAFT (BL view)
 BR-KHI-01 · Week 19–25 Oct 2026 · Draft · rev 0
 Totals (live): Rs 3,500.00 · 1 entry · Cash 3,500 · New members 0
 Lines: COL-…-00015  21 Oct  Cash  3,500.00
 Activities* [textarea]  Volunteer hours* [__]  Issues [textarea]
 [Save] [Submit for review]

SUBMITTED (FR view)
 Status timeline: Drafted ✓ → Submitted ✓ (Ayesha, 26 Oct 10:02)
 Snapshot totals + lines (read-only), hash a3f9…
 Comment [textarea]   [Return to branch]  [Approve & lock]

RETURNED (BL view)
 ⚠ Returned by Farah Naz: "Attach slip for C06 / amount mismatch"
 Week re-opened: edit open collections; update narrative
 [Resubmit] (rev 1 → 2)

RESUBMITTED (FR view) — same as Submitted, badge "Revision 2"

LOCKED (all)
 🔒 Approved by Farah Naz 26 Oct 11:30 · Locked
 Read-only · [Export PDF] · History (6 events)
```

### 4.8 Head-office dashboard
```text
Dashboard   Period [October 2026 ▼]  (as of 31 Oct 2026)     [PDF] [CSV]
┌Collected──────┐┌Approved──────┐┌Awaiting──────┐┌Unsent (all)───────┐
│Rs 73,250.50   ││Rs 43,250.50  ││Rs 30,000.00  ││Rs 35,250.50 · 6   │
│8 entries      ││59% of coll.  ││              ││oldest 26 days     │
└───────────────┘└──────────────┘└──────────────┘└───────────────────┘
┌Branches A2 P1 F1 C1┐┌Members 9 (+3)┐┌Pending apps 3 · 75%┐┌Reports: 1 to review · 1 returned · compliance 0%┐
[Chart: 12-month collected vs approved]   [Chart: new members]
Unsent collections (sorted by age) …  table L1
Branch summary …  table L2
```

### 4.9 Audit log viewer
```text
Audit log            [Verify chain ✓ intact]  [Export CSV]
From [ ] To [ ] Actor [▼] Action [report.* ▼] Entity [Report ▼] Branch [▼] [Filter]
│ 26 Oct 11:30 │ farah… (FR) │ report.locked    │ BR-KHI-01 · 2026-W43 │
│ 26 Oct 11:30 │ farah… (FR) │ report.approved  │ BR-KHI-01 · 2026-W43 │
│ 26 Oct 11:12 │ ayesha (BL) │ report.resubmitted│ …                    │
Drawer: before {status: RESUBMITTED} → after {status: APPROVED} · IP · request id · hash
```

### 4.10 Content manager
```text
Content   [Programs] [Events] [Page sections]          [+ New]
│ Education Support │ Published │ ● unpublished changes │ edited 30 Oct │
│ Tree Plantation   │ Draft     │                        │               │
Editor:  [English] [اردو]  Title [__] Summary [__] Body (Markdown) [____]
Event: start [ ] end [ ] location [ ] branch [▼]
[Save draft] [Preview] [Publish] [Unpublish] [Archive]
```

## 5. Public content plan
- **Organisation:** "Ujala Volunteer Network" (placeholder until brand pack) — tagline "Light up your city" / "اپنے شہر کو روشن کریں".
- **About:** founded story (fictional), mission, values (transparency, dignity, service), "How we handle donations: offline only, receipted, deposited to our main account and reviewed weekly by finance".
- **Programs:** Education Support (weekend tutoring), Ration Drive (monthly food packs), Community Health Camps (free check-ups with partner clinics); Draft: Tree Plantation.
- **Events:** Health Camp Lahore (upcoming), Ration Packing Day Karachi (upcoming), Volunteer Orientation Islamabad (past).
- **Branches:** auto from register; visibility per BR-013; Forming shows "Coming soon — apply to be a founding volunteer".
- **Get Involved:** volunteer form + "Donate offline at your nearest branch; always ask for an official receipt" (no payment UI).
- **Contact:** head office address (fictional), `info@ujala.example`, phone `+92 21 0000000`.
- **Urdu approach:** I draft English; Urdu translation produced with AI assistance then reviewed for tone by a fluent speaker if available (declared in AI-USAGE.md); all copy kept short to reduce translation risk.
