# Browser journeys and accessibility

The default `pytest` run excludes `e2e` and `visual` tests. Normal unit/integration
tests still use PostgreSQL and the coverage gate. The E2E suite uses
pytest-playwright's Chromium fixtures against a separately running production
image; it never accesses or resets the target database through Django fixtures.

## Local seeded demo

Use a disposable database with `DEMO_MODE=true` and a `DEMO_PASSWORD` of at least
twelve characters supplied in your shell environment. Production startup runs
`seed_demo --if-empty`. Use fresh containers/database storage for each complete
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
