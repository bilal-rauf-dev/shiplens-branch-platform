# 24 — Design System: Material You (MD3), adapted to our stack

**Decision (2026-10-28, owner):** the UI uses **Material You / Material Design 3** with a purple seed (`#6750A4`). This replaces the teal/amber palette in `16-ux-design-screens.md` §2. Screen inventory, wireframes and page structure in `16-…` still apply; only the visual language changes.

The owner's reference spec is written for Tailwind. **We don't use Tailwind** (see `AGENTS.md` §3: hand-written CSS, logical properties only, no build step). This file translates every rule into plain CSS custom properties and classes, and adds constraints from our other hard requirements: Lighthouse ≥ 90 on mobile, WCAG 2.1 AA, a strict CSP (no inline styles or scripts, fonts from `'self'` only), Urdu RTL, and zero JavaScript on public pages.

## 1. Tokens (`static/css/tokens.css`, loaded first)

```css
:root {
  /* Colour roles — light scheme from seed #6750A4 */
  --md-surface: #FFFBFE;              /* page background; never pure white */
  --md-on-surface: #1C1B1F;           /* body text */
  --md-on-surface-variant: #49454F;   /* secondary text, icons */
  --md-surface-container: #F3EDF7;    /* cards */
  --md-surface-container-low: #E7E0EC;/* inputs, recessed areas */
  --md-primary: #6750A4;
  --md-on-primary: #FFFFFF;
  --md-secondary-container: #E8DEF8;
  --md-on-secondary-container: #1D192B;
  --md-tertiary: #7D5260;
  --md-on-tertiary: #FFFFFF;
  --md-outline: #79747E;
  --md-outline-variant: #CAC4D0;      /* decorative dividers only */
  /* Status roles (MD3 has only "error"; the others are tonal additions with AA contrast) */
  --md-error: #B3261E;        --md-error-container: #F9DEDC;   --md-on-error-container: #410E0B;
  --md-success: #1E6B3A;      --md-success-container: #D4EDDA; --md-on-success-container: #0B2E17;
  --md-warning: #7A5300;      --md-warning-container: #FBE7C2; --md-on-warning-container: #2B1D00;
  --md-info: #1F4E99;         --md-info-container: #DCE6F7;    --md-on-info-container: #0A1F44;

  /* Shape */
  --md-radius-xs: 8px; --md-radius-sm: 12px; --md-radius-md: 16px;
  --md-radius-lg: 24px; --md-radius-xl: 28px; --md-radius-2xl: 32px; --md-radius-3xl: 48px;
  --md-radius-full: 9999px;

  /* Elevation (soft, low-opacity) */
  --md-elev-1: 0 1px 2px rgb(0 0 0 / .08), 0 1px 3px rgb(0 0 0 / .06);
  --md-elev-2: 0 2px 6px rgb(0 0 0 / .10), 0 1px 3px rgb(0 0 0 / .06);
  --md-elev-3: 0 6px 16px rgb(0 0 0 / .12), 0 2px 6px rgb(0 0 0 / .08);

  /* Motion */
  --md-ease: cubic-bezier(0.2, 0, 0, 1);
  --md-dur-fast: 200ms; --md-dur: 300ms; --md-dur-slow: 400ms;

  /* Spacing (4px base) */
  --md-s1: 4px; --md-s2: 8px; --md-s3: 12px; --md-s4: 16px; --md-s5: 24px;
  --md-s6: 32px; --md-s8: 48px; --md-s12: 96px;

  /* Type */
  --md-font: "Roboto", system-ui, -apple-system, "Segoe UI", sans-serif;
  --md-font-ur: "Noto Naskh Arabic", "Roboto", serif;
}
[lang="ur"] { --md-font: var(--md-font-ur); }
```

Contrast checks to verify in tests/Lighthouse: on-surface on surface ≈ 16:1; primary on surface ≈ 6:1 (OK for text and focus rings); on-surface-variant on surface-container ≈ 8:1; outline on surface ≈ 4.4:1 (≥ 3:1 for UI borders). Status text uses the `on-*-container` colours on `*-container` backgrounds (all > 7:1).

## 2. Typography

- **Roboto, self-hosted** (`static/fonts/roboto-{400,500,700}-latin.woff2`, Apache-2.0 licence file included). Not Google Fonts: our CSP allows fonts from `'self'` only, and a third-party font request costs Lighthouse points. `font-display: swap` for 400; `optional` for 500/700 to prevent late heading reflow (F1). English pages preload 400 and 500; Urdu preloads only Naskh. Latin subset only (~20 KB per weight).
- **Urdu keeps Noto Naskh Arabic** (Roboto has no Urdu glyphs), loaded only on `/ur/` pages, as already planned in `12-i18n-rtl.md`.
- Scale (mobile steps one size down): Display 3.5rem/1.2 · Headline L 3rem/1.2 · Headline M 2rem/1.25 · Title L 1.5rem/1.3 · Body L 1.25rem/1.5 · Body M 1rem/1.55 · Label M 0.875rem/1.4 (letter-spacing .01em, weight 500) · Label S 0.75rem/1.4. Headings weight 500; body 400. Urdu line-height +0.25 on every step.

## 3. Components (classes in `static/css/components.css`)

| Component | Rules |
|---|---|
| **Buttons** `.btn` + `.btn--filled` / `--tonal` / `--outlined` / `--text`; sizes `--sm` 36px, default 40px, `--lg` 48px | Always pill (`--md-radius-full`), padding-inline 24–32px, Label M. Filled: primary bg, white text, no shadow at rest, `--md-elev-2` on hover. Tonal: secondary-container. Outlined: 1px outline border, primary text. Text: transparent. **State layers** via a `::before` overlay of `currentColor` at 8% (hover) / 12% (pressed) / 10% (focus) — this is the MD3 way and works for every variant and in RTL. `:active { transform: scale(.95) }`. Transition `background-color, box-shadow, transform` at `--md-dur-fast` with `--md-ease`. Disabled: opacity .38, `cursor: not-allowed`, `pointer-events: none`. Danger actions (void, close branch, return) use `.btn--filled.btn--error`. |
| **FAB** `.fab` | Tertiary bg, 56×56, radius 16px (MD3 FAB), `--md-elev-3`. Use only for the main "add" action on mobile lists (New collection, New application review is not a FAB). Has an accessible label. |
| **Cards** `.card`, `.card--interactive`, `.card--featured` | surface-container bg, radius 24px, padding 24–32px, no border, `--md-elev-1`. Interactive cards (links): hover → `--md-elev-2` + `scale(1.02)`; press → `scale(.98)`. Featured (e.g. the next upcoming event on Home): 2px primary ring and `translate-y(-16px)` on ≥ 768px only. |
| **Hero / major sections** `.hero`, `.section--tonal`, `.section--primary` | Radius 48px (24px under 640px), surface-container bg, generous padding (48–96px block). `--primary` sections (final "Volunteer with us" CTA) use primary bg + white text, with nested glass cards (`rgb(255 255 255 / .12)` bg, 1px `rgb(255 255 255 / .18)` border). |
| **Inputs** (MD3 filled text field) | Height 56px, bg surface-container-low, radius 12px 12px 0 0, bottom border 1px outline at rest → 2px primary on focus (200ms colour transition), plus a visible focus ring for keyboard users. Label always visible above the field (not placeholder-only — accessibility). Errors: bottom border and helper text in `--md-error`, an error icon, `aria-invalid`. Selects, textareas and date inputs share the style; checkboxes/radios use `accent-color: var(--md-primary)` with 44px hit areas. |
| **Chips / badges** `.chip`, `.badge--{status}` | Pill, Label S/M, tonal container colours. Status badges always include text (and an icon), never colour alone: Draft (secondary-container), Submitted/Resubmitted (info), Returned (warning), Approved/Locked (success, lock icon), Voided/Closed (error), Paused (warning), Forming (info), Active (success). |
| **Tables** `.data-table` | Inside a card; header row on surface-container-low; row hover is a state layer only (**no scale on rows** — scaling tables causes layout jank); numbers `text-align: end` with `<bdi>`; card layout under 640px (existing behaviour). |
| **Navigation** | Top app bar: surface at 85% opacity with `backdrop-filter: blur(12px)` and a 1px outline-variant bottom border; sticky. Active nav item = secondary-container pill. Staff app on ≥ 1024px: a navigation rail/drawer with pill active indicator; mobile: the existing `<details>` menu styled as a sheet (radius 28px). |
| **Messages / toasts** | Server flash messages as a snackbar-style card (inverse surface `#313033`, text `#F4EFF4`), radius 8px, `role="status"`; errors use error-container. |
| **Empty states** | Card with a soft blob shape behind an icon, one sentence and a tonal button. |
| **Dialogs** (confirm transitions) | Native `<dialog>` or a confirm page; radius 28px, `--md-elev-3`, scrim `rgb(0 0 0 / .32)`. |

## 4. Atmosphere: organic shapes — the performant way

The spec's signature is large blurred colour shapes. CSS `filter: blur(64px)` on big elements is expensive to paint on mobile and can sink the Lighthouse Performance score. We get the same look cheaply:

- Use **`radial-gradient()` backgrounds** (a soft gradient already looks blurred) on pseudo-elements `::before`/`::after` of `.hero`, `.section--primary` and the Get Involved intro. Colours: primary, secondary-container, tertiary at 15–30% alpha. Shapes are circles and "organic pills" (`border-radius: 100px 20px 100px 100px`).
- Position with **logical** offsets (`inset-inline-end: -10%`), so they mirror in Urdu.
- `pointer-events: none`, purely decorative (pseudo-elements are ignored by screen readers; any real element gets `aria-hidden="true"`).
- At most 3 shapes per section; **none on staff data pages** (tables, forms, reports). Staff pages get tonal surfaces and pill/rounded shapes only, so they stay calm and fast.
- `mix-blend-mode: multiply` is allowed on the hero only.

## 5. Motion

- Easing `--md-ease` everywhere; 200ms for buttons/colours, 300ms for cards/shadows, ≤ 400ms for sheets/dialogs.
- Only `background-color`, `box-shadow`, `opacity`, `transform` animate. Never radius or layout.
- Hover-only effects are wrapped in `@media (hover: hover)` so touch devices don't get stuck hover states.
- `@media (prefers-reduced-motion: reduce)`: remove all transforms and transitions except colour changes ≤ 1ms.

## 6. RTL

All new CSS uses logical properties (`padding-inline`, `inset-inline-start`, `border-start-start-radius` for the input's top corners, `margin-block`). Directional icons flip under `[dir="rtl"]`. Shadows are symmetric, so they need no mirroring.

## 7. Where it applies

| Area | Treatment |
|---|---|
| Public site (7 pages) | Full expression: hero with organic shapes, tonal sections, interactive cards, featured event, primary CTA band, pill buttons. |
| Login / password pages | Centered card (radius 28px) on surface with one soft shape. |
| Staff app | Calm: tonal surfaces, rounded cards, MD3 inputs and buttons, status chips, navigation rail; no decorative shapes; no hover scaling on tables. |
| PDFs | Same colour roles and Roboto/Naskh, but flat (no shadows, gradients or shapes). |
| Dark mode | Not in scope (spec defines light only). |

## 8. Acceptance for the design PR
- Tokens and components implemented as above; all existing templates migrated to the new classes; old teal tokens removed.
- Contrast unit test for the colour pairs in §1 (WCAG formula in Python) — every text pair ≥ 4.5:1, UI borders ≥ 3:1.
- Lighthouse (mobile) on `/en/`, `/ur/`, `/en/get-involved/` still ≥ 90 in all four categories (verify locally; CI gate arrives in P12).
- Keyboard focus visible on every interactive element; reduced-motion respected; RTL screenshots of home, form and one staff table look mirrored and correct.
- No inline styles, no third-party requests, no JavaScript added to public pages.
