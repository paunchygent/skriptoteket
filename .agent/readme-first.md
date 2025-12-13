# Read Me First (Agents)

Use this file as the starting point when you begin a new session.

## What this repo is

Skriptoteket is a teacher-first Script Hub: users log in, browse tools by profession/category, upload files, and receive results.
Auth is **local accounts + server-side sessions in PostgreSQL** (v0.1). Future HuleEdu SSO is planned via identity federation.

## Read order (mandatory)

1. `docs/index.md` (PRD/ADRs/backlog entrypoint)
2. `.agent/rules/000-rule-index.md` (engineering rules and patterns)
3. `AGENTS.md` (repo contributor guide)
4. `doc_structure_requirements.md` (docs-contract governance)

## Where to work

- Production code lives in `src/skriptoteket/` (DDD/Clean layers).
- `docs/` is contract-governed; do not add new top-level folders under `docs/` without updating the contract.

## Key commands

- Docs contract: `pdm run docs-validate`
- Format/lint/typecheck: `pdm run format` / `pdm run lint` / `pdm run typecheck`
- Tests: `pdm run test`
- DB (dev): `docker compose up -d db` then `pdm run db-upgrade`
- Bootstrap first superuser: `pdm run bootstrap-superuser`

## Session handoff

Before ending a session, update `.agent/handoff.md` with what changed, decisions, and next steps.
