# Public website and content workflow

The public organisation is Ujala Volunteer Network (ASSUMPTION-24). The staff
application retains the ShipLens product name. Contact details and sample stories
are fictional. Public impact numbers are authored CMS copy, never live finance data.

## Publishing

Super Admins and Content Editors create a working copy in Content. English and Urdu
tabs are native radio controls styled with CSS. Save, preview, then publish.
Publishing requires an English title/body and an Urdu title (BR-121); an absent Urdu
body shows the English body with an explicit note. Unpublish returns to Draft;
archive removes content from public selectors; restore returns it to Draft.

Editing published content changes only its working translations and metadata.
Public pages, metadata and sitemap slugs use `published_snapshot` until the next
publish. Markdown is sanitized when saved and again in `render_cms`, the single
safe-HTML boundary. Illustrations are four original static SVGs; uploads are absent.
The optional model branch association is not bound from editor form input.

`sample_data/content.csv` is validated by the same header reader as the financial
dataset and imported through CMS services using the Content Editor. Its fixed
event dates include one October event and three November/December events.

## Public routing and SEO

Public routes are registered explicitly. Branches reuse `public_branches()`;
the city filter cannot reveal Closed branches. Public templates show no staff
navigation even when a staff user visits the site. Language switching is Django's
CSRF-protected POST view with a translated next URL.

Indexable pages have canonical and English/Urdu/x-default alternate links,
descriptions and Open Graph metadata. Published summaries supply descriptions
where available. Staff, login and reference-bearing thanks pages have noindex.
The Django sitemap contains only public static pages, published programs/events,
and public branches, with language alternates. Robots excludes staff/account paths.

## Verification

`pytest tests/publicsite` covers both locales, unpublished/archived content and PII
isolation, branch visibility, SEO and a maximum of six queries per public page.
Application-form initial rule reads are batched to meet that budget.

Run `pytest tests/visual -m visual --browser-channel chrome --no-cov` against local
PostgreSQL to capture eight paths at 1440×900 and 390×844 in `.tmp/screenshots/`.
These checks are excluded from default runs and CI. The P10 inspection covered all
16 screenshots, including desktop/mobile navigation, RTL, gradients, control
alignment and overflow. A single past-event card was constrained after inspection.

Lighthouse mobile checks use the seeded local Django server, warmed before audits.
Scores are recorded in the task summary; JSON reports remain in `.tmp/`.

P10 mobile results (performance / accessibility / best practices / SEO):
English home **97 / 100 / 100 / 100**; Urdu home **100 / 100 / 100 / 100**.
