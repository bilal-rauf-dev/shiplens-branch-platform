# CSV and PDF exports

Exports use the permissions in [the generated matrix](permissions.md) and the
catalogue in [planning/13](planning/13-exports.md). They are generated for each GET
request; the application never saves exported files.

CSV links preserve the list's query string. Collections, reports, members and audit
reuse their existing filter forms and scoped selectors. Unsent rows and the monthly
branch table reuse the dashboard's period form and KPI functions. Missing periods
use the dashboard's latest-populated-month default. Unknown query parameters do
not widen scope.

All CSVs have a UTF-8 BOM, CRLF records, translated headers and stable column order.
Amounts have two decimal places without grouping. Text beginning with a spreadsheet
formula prefix gets an apostrophe. Collections also include Source note to cover
the formula-injection example required by planning/13's test catalogue.

Every successful export records its catalogue code (X1–X7), validated filters,
row count and language. The shared per-user allowance defaults to 30 requests per
hour. PDF and CSV requests consume the same budget. Audit CSVs exclude their own
delivery event.

Weekly PDFs reuse report detail data: drafts use live figures, while submitted
and locked reports use the stored revision snapshot and lines. Only locked reports
omit the draft watermark. Monthly PDFs reuse the head-office dashboard data,
including K1–K10, branches, trends and unsent receipts. The 2,000-row limit counts
branch, trend and unsent table rows together; above it, the page suggests CSV.

Print styles use the same flat MD3 colours, A4 pages, 18 mm margins, repeating table
headers, unbroken rows and page counters. Staticfiles finders resolve the stylesheet;
its relative font URLs load local Roboto and Noto Naskh Arabic WOFF2 files. No TTF
copies were needed. The web header uses the original diya mark; PDF templates
retain the organisation's text name and flat print layout.

## Verification

The production Docker image successfully rendered the imported R7 report in English
and Urdu and the October summary. All six resulting pages were rendered to PNG and
inspected for alignment, clipping, repeated headers, page breaks and RTL mirroring.
The paired first-page screenshots show [English](screenshots/export-report-en.png)
and [Urdu](screenshots/export-report-ur.png). D3 refreshed these from the same R7
report and inspected both pages in both languages using bundled Poppler at 94 dpi.
The sample report contains BR-KHI-01, 25,250.50 and Locked; summary totals match
planning/09 §4. The existing WOFF2 fonts embed successfully.

The PDF test checks an extracted Urdu label and embedded Naskh font. Some other
Urdu words extract imperfectly with pypdf despite correct visual shaping; the PDF
image check is necessary alongside text extraction. Export labels are included
in the Urdu catalogue and checked by the translation parity suite.

On Windows without Pango, run PDF tests in Linux using the production image's
libraries and the locked development dependencies. Run `pytest tests/exports`
against PostgreSQL; the normal full suite also covers every export route in the
role matrix. `pypdf` is a development-only dependency for PDF assertions.

Scope checks cover foreign branch IDs and branch text in CSV queries, foreign
report PDF IDs, HR assignment revocation, and Finance Reviewer denial for member
exports. HR filenames identify assigned scope too. The review queue deliberately
does not offer the general report-list CSV button: its implicit review-status
filter is different from the general list.
