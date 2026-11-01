# 0013 — Adapt Material You to handwritten logical CSS

Date: 2026-11-01 (recorded from the implementation)

Status: Accepted

## Context

The owner selected Material You on 28 October; the fixed stack excludes CSS frameworks and requires Urdu RTL.

## Decision

Implement MD3 colors, spacing and components with CSS custom properties and logical properties. Use gradients for public decorative shapes and calm tonal staff pages.

## Consequences

One stylesheet works in both directions; no Tailwind build or inline styles. Local Roboto/Naskh fonts and keyboard/reduced-motion rules need browser checks. See [design system](../design-system.md).

## Alternatives considered

Tailwind would contradict the fixed stack. The earlier teal/amber design is superseded. Full Material web components would add JavaScript and complexity.
