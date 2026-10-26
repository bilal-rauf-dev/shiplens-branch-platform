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
