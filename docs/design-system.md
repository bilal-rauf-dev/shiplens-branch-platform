# ShipLens design system

The source of truth is [the Material You specification](planning/24-design-system.md), including the 2 November night-city amendment. Public pages add night/amber roles, skylines, arches and layered sections; staff data pages keep the light, plain tonal design. The brand lockup and real-wait indicators are shared.

## Use the styles

`base.html` loads `tokens.css`, `base.css`, `components.css`, `icons.css`, then `layout.css`. Public pages additionally load `public.css`; Urdu pages then load `urdu.css`. Staff pages omit `public.css`. Use a token such as `var(--md-primary)` or `var(--md-s4)` instead of a new colour or spacing value. Typography and the keyboard focus ring come from `base.css`. Roboto and Noto Naskh Arabic are served locally from `static/fonts/`; see the [current preload policy](performance.md).

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

Use the production Docker image with a disposable authored seed and the five configured mobile pages, three valid runs each. D6 targets median scores of at least 95 in Performance, Accessibility, Best Practices and SEO; the existing CI baseline remains 90. The local proxy supplies the trusted TLS header for all requests, including `robots.txt`. See [testing](testing.md#d6-night-city-verification) for current results.

Historical D1 evidence (28 October 2026, Lighthouse 13.6.0, empty PostgreSQL database): **100 / 100 / 96 / 91** on each of the three routes then audited. That run used a rebuilt application layer; its attempted full dependency rebuild stopped during slow package downloads. The old proxy also timed out on Lighthouse's separate `robots.txt` request. Later work fixed the proxy, and D6 uses a complete default Docker build and the seeded five-page checks above.
