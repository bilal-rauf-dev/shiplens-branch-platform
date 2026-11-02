# Performance verification

P13 verification on 31 October 2026 uses the production Docker image, PostgreSQL
16 and the authored sample data. The design follows
[the performance plan](planning/14-performance-a11y-seo.md) and the newer
[Material You specification](planning/24-design-system.md).

## Cold browser transfer

`tests/security/test_browser.py` measures Chromium's CDP
`Network.loadingFinished.encodedDataLength` with the browser cache disabled.
The local production container serves compressed, hashed assets through
WhiteNoise. The browser sends `X-Forwarded-Proto: https` to emulate the trusted
deployment proxy over loopback HTTP. These are local measurements, not network
latency or Lighthouse scores.

| `/en/` resource type | Transferred bytes |
| --- | ---: |
| HTML | 8,163 |
| CSS | 9,780 |
| Fonts | 86,031 |
| **HTML + CSS + fonts** | **103,974** |
| Images | 3,357 |
| **Total including images** | **107,331** |

There are no script elements on public content pages. At this P13 measurement,
only the active language's regular font was preloaded. The current policy is
described below. Existing CMS SVG illustrations are already minified, below the
60 KB hero budget, and rendered images have explicit width and height.

## Query budgets

`tests/security/test_performance.py` checks complete Django client responses,
including middleware, session work and template rendering, against PostgreSQL.
Staff fixtures include thirty extra collections to exercise a populated page.

| Page | Observed queries | Maximum |
| --- | ---: | ---: |
| Every public page, English and Urdu | 0–3 | 6 |
| Super Admin dashboard | 21 | 25 |
| Collection list, Super Admin / Branch Lead | 9 / 10 | 10 |
| Locked report, Super Admin / Branch Lead | 9 / 10 | 12 |
| Draft report, Super Admin / Branch Lead | 11 / 12 | 12 |

Business-rule overrides and evaluated branch assignments are reused within one
request, then discarded. Assignment services invalidate the assignment snapshot
on writes, so revocations take effect during the same request. Direct service
calls continue to read fresh assignments and rules. Report figures combine
collection aggregates in one query; independent member and application counts
use subqueries to avoid multiplying counts through a join.

## Static caching and reproduction

Hashed assets have `Cache-Control: max-age=31536000, public, immutable`. Mutable
asset URLs keep their short cache lifetime. The production-storage integration
test collects files and checks an actual WhiteNoise response for each case.

Build and run the production Docker image with a disposable database, then run
the browser file with `BROWSER_URL`, `BROWSER_EMAIL` and `BROWSER_PASSWORD` set to
that local instance and a disposable Super Admin. It verifies English and Urdu
charts, the CMS editor and PDF downloads before printing the transfer totals.
Run the query tests with the normal PostgreSQL test settings. Asset or content
changes can change the byte totals; query budgets remain regression assertions.


F1 changed Roboto 500/700 to `font-display: optional` to prevent late heading swaps.
Roboto 400 and both Naskh weights retain `swap`; the regular-face fallback alias
remains removed.

The D6 amendment preloads Roboto 400/500/700 on English pages and Noto Naskh Arabic
400/700 on Urdu pages, because the brand lockup and public headings use bold.
No font files were added. The earlier byte measurements remain dated P13 evidence,
not measurements of the current policy. Public window lighting and scroll effects
use only CSS opacity/transform and respect reduced motion; public pages load no
loader script. [D6 verification](testing.md#d6-night-city-verification) records the
current browser and Lighthouse checks.
