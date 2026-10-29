# AI Usage Declaration

I used AI tools as allowed by the ShipLens 1.0 rules. I reviewed and tested every line in this repository, and I can explain it.

## Tools

| Tool | Model / version | Used for |
|---|---|---|
| Claude Code (Anthropic) | Claude Opus | Planning documents in `docs/planning/`, design review, the `AGENTS.md` rules and the Codex task prompts |
| OpenAI Codex | <model> | Implementation following the task prompts in `docs/planning/22-codex-prompts.md`, step by step, with my review before every commit |

## Rules I followed

- I read AI output line by line and ran the tests before committing any of it.
- I never pasted secrets or real personal data into an AI tool.
- I own the business rules, data model and permission decisions (see `docs/planning/` and the ADRs). AI proposed alternatives; I chose.
- AI tools never committed, pushed or opened pull requests. I did every git step myself.

## Log

| Date | Tool | Task | Files | What I changed / verified |
|---|---|---|---|---|
| 2026-10-24 | Claude Code | Project planning documents | `docs/planning/00`–`21` | Reviewed the assumptions, confirmed the 2 Nov deadline, chose to author our own sample data after finding none published |
| 2026-10-25 | Claude Code | Codex rules and task prompts; repository starter files | `AGENTS.md`, `docs/planning/22-codex-prompts.md`, `LICENSE`, `README.md`, `.gitignore` | Reviewed the prompts and rules; filled in my name in LICENSE |
| 2026-10-25 | Codex | P1 walking skeleton | config/, apps/core/, Dockerfile, compose.yaml, CI workflows, render.yaml | Reviewed each step; asked for request-ID validation, HSTS preload removal and health-probe routing before Render; verified live /health |
| 2026-10-25 | Codex | P2 auth, RBAC, audit | apps/accounts/, apps/audit/, apps/core/routes.py, tests/rbac/ | Checked the permission matrix cell by cell against plan 05; asked for a proxy-aware client IP, a lean production image and updated_at on all user writes; reviewed the audit hash chain and raw-SQL exceptions |
| 2026-10-26 | Codex | P3 branch register | apps/branches/, apps/core/ids.py, templates/branches/, tests/branches/ | Removed an unneeded legacy-data backfill from an uncommitted migration; asked for POST-redirect-GET on transitions; verified the transition table against the state diagram and the out-of-scope 404 |
| 2026-10-27 | Codex | P4 volunteer applications | apps/volunteers/, templates/volunteers/, tests/volunteers/ | Verified the atomic accept test also checks the member counter; aligned the plan's reassignment-scope wording with the permission table; checked thanks-page reference validation and silent spam rejection |
| 2026-10-27 | Codex | P5 members, audit viewer, handbook fixes | apps/volunteers/, apps/audit/, docker-compose.yml, tests/ | Reconciled the plan with the participant handbook; restored a historical AI-USAGE row Codex had edited; reviewed the full PR diff; switched Codex to committing each finished step |
| 2026-10-28 | Codex | P6 collections, 7-day lock, transfers | apps/finance/, templates/finance/, tests/finance/ | Required plainly named day-7/day-8 lock tests for the defense; reviewed the full PR diff, the model-level save guard and the transfer DB triggers |
| 2026-10-28 | Codex | P7 weekly report workflow | apps/finance/report_*.py, templates/finance/, tests/finance/test_report_*.py | Reviewed the full PR diff and the six-event lifecycle test driven through the HTTP views; checked DB-level lock triggers |
| 2026-10-28 | Claude Code + Codex | Material You design system | docs/planning/24-design-system.md, static/css/, static/fonts/, templates/ | Chose Material You; Claude adapted the Tailwind reference to plain CSS within our CSP, performance and RTL limits and verified contrast; Codex implemented it; I reviewed the screens locally |
| 2026-10-29 | Codex | P8 sample data, importer, demo reset, dashboards | sample_data/, apps/seed/, apps/dashboard/, templates/dashboard/, tests/seed/, tests/dashboard/ | Authored the timeline and hand-calculated the expected values; reviewed the full diff, including the demo-only reset SQL and its DEMO_MODE guard; checked the dashboard figures against planning/09 |