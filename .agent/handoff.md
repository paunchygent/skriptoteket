# Session Handoff

Keep this file updated so the next session can pick up work quickly.

## Editing Rules (do not break structure)

- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files instead.
- Never include secrets/tokens/passwords or personal data.
- If you need to write a **chat message** to a new developer/agent, use `.agent/next-session-instruction-prompt-template.md` instead (this file is not that message).

## Snapshot

- Date: 2025-12-13
- Branch / commit: `main` (see `git log -1 --oneline`)
- Goal of the session: Establish identity foundation (sessions + bootstrap) and lock in agent workflow (no legacy, structured handoff).

## What changed

- Implemented v0.1 identity scaffold in `src/skriptoteket/` (local accounts + Postgres sessions, login/logout, DI, migrations).
- Added dev Postgres in `docker-compose.yml` and Alembic migration baseline (`migrations/`, `alembic.ini`).
- Added agent workflow helpers under `.agent/` and documented them in `doc_structure_requirements.md` and `docs/index.md`.
- Enforced **no legacy support** by removing the `app/` shim entirely.

## Decisions (and links)

- Docs/ADRs updated:
  - Future HuleEdu identity federation: `docs/adr/adr-0011-huleedu-identity-federation.md`
  - v0.1 auth: `docs/adr/adr-0009-auth-local-sessions-admin-provisioned.md`
  - Architecture principles: `docs/reference/ref-architecture.md`
- Scope decisions:
  - Browse/run requires login (v0.1) — no anonymous access.
  - No legacy support/workarounds: full refactor only (delete old paths instead of shims).
  - When asked for a “message to a new developer/agent”, fill `.agent/next-session-instruction-prompt-template.md` (address recipient as “you”).

## How to run / verify

- `docker compose up -d db`
- `pdm run db-upgrade`
- `pdm run bootstrap-superuser`
- `pdm run dev` then open `/login`
- Quality gates: `pdm run docs-validate && pdm run lint && pdm run typecheck && pdm run test`

## Known issues / risks

- Docker image build still expects `requirements.txt` in `Dockerfile`; either export it in CI or switch Dockerfile to PDM-based install.
- Tool catalog (profession→category→tool) is not implemented yet; only auth + basic home page exists.

## Next steps (recommended order)

1. Implement taxonomy + navigation UI (ST-01-01) with ordered categories and multi-tag tool listing.
2. Implement persistence for taxonomy/tool metadata (PostgreSQL models + repos behind protocols; UoW-owned transactions).
3. Implement contributor suggestion → admin review → draft tool workflow (EPIC-03) end-to-end.

## Notes

- Do not include secrets/tokens in this file.
