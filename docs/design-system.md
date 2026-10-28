# ShipLens design system

The source of truth is [the Material You specification](planning/24-design-system.md). Use its light colour roles and components when changing a template. The public site can use soft radial shapes; staff data pages stay plain and tonal.

## Use the styles

`base.html` loads `tokens.css`, `base.css`, `components.css`, then `layout.css` (and `urdu.css` on Urdu pages). Use a token such as `var(--md-primary)` or `var(--md-s4)` instead of a new colour or spacing value. Typography and the keyboard focus ring come from `base.css`. Roboto and Noto Naskh Arabic are served locally from `static/fonts/`.

Use the existing classes in `components.css`: `.btn` plus a variant (`.btn--filled`, `.btn--tonal`, `.btn--outlined`, `.btn--text`, or `.btn--error`), `.card`, `.chip`, `.status-badge`, `.data-table`, `.filter-panel`, `.notice`, and `.empty-state`. Status badges take a `data-status` value matching the model status; the CSS supplies the tonal colour and icon. Keep their visible text. Wrap tables in `.table-container.card`, give each numeric cell `.numeric`, and wrap displayed numbers or codes in `<bdi>`.

Forms use visible labels and the shared `.form-field` wrapper. Add `.form-field--error` when a field has errors, and keep the field's Django errors and helper text visible. The top app bar and staff navigation live in `base.html` and `partials/staff_navigation.html`.

## Do and don't

- Do use logical CSS properties so English and Urdu layouts mirror naturally.
- Do keep keyboard focus visible and test both pointer and keyboard interaction.
- Do put hover effects in `@media (hover: hover)` and respect reduced motion.
- Do use the existing server-rendered forms, messages, and confirm pages.
- Don't add inline styles, public-page JavaScript, third-party fonts, Tailwind, or large blurred elements.
- Don't use colour as the only status signal, scale table rows, or add organic shapes to staff pages.

Run `python bin/check_conventions.py` and the full pytest suite after CSS or template changes. The design tests cover contrast, component rules, stylesheet order, inline styles, and RTL markup.

## Lighthouse

Use the production Docker image and an empty database. Audit `/en/`, `/ur/`, and `/en/get-involved/` in mobile mode, checking Performance, Accessibility, Best Practices, and SEO. Production redirects plain HTTP to HTTPS; when testing on localhost, send `X-Forwarded-Proto: https` to simulate the trusted proxy. The [design specification](planning/24-design-system.md#8-acceptance-for-the-design-pr) sets a minimum score of 90 in each category.

The D1 check on 28 October 2026 used Lighthouse 13.6.0 and a fresh Docker image containing the current source and collected static files on the existing production runtime, with an empty PostgreSQL database. Scores (Performance / Accessibility / Best Practices / SEO) were **100 / 100 / 96 / 91** on each of the three routes. A full default Dockerfile rebuild was attempted but stopped while the package registry was delivering wheels at about 12–25 KB/s; rerun that build before release. The local HTTP proxy simulation causes Lighthouse's separate `robots.txt` fetch to time out, which accounts for the remaining SEO deduction.
