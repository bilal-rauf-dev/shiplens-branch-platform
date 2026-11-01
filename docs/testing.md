# Browser journeys and accessibility

The default `pytest` run excludes `e2e` and `visual` tests. Normal unit/integration
tests still use PostgreSQL and the coverage gate. The E2E suite uses
pytest-playwright's Chromium fixtures against a separately running production
image; it never accesses or resets the target database through Django fixtures.

## Local seeded demo

Use a disposable database with `DEMO_MODE=true` and a `DEMO_PASSWORD` of at least
twelve characters supplied in your shell environment. Production startup runs
`seed_demo --if-empty`, then generates missing weekly drafts. Use fresh
containers/database storage for each complete
run: E2E-04 intentionally advances the seeded R10 report from Draft to Locked.
Do not point write journeys at a database you want to preserve.

Install the locked Python development dependencies, then:

```sh
python -m playwright install chromium
BASE_URL=http://localhost:8000 pytest tests/e2e -m e2e --browser chromium \
  --no-cov --tracing retain-on-failure --screenshot only-on-failure \
  --output test-results/e2e
```

On Windows, set environment variables with `$env:NAME = 'value'`. An installed
Chrome may be selected locally with `--browser-channel chrome`; CI installs the
Chromium revision matching the locked Playwright package. The CI overlay's
loopback proxy supplies `X-Forwarded-Proto: https` on every request, including
Lighthouse's separate robots fetch, to retain production HTTPS/cookie settings.
Direct local browser runs also supply that header. Configure localhost as an allowed host
and its HTTP origin as a trusted CSRF origin on the disposable stack.

| Journey | Proof |
| --- | --- |
| E2E-01 | Eight public pages in both languages: HTTP 200, no console/CSP errors, no serious/critical axe violations |
| E2E-02 | Browser application, HR acceptance, generated member ID and member-list presence |
| E2E-03 / H-13 | Urdu switcher round-trip, server form errors, collections table and October dashboard; four screenshots |
| E2E-04 | Today's collection, seeded R10 submit/return/resubmit/approve/lock and six audit actions |
| E2E-05 | Finance October 2026 Collected KPI: Rs 73,250.50 |
| D3 motion | Six local checks: EN/UR with and without reduced motion, visible hero text, four-pixel directional arrows, tonal KPI chips, static charts and unscaled staff rows |

The public form test honours the real three-second default timing rule. R10 is
identified by Karachi and week starting 19 October 2026, not a database ID. The
temporary collection uses the server's Karachi date and is voided through the
normal UI afterward, keeping the fixed October collected total unchanged.
The tests use the shared `DEMO_PASSWORD` environment variable for all demo users;
no passwords are embedded in test source.

Screenshots and retained failure traces go to the Playwright output directory.
Open a trace with `python -m playwright show-trace path/to/trace.zip`. Artifacts
contain fictional demo data and authenticated browser state; use disposable
credentials and do not commit the artifacts.

## Read-only live checks

Set `BASE_URL` to the Render HTTPS URL and `DEMO_PASSWORD` to that deployment's
demo password, then run the same command. Only E2E-01 and E2E-05 execute remotely;
E2E-02, E2E-03 and E2E-04 are skipped. A request guard also blocks unsafe HTTP
methods remotely except the same-origin login POST needed by E2E-05. No domain
records are created, edited, approved or voided by live checks. Login itself
creates normal session/security records.
The additional local font/contrast regressions also skip on remote targets.

Pytest still imports the repository's Django test settings. Supply a local test
`SECRET_KEY` and syntactically valid PostgreSQL `DATABASE_URL` in the shell, as
for the ordinary suite; these are not the live site's credentials. E2E overrides
the parent database fixture, so no PostgreSQL connection is made by these tests.

The host must be exactly `localhost`, `127.0.0.1` or `::1` to allow write journeys;
a hostname containing one of those words does not qualify. There is no override
flag to permit remote write journeys.

## Accessibility engine

The pinned [axe-core 4.14.0](https://www.npmjs.com/package/axe-core/v/4.14.0) copy
and its MPL-2.0/third-party notices live in `tests/e2e/vendor/`. Tests inject it
from disk using DevTools evaluation, without changing CSP or shipping the engine
to visitors. Serious and critical violations fail the public-page journey;
manual keyboard and screen-reader review is still needed beyond automated rules.

## CI stack and Lighthouse

Both browser jobs build the default production Docker target and start the
disposable stack with the E2E overlay. The workflow supplies a CI-only demo
password, separate from the live site's password. Reproduce the commands locally
after setting a disposable `DEMO_PASSWORD` in the environment:

```sh
docker build --tag shiplens:ci .
docker compose -f docker-compose.ci.yml -f docker-compose.e2e.yml up --detach --wait --wait-timeout 120
python -m playwright install chromium
pytest tests/e2e -m e2e --browser chromium --no-cov --tracing retain-on-failure --screenshot only-on-failure --output test-results/e2e
npx --yes --package @lhci/cli@0.15.1 lhci collect --config=lighthouserc.json
npx --yes --package @lhci/cli@0.15.1 lhci assert --config=lighthouserc.json
docker compose -f docker-compose.ci.yml -f docker-compose.e2e.yml down --volumes
```

Set `COMPOSE_PROJECT_NAME` to a unique disposable project name. Always run the
cleanup command even if a check fails. `down --volumes` deletes that project's
disposable database; it must never target the live stack. On Windows, Lighthouse
can use installed Chrome via `CHROME_PATH` if Chrome discovery needs help.
Collection must succeed for all fifteen runs before asserting scores. An assert
command with zero saved reports is not a valid gate result; the CI action fails
when collection fails.

The `e2e` job uploads retained traces/screenshots on failure. The `lighthouse`
job always stores `.lighthouseci/` reports as a GitHub artifact and does not upload
them to temporary public storage. All actions are pinned to full commit hashes.

Lighthouse measures `/en/`, `/ur/`, `/en/get-involved/`, `/en/branches/` and
`/en/events/` with three mobile runs per page. Each category uses its median score
and must reach 0.90: Performance, Accessibility, Best Practices and SEO. Mobile is
selected with Lighthouse's `formFactor` setting (the older plan example's
`preset: mobile` is not a Lighthouse preset). Only `is-on-https` is disabled,
because CI uses HTTP localhost; the proxy mirrors the production proxy. This
fixed-upstream helper is mounted read-only by the CI overlay and excluded from
the production image. The overlay uses Compose's `!reset` tag (Compose 2.24.4+)
to remove the app's direct host port; only the proxy is exposed on host loopback.
Before handover, manually verify HTTPS, redirects and certificate validity on
the live Render deployment. Local audits do not certify that external setup.

### P12 Step 2 local baseline

Production image, authored demo seed, loopback CI proxy, Lighthouse CI 0.15.1,
three mobile runs on 31 October 2026. All category assertions passed.

| Page | Performance | Accessibility | Best Practices | SEO |
| --- | ---: | ---: | ---: | ---: |
| `/en/` | 99 | 100 | 100 | 100 |
| `/ur/` | 98 | 100 | 100 | 100 |
| `/en/get-involved/` | 100 | 100 | 100 | 100 |
| `/en/branches/` | 99 | 100 | 100 | 100 |
| `/en/events/` | 100 | 100 | 100 | 100 |

These are category medians, not a promise of identical scores on a free-tier
deployment. Font-swap layout shift in individual runs remains for Step 3 review.

### P12 Step 3 fixes and manual review

- A deliberately delayed medium/bold font test reproduced a mobile layout shift
  of 0.1127. The English stack now reuses the preloaded Roboto regular file as a
  fallback until those weights arrive. The same test measures 0.0000 afterward;
  all faces retain `font-display: swap`, with no extra font preload or download.
- Axe could not determine some backgrounds because of decorative pseudo-elements.
  Pixel sampling of the rendered backgrounds found the home hero's outlined
  button at only 4.290:1. It now has an opaque MD surface backing: 6.282:1 at
  rest, 5.603:1 on hover and 5.423:1 on keyboard focus in both languages. The
  regression hides glyph paint temporarily to sample the actual backing under
  the text; geometry, gradient, foreground colour and state layers remain intact.
- All 27 final E2E/accessibility cases pass. An additional review of all axe
  severities on the sixteen public variants found no violations. Other
  pseudo-element contrast entries were manually checked against rendered pixels;
  the lowest reviewed text contrast was 4.622:1, above the 4.5:1 requirement.
- Keyboard verification confirms the first Tab reaches the skip link and Enter
  focuses the main landmark. Urdu form/table/dashboard screenshots remain in the
  Playwright output. Automated results do not replace screen-reader review.

Remaining diagnostic notices are documented rather than hidden by disabling
audits. Axe's pseudo-element contrast entries require the manual check above.
Lighthouse can report the four small synchronous CSS layers as render blocking;
they keep the first paint styled, and inline CSS is prohibited by CSP. Dynamic
HTML stays uncompressed per the security plan's BREACH precaution; hashed static
assets use WhiteNoise compression. A local slow-CPU notice describes the test
machine, not an accessibility failure; throttling and category gates are unchanged.

Final Lighthouse verification used fifteen successful reports (exactly three for
each of the five URLs), with no runtime errors and all category assertions
passing. A Windows Chrome trace-recording error on an earlier attempt was
discarded and the entire collection repeated. Every final run measured CLS 0.

| Page | Performance | Accessibility | Best Practices | SEO |
| --- | ---: | ---: | ---: | ---: |
| `/en/` | 99 | 100 | 100 | 100 |
| `/ur/` | 98 | 100 | 100 | 100 |
| `/en/get-involved/` | 99 | 100 | 100 | 100 |
| `/en/branches/` | 99 | 100 | 100 | 100 |
| `/en/events/` | 99 | 100 | 100 | 100 |

The results use Lighthouse 12.6.1 through LHCI 0.15.1. Small Performance score
variation between collections is expected; the category gate and simulated
mobile throttling were not relaxed. The final E2E run used Playwright's pinned
headless Chromium, with all twenty-seven cases passing. Local regression tests
also reproduced and checked the font fix in the installed Chrome channel used
by Lighthouse.


## F1 deterministic font loading

The earlier P12 regular-face alias still allowed timing-dependent heading rewraps
in CI. F1 removes it. Roboto 500/700 use `font-display: optional`: a late heading
font will not replace its fallback during that page load. Roboto 400 and the
Urdu Naskh faces retain `swap`. English pages preload 400 and 500; Urdu preloads
only Naskh, with no new font files.

The mobile font regression now checks 412 px and 360 px. At each width it creates
six fresh browser contexts: five with both heading faces delayed 0.7 seconds,
then one with the regular face also delayed 0.3 seconds. Every context must meet
the unchanged CLS limit of 0.1. Per-run JSON and traces go to Playwright output.
The complete E2E suite is run against a fresh seed three times for F1; R10 must
be reset by the operator between runs, because its lifecycle test locks it.


F1 Step 1 verification (1 November 2026): all three full Chromium runs passed
28/28 cases (99.40 s, 92.84 s and 95.04 s). All 36 delayed-font contexts recorded
CLS 0. The normal PostgreSQL suite passed 2,119 tests with 97.88% app coverage.
The unchanged Lighthouse configuration produced fifteen successful mobile reports
and passed all four median category gates:

| Page | Performance | Accessibility | Best Practices | SEO |
| --- | ---: | ---: | ---: | ---: |
| `/en/` | 99 | 100 | 100 | 100 |
| `/ur/` | 98 | 100 | 100 | 100 |
| `/en/get-involved/` | 100 | 100 | 100 | 100 |
| `/en/branches/` | 100 | 100 | 100 | 100 |
| `/en/events/` | 100 | 100 | 100 | 100 |


## F1 proxy header boundary

The CI-only proxy drops copied request or response headers if either their name
or value contains CR or LF. It writes a fixed direction-specific notice to stderr
without printing the rejected data, avoiding log injection or credential leakage.
Safe headers and duplicate response cookies are preserved. Unit tests inject
CRLF, lone CR and lone LF into both names and values at the copy boundary; they
mock transport because a real HTTP client may reject the payload before the
proxy can inspect it.

Newline-free candidate copies are compared with the originals; any difference
drops the entire header, rather than forwarding a repaired value. Safe copies
are forwarded only when unchanged. This also exposes the sanitization boundary
to [CodeQL's Python header-injection model](https://github.com/github/codeql/blob/main/python/ql/lib/semmle/python/security/dataflow/HttpHeaderInjectionCustomizations.qll),
which recognises newline replacement.


F1 Step 2 verification: 21 focused safety tests passed, including six CR/LF
header cases exercising both directions; all 17 public/Finance browser checks
passed through the restarted proxy. The full PostgreSQL suite passed 2,125 tests
with 97.88% app coverage. Ruff, formatting and convention checks passed.
CodeQL was not executed locally because its CLI is unavailable; the existing
CodeQL workflow will perform the scan in CI.

## D3 visual polish checks

`tests/core/test_visual_assets.py` checks every CMS illustration path, SVG size
and safety, template icon coverage and the CSS motion boundary. Positive
animations/transitions must opt in through `prefers-reduced-motion: no-preference`;
keyframes and transitions may change only opacity or transform. The browser
checks in `tests/e2e/test_motion.py` exercise both preferences and both languages.
Directional icons stay mirrored even when motion is disabled. Staff charts render
without animation, and staff data pages have no decorative gradient shapes.

The D3 Lighthouse acceptance target is 95 in all four categories on all five
configured pages, using the median of three valid mobile runs. The existing CI
baseline in `lighthouserc.json` remains 90. Incomplete traces are not valid audits;
retry those runs without discarding completed measurements. Prefer collecting
performance measurements after CPU-heavy test runs finish.

The README's home/dashboard screenshots were recaptured in EN and UR from a
fresh local authored seed using installed Chrome at 1440×1000, device scale 1,
full-page capture after fonts and lazy images loaded. The paired report images
come from the existing export route; see [PDF verification](exports.md#verification).
Financial reference values stay fixed; ages and compliance use the capture date.

D3 completed local verification (1 November 2026):

| Step | Full PostgreSQL suite | App coverage | Browser checks |
| --- | --- | --- | --- |
| 1 — Illustrations | 2,172 passed, 0 failed | 97.86% | 16 public-page cases; eight EN/UR viewports |
| 2 — Icons | 2,194 passed, 0 failed | 97.86% | 16 public-page cases; eight EN/UR viewports |
| 3 — Motion | 2,195 passed, 0 failed | 97.86% | Full E2E: 34 passed; final eight-viewport check |

Ruff, formatting, conventions and Urdu extraction passed in every step. The
final catalogue has 781 message entries. The final E2E run includes the original
font-delay/CLS regressions. A new motion assertion was corrected to wait for CSS
readiness on script-free public pages; both motion preferences then passed.

Mobile Lighthouse medians (three completed runs per page in each step):

| Page | Performance S1 | Performance S2 | Performance S3 | Accessibility, every step | Best Practices, every step | SEO, every step |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `/en/` | 99 | 99 | 99 | 100 | 100 | 100 |
| `/ur/` | 98 | 99 | 99 | 100 | 100 | 100 |
| `/en/get-involved/` | 100 | 98 | 100 | 100 | 100 | 100 |
| `/en/branches/` | 100 | 100 | 100 | 100 | 100 | 100 |
| `/en/events/` | 100 | 100 | 100 | 100 | 100 | 100 |

All 45 completed audits scored at least 96 in every category. Two Step 2
NO_NAVSTART recordings were retried; completed scores were retained. The final
set ran after the heavy test workloads finished. HTTPS/certificate validation
remains a separate live check; only the localhost HTTPS audit was skipped.

## D4 visual review fixes

Step 1: 2,202 PostgreSQL tests passed, 0 failed, with 97.86% app coverage.
Eight new local EN/UR browser checks passed: Finance/HR/Branch Lead heading
hierarchy, scoped summary/unsent export labels, unchanged generic CSV labels,
text-only audit chips, and amount/date wrapping with contained table overflow
at 360, 768 and 1440 px. Mobile table cards remained active below 640 px.
Every value of the six domain status enums has an explicit badge-mask rule.
Ruff, formatting, conventions and Urdu extraction passed (783 entries).
