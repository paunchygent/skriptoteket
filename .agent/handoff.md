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
- Branch / commit: `main` (base: `17a4717`; working tree has uncommitted changes)
- Goal of the session: Implement ST-01-01 taxonomy browsing (profession → category → tool listing) + add migration/live-check workflows.

## What changed

- Marked EPIC-01 active and ST-01-01 done in `docs/backlog/`.
- Added catalog domain models in `src/skriptoteket/domain/catalog/models.py`.
- Added query use-cases + protocols for taxonomy browsing in `src/skriptoteket/application/catalog/` and `src/skriptoteket/protocols/catalog.py`.
- Added Postgres schema + seeded profession/category allowlists via `migrations/versions/0002_catalog_taxonomy.py` and new SQLAlchemy models under `src/skriptoteket/infrastructure/db/models/`.
- Added Postgres repositories for browsing queries in `src/skriptoteket/infrastructure/repositories/` and wired them into Dishka DI in `src/skriptoteket/di.py`.
- Added protected browsing pages under `/browse` in `src/skriptoteket/web/pages/browse.py` + templates in `src/skriptoteket/web/templates/`.
- Added protocol-mocked unit tests for catalog query handlers in `tests/unit/application/catalog/` (+ `tests/fixtures/catalog_fixtures.py`).
- Fixed a real transaction bug in login: `LoginHandler` now enters UoW before any DB reads (avoids SQLAlchemy autobegin conflicts): `src/skriptoteket/application/identity/handlers/login.py`.
- Added required workflow rules:
  - Live UI verification per session: `AGENTS.md`
  - Migration idempotency via Testcontainers: `.agent/rules/054-alembic-migrations.md` (+ index update)
- Added Testcontainers-based migration integration test for `0002_catalog_taxonomy`: `tests/integration/test_migration_0002_catalog_taxonomy_idempotent.py` and dependency `testcontainers` in `pyproject.toml`.
- Added `.env` + `.env.example` and switched `compose.yaml` to use env-driven Postgres credentials + host port mapping (default host port now `55432` to avoid local Postgres conflicts).
- Updated `migrations/env.py` to load `.env` (so `pdm run db-upgrade` uses `DATABASE_URL` from `.env`).
- Fixed `pdm run dev-build-start-clean` to be a PDM composite script (no shell `&&`).
- Applied `alembic upgrade head` against the Docker dev DB and created a new superuser using `.env` bootstrap values.

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
- `pdm run provision-user`
- `pdm run dev` then open `/login` and browse `/browse`
- Docker hot-reload: `pdm run dev-build-start` then open `/login`
- Docker workflow helpers: `pdm run dev-start` / `pdm run dev-stop` / `pdm run dev-build-start-clean` (rebuild no-cache; keeps DB) / `pdm run dev-db-reset` (nukes DB volume)
- Quality gates: `pdm run docs-validate && pdm run lint && pdm run typecheck && pdm run test`
- Migration docker test: `pdm run pytest -m docker --override-ini addopts=''`
- Live UI check (performed this session): started a Testcontainers Postgres + `alembic upgrade head`, created a local user, ran uvicorn, then verified `/browse/` renders seeded professions after login.
- Dev DB port mapping: `localhost:55432` (configure via `POSTGRES_HOST_PORT` in `.env`).

## Known issues / risks

- Tool lists will be empty until tools + tag rows are created (EPIC-03 introduces authoring/governance flows).
- If `pdm run db-upgrade` fails against an existing Docker volume due to mismatched Postgres credentials/users, reset via `pdm run dev-db-reset` (this nukes the DB volume).
- Local dev note: after the Compose change, Postgres maps to `localhost:55432` by default; create a local `.env` from `.env.example` so `DATABASE_URL` matches (the Settings default is still `localhost:5432`).

## Next steps (recommended order)

1. Implement tool governance workflow (EPIC-03) so contributors/admins can create tools and add profession/category tags.
2. Add a minimal tool detail + “run tool” entrypoint after governance creates published tools.
3. Consider integration tests for Postgres catalog repos once tool authoring is in place.

## Notes

- Do not include secrets/tokens in this file.
