# 12 — Internationalisation and RTL Plan

## 1. Approach
- **Library:** Django i18n (gettext). `LANGUAGES = [("en", "English"), ("ur", "اردو")]`, `LANGUAGE_CODE="en"`, `LOCALE_PATHS=[BASE_DIR/"locale"]`, `USE_I18N=True`. Django knows `ur` is bidi → `LANGUAGE_BIDI` is True in Urdu templates.
- **Strings from day 2:** every template string wrapped in `{% translate %}` / `{% blocktranslate %}`; Python strings via `gettext_lazy as _`. Urdu translation pass on day 8, but no hardcoded English is ever committed (`T-I18N-NO-HARDCODED` heuristic: templates scanned for bare text nodes outside trans tags — warn-only).
- **Message IDs:** natural English msgids (Django convention) + `pgettext` contexts for ambiguous words (`pgettext("report status", "Returned")`). Error messages use stable keys in code (`err.phone_invalid`) mapped to translated text in one `messages.py` — easy to audit.

## 2. Files
```text
locale/ur/LC_MESSAGES/django.po   # committed
locale/ur/LC_MESSAGES/django.mo   # compiled in Docker build (compilemessages), not committed
```
Workflow: `makemessages -l ur --ignore=venv` → translate → `compilemessages`. CI runs `makemessages --check`-style diff (script: run makemessages to temp, fail if new msgids missing from committed .po).

## 3. Locale routing & persistence
- Public and app URLs wrapped in `i18n_patterns(prefix_default_language=True)` → `/en/…`, `/ur/…`. `/` redirects by cookie → Accept-Language → `en`.
- Switcher: `<form method="post" action="{% url 'set_language' %}">` with `next` = same path in other language (`translate_url`). Stores `django_language` cookie (Secure, SameSite=Lax, 1 year). Logged-in users: also saved to `user.preferred_language`.
- `/health`, static, exports with explicit `?lang=` are outside i18n patterns.

## 4. RTL layout
- `<html lang="{{ LANGUAGE_CODE }}" dir="{% if LANGUAGE_BIDI %}rtl{% else %}ltr{% endif %}">`.
- **CSS logical properties only:** `margin-inline-start`, `padding-inline-end`, `inset-inline-start`, `border-inline-start`, `text-align: start`. Lint rule: stylelint `liberty/use-logical-spec` (or a simple grep in CI for `margin-left|padding-right|left:|right:|text-align: left`).
- Flex/grid follow `dir` automatically. Directional icons (arrows, chevrons) flipped with `[dir="rtl"] .icon-directional { transform: scaleX(-1); }`.
- Numbers, codes, emails, phones, amounts wrapped in `<bdi>` or `dir="ltr"` spans so `BR-KHI-01` and `+923001234567` don't reorder.
- Tables: column order mirrors naturally; numeric columns `text-align: end`.
- Chart.js: `rtl: true` legend option + `textDirection: 'rtl'` in Urdu.

## 5. Typography and font cost
| Locale | Font | Delivery |
|---|---|---|
| en | System font stack (`system-ui, -apple-system, Segoe UI, Roboto, sans-serif`) | 0 KB |
| ur | **Noto Naskh Arabic** (OFL) regular + bold, subset to Arabic + Urdu ranges (U+0600–06FF, U+0750–077F, U+FB50–FDFF, U+FE70–FEFF, digits, punctuation) with `pyftsubset`, woff2 | ~2 × 45–70 KB; loaded **only on `/ur/` pages** via a locale-specific stylesheet; `font-display: swap`; `<link rel="preload">` for regular weight only |
- Urdu line-height 1.8, base size 1.0625rem (Urdu glyphs read small).
- OPT-07: Noto Nastaliq Urdu for headings only.

## 6. Numerals, dates, money
- Digits: Western (0-9) in both locales (common in Pakistani finance documents, avoids ambiguity). Global `USE_THOUSAND_SEPARATOR=False` (Django default) keeps IDs and form values ungrouped; the money filter groups financial amounts explicitly.
- Dates: Django `date` filter with localised month names (`DATE_FORMAT` per locale in `formats/ur/formats.py`: `j F Y`).
- Money: `Rs 12,345.50` in both locales via one template filter `money`.

## 7. CMS translations
- `content_translations` rows per locale; editor UI has EN / اردو tabs; Urdu tab inputs `dir="rtl" lang="ur"`.
- Publish guard: UR title required; UR body falls back to EN with a visible "Available in English only" note.
- Branch names: `name_en`/`name_ur` columns; templates pick by locale with fallback to EN.

## 8. SEO for bilingual
- `<link rel="alternate" hreflang="en" href="…/en/…">`, `hreflang="ur"`, `hreflang="x-default"` → `/en/`.
- `sitemap.xml` includes both locales with `xhtml:link` alternates (Django sitemaps `i18n=True, alternates=True`).

## 9. RTL in PDFs
WeasyPrint renders the same HTML/CSS templates with `dir="rtl"` and the Naskh font file embedded via `@font-face` (file URL). Pango/HarfBuzz handle shaping and bidi. Test `T-EXP-PDF-UR`: generate Urdu report PDF, extract text with `pypdf`, assert presence of known Urdu label; plus manual visual check recorded as screenshot in `docs/screenshots/`.

## 10. Tests
| Test | Assertion |
|---|---|
| `T-I18N-PARITY` | Parse `ur/django.po` with `polib`: `percent_translated() == 100`, no fuzzy, no obsolete; every msgid from a fresh `makemessages` run present. Placeholder parity: `%(name)s`/`{}` sets equal in msgid and msgstr. |
| `T-I18N-DIR` | GET `/ur/` → `dir="rtl"`, `lang="ur"`; `/en/` → `ltr`. |
| `T-I18N-SWITCH` | POST set_language from `/en/branches/` → redirect `/ur/branches/`, cookie set. |
| `T-I18N-VALIDATION-UR` | Submit invalid form on `/ur/get-involved/` → Urdu error text. |
| `E2E-03` | Playwright: Urdu home screenshot; nav order reversed (first nav item is right-most). |
