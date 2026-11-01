# 0009 — Noto Naskh Arabic and WeasyPrint for Urdu PDFs

Date: 2026-11-01 (recorded from the implementation)

Status: Accepted

## Context

Urdu needs joining, bidi layout and legible table spacing in both browser and PDF.

## Decision

Serve local Noto Naskh Arabic WOFF2 faces for Urdu and use WeasyPrint/Pango for PDFs. English uses local Roboto. Keep Western digits and explicit money formatting.

## Consequences

Docker includes native Pango/HarfBuzz libraries. PDF text extraction is imperfect, so visual checks complement automated tests. See [exports](../exports.md) and the [Urdu guide](../i18n-glossary.md).

## Alternatives considered

Nastaliq needs taller lines and more layout work. A browser-based PDF engine would add a heavier runtime.
