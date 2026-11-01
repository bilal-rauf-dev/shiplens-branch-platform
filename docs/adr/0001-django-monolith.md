# 0001 — Django monolith with server-rendered templates

Date: 2026-11-01 (recorded from the implementation)

Status: Accepted

## Context

One solo developer must explain every request, support Urdu and deliver secure forms.

## Decision

Use Python 3.12, Django 5.2 LTS and PostgreSQL 16. Render Django templates and keep views thin; put writes in services and reads in selectors/KPIs.

## Consequences

One deployment and one language for application logic. Forms use full-page requests. Chart.js is confined to dashboards.

## Alternatives considered

A React/Next.js SPA adds client state and an API. Laravel was viable but would change the fixed Python stack.
