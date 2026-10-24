# 14 — Performance, Accessibility and SEO (Lighthouse 90+)

## 1. Pages measured (mobile preset, LHCI on CI + manual PageSpeed on live)
`/en/` · `/ur/` · `/en/get-involved/` (form) · `/en/branches/` · `/en/events/` — plus spot checks of `/ur/get-involved/` and `/en/programs/`.
**Targets:** ≥ 90 in Performance, Accessibility, Best Practices, SEO on every measured page. Staff pages: not scored by judges, but kept light (same CSS, Chart.js only on dashboard).

## 2. Performance tactics
| Tactic | Detail |
|---|---|
| Zero JS on public pages | No framework; language switcher is a plain form; mobile nav via `<details>/<summary>`. Only the form page loads a ~1 KB script for live character counters (optional). |
| One small CSS file | ~15 KB unminified → ~4 KB brotli; hashed filename via WhiteNoise manifest; `Cache-Control: max-age=31536000, immutable`. Critical CSS inlining unnecessary at this size. |
| Fonts | EN uses system fonts (0 bytes). UR: subset woff2 Naskh, `font-display: swap`, preload regular only, loaded only on `/ur/`. |
| Images | Few, pre-optimised at build time: AVIF/WebP + JPEG fallback via `<picture>`, explicit `width`/`height` (no CLS), `loading="lazy"` below the fold, `fetchpriority="high"` for hero. Hero ≤ 60 KB. SVG logo inline. |
| Server | gunicorn 2 workers; DB queries per public page ≤ 5 (`select_related`, `prefetch_related`); `django-debug-toolbar` locally to check N+1. Template fragment cache for public CMS blocks (60 s, invalidated on publish) — optional. |
| Compression | WhiteNoise brotli/gzip for static; `GZipMiddleware` **off** (BREACH risk with CSRF tokens on HTML) — HTML is small anyway. |
| TTFB / cold start | Render free instances sleep after 15 min → 30–60 s first hit ruins Performance. Mitigation: paid Starter for judging window (Q-05) or keep-warm ping; measure only warm. LHCI runs against the local Docker build in CI, so CI scores are independent of Render. |
| Third parties | None (no Google Fonts, analytics, maps embeds — map is a link to OpenStreetMap). |

## 3. Accessibility (WCAG 2.1 AA)
- Semantic landmarks (`header`, `nav`, `main`, `footer`), one `h1` per page, logical heading order.
- Skip link "Skip to content" (translated).
- All inputs have `<label for>`; errors linked with `aria-describedby`, `aria-invalid="true"`; error summary at top with links to fields; focus moved to summary on failed submit (server render with `autofocus` on summary).
- Colour contrast ≥ 4.5:1 text, 3:1 UI (palette in `16-…` verified).
- Visible focus ring (`:focus-visible`, 3 px outline, offset).
- Status badges include text, not colour only.
- Tables: `<caption>`, `scope="col"`.
- `lang` attribute per page; mixed-language snippets marked `lang="en"` inside Urdu pages.
- Reduced motion respected (`prefers-reduced-motion`).
- Automated: axe-core via Playwright in `E2E-A11Y` on the 7 public pages × 2 locales (fail on serious/critical).

## 4. SEO
- Unique `<title>` and meta description per page and locale (from CMS page sections where available).
- `hreflang` alternates + `x-default`; canonical URL.
- `sitemap.xml` (Django sitemaps, i18n alternates), `robots.txt` (allow public, disallow `/en/app/`, `/ur/app/`, `/accounts/`).
- Open Graph tags (title, description, image).
- Staff app pages: `<meta name="robots" content="noindex">`.
- Structured data (Could): `Organization` JSON-LD. Inline `<script type="application/ld+json">` is a data block that browsers don't execute; verify on day 8 that the CSP produces no console violation (which would cost Best Practices points). If it does, drop JSON-LD — it is not needed for the SEO score.

## 5. Best Practices
HTTPS, no console errors, no deprecated APIs, correct image aspect ratios, CSP present, no vulnerable JS libraries (Chart.js latest), doctype + charset.

## 6. CI gate (Lighthouse CI)
Job `lighthouse` (on PRs touching templates/static and on `main`): `docker compose up -d` with seed → `treosh/lighthouse-ci-action` with `lighthouserc.json`:
```json
{ "ci": { "collect": { "url": ["http://localhost:8000/en/", "http://localhost:8000/ur/",
  "http://localhost:8000/en/get-involved/", "http://localhost:8000/en/branches/",
  "http://localhost:8000/en/events/"], "numberOfRuns": 3, "settings": { "preset": "mobile" } },
  "assert": { "assertions": {
    "categories:performance": ["error", {"minScore": 0.9}],
    "categories:accessibility": ["error", {"minScore": 0.9}],
    "categories:best-practices": ["error", {"minScore": 0.9}],
    "categories:seo": ["error", {"minScore": 0.9}] } } } }
```
Note: LHCI on `http://localhost` loses HTTPS-related points in Best Practices; run CI container with a self-signed TLS proxy **or** mark `is-on-https` audit off in CI only and verify it manually on live. Default: disable that single audit in CI and document it. If the job is flaky, keep it **required for performance/a11y/seo at 0.85** and verify 0.9 manually on live before submission.
