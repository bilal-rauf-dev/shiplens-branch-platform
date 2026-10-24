# 13 — Exports Plan (CSV and PDF)

## 1. Export catalogue

| Code | Export | Format | Columns / content | Roles (scope) |
|---|---|---|---|---|
| X1 | Collections | CSV | reference, branch_code, collection_date, method, amount, receipt_no, status (OPEN/LOCKED/SENT/VOIDED), transfer_ref, created_by, created_at (PKT) | SA, FR (all); BL (own) |
| X2 | Unsent collections | CSV | branch_code, reference, collection_date, method, amount, age_days, locked, week_report_status | SA, FR; BL (own) |
| X3 | Weekly reports list | CSV | branch_code, week_start, week_end, status, revision, total_amount, entry_count, submitted_at, approved_at | SA, FR; BL (own) |
| X4 | Weekly report (official copy) | PDF | header (org, branch, week, status, revision, snapshot hash), aggregates, line items table, narrative, review history (from audit), footer (generated at, by, page x/y). Watermark "DRAFT — NOT APPROVED" unless LOCKED. | SA, FR; BL (own) |
| X5 | Monthly head-office summary | PDF + CSV | K1–K10, per-branch table L2, trend table, unsent list | SA, FR |
| X6 | Members | CSV | member_id, full_name, branch_code, team, role, status, joined_on, left_on, email, phone | SA; HR (scoped) |
| X7 | Audit log (filtered) | CSV | occurred_at, actor, role, action, entity_type, entity_label, branch_code, changes (JSON), ip, request_id | SA |

All exports honour the **same filters** as the on-screen list (query string) and the **same scope** (`scope_queryset`).

## 2. CSV rules
- Encoding **UTF-8 with BOM** (`utf-8-sig`) so Excel opens Urdu text correctly; `\r\n` line endings; RFC 4180 quoting.
- Header row in the export's language (translated) + machine-stable column order.
- **Formula-injection guard:** any cell starting with `=`, `+`, `-`, `@`, `\t`, `\r` is prefixed with `'` — except numeric amount columns, which are written as plain numbers (negative adjustments are numeric, so they are safe).
- Amounts: `12345.50` (no thousands separator) for machine use.
- Streaming via `StreamingHttpResponse` for large sets; filename `shiplens_collections_BR-KHI-01_2026-10_20261031T2300.csv`.

## 3. PDF rules
- **Engine:** WeasyPrint rendering dedicated print templates (`templates/pdf/*.html`) + `pdf.css` with `@page { size: A4; margin: 18mm; @bottom-center { content: counter(page) " / " counter(pages); } }`.
- **Urdu:** `?lang=ur` or current locale; `dir="rtl"`; Noto Naskh Arabic embedded; HarfBuzz shaping. Latin codes/numbers in `<bdi>`.
- **Branding:** org name/logo from brand pack (SVG inlined), colour accent, "Demo data" footer in DEMO_MODE.
- **Pagination:** `thead { display: table-header-group; }` repeats headers; `tr { break-inside: avoid; }`.
- **Performance:** typical report < 1 s, < 60 MB RAM; summary capped at 2,000 line rows (else suggest CSV).
- Generated on request, never stored (no file storage needed).

## 4. Audit of exports
Every export → `export.csv` / `export.pdf` with metadata `{export_code, filters, row_count, lang}`. Rate limit 30/hour/user.

## 5. Tests
| Test | Assertion |
|---|---|
| `T-EXP-CSV-COLLECTIONS` | BOM present; header; row count = scoped queryset; KHI lead sees no LHE rows |
| `T-EXP-CSV-INJECTION` | source_note `=HYPERLINK(...)` exported as `'=HYPERLINK(...)` |
| `T-EXP-CSV-UR` | Urdu headers when `lang=ur`; decodes as UTF-8 |
| `T-EXP-PDF-REPORT` | `application/pdf`, starts with `%PDF`, `pypdf` text contains branch code, total `25,250.50`, "Locked" |
| `T-EXP-PDF-UR` | Urdu PDF text extraction contains a known Urdu label |
| `T-EXP-PDF-WATERMARK` | Draft report PDF contains "DRAFT" |
| `T-RBAC-SCOPE-EXP` | Out-of-scope export → 404; CE → 403 |
| `T-AUD-EXPORT` | audit row with correct row_count |
