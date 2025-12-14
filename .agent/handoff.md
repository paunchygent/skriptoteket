# Session Handoff

Keep this file updated so the next session can pick up work quickly.

## Editing Rules (do not break structure)

- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files instead.
- Never include secrets/tokens/passwords or personal data.
- If you need to write a **chat message** to a new developer/agent, use `.agent/next-session-instruction-prompt-template.md` instead (this file is not that message).

## Snapshot

- Date: 2025-12-14
- Branch / commit: `main` (base: `e3ed146`; working tree has uncommitted changes)
- Goal of the session: Implement ST-03-01 “Contributor submits a script suggestion” end-to-end (domain → application → infra → web) + minimal admin review queue visibility.

## What changed

- Marked EPIC-03 active and ST-03-01 done in `docs/backlog/`.
- Added new domain bounded context for suggestions (pure): `src/skriptoteket/domain/suggestions/models.py`.
- Added application commands/queries/handlers + protocols for suggestions:
  - `src/skriptoteket/application/suggestions/`
  - `src/skriptoteket/protocols/suggestions.py`
- Extended catalog protocols/repos to support listing + validating category slugs:
  - `src/skriptoteket/protocols/catalog.py`
  - `src/skriptoteket/application/catalog/handlers/list_all_categories.py`
  - `src/skriptoteket/application/catalog/queries.py`
  - `src/skriptoteket/infrastructure/repositories/category_repository.py`
- Added Postgres persistence for suggestions + migration:
  - `migrations/versions/0003_script_suggestions.py`
  - `src/skriptoteket/infrastructure/db/models/script_suggestion.py`
  - `src/skriptoteket/infrastructure/repositories/script_suggestion_repository.py`
  - Wired into Dishka: `src/skriptoteket/di.py` (+ `migrations/env.py` import)
- Added server-rendered pages + templates:
  - Contributor: `/suggestions/new` in `src/skriptoteket/web/pages/suggestions.py` + `src/skriptoteket/web/templates/suggestions_new.html`
  - Admin queue: `/admin/suggestions` in `src/skriptoteket/web/pages/suggestions.py` + `src/skriptoteket/web/templates/suggestions_review_queue.html`
  - Added nav links + textarea styling: `src/skriptoteket/web/templates/base.html`
  - Added contributor role dependency: `src/skriptoteket/web/auth/dependencies.py`
- Added tests:
  - Unit tests for suggestion handlers: `tests/unit/application/test_suggestions_handlers.py`
  - REQUIRED migration idempotency test: `tests/integration/test_migration_0003_script_suggestions_idempotent.py`
- Fixed a transaction regression for protected write flows: UoW now begins only when needed (prevents `InvalidRequestError: A transaction is already begun` after auth/session DB reads): `src/skriptoteket/infrastructure/db/uow.py`

## Decisions (and links)

- Suggestion tags are stored as validated slugs (arrays) in Postgres table `script_suggestions` (no cross-domain joins yet); validation happens in the application handler via catalog repos.

## How to run / verify

- `docker compose up -d db`
- `pdm run db-upgrade`
- Create/ensure superuser exists (no secrets in shell history): `set -a; source .env; set +a; pdm run bootstrap-superuser --email "$BOOTSTRAP_SUPERUSER_EMAIL" --password "$BOOTSTRAP_SUPERUSER_PASSWORD"`
- `pdm run provision-user`
- `pdm run dev` then open `/login` and browse `/browse`
- After login (as contributor+), open `/suggestions/new` and submit a suggestion; as admin, verify it appears in `/admin/suggestions`
- Docker hot-reload: `pdm run dev-build-start` then open `/login`
- Docker workflow helpers: `pdm run dev-start` / `pdm run dev-stop` / `pdm run dev-build-start-clean` (rebuild no-cache; keeps DB) / `pdm run dev-db-reset` (nukes DB volume)
- Quality gates: `pdm run docs-validate && pdm run lint && pdm run typecheck && pdm run test`
- Migration docker test: `pdm run pytest -m docker --override-ini addopts=''`
- Live UI check (performed this session): `docker compose up -d`, `pdm run db-upgrade`, logged in via `/login` as an existing superuser from `.env`, submitted a suggestion via `/suggestions/new`, then verified it is listed under `/admin/suggestions`.
- Dev DB port mapping: `localhost:55432` (configure via `POSTGRES_HOST_PORT` in `.env`).

## Known issues / risks

- Tool lists will be empty until tools + tag rows are created (EPIC-03 introduces authoring/governance flows).
- If `pdm run db-upgrade` fails against an existing Docker volume due to mismatched Postgres credentials/users, reset via `pdm run dev-db-reset` (this nukes the DB volume).
- Local dev note: after the Compose change, Postgres maps to `localhost:55432` by default; create a local `.env` from `.env.example` so `DATABASE_URL` matches (the Settings default is still `localhost:5432`).

## Next steps (recommended order)

1. Continue EPIC-03 with admin decisioning for suggestions (accept/modify/deny) and a basic status lifecycle.
2. Add authoring flow to create a Tool from an accepted suggestion (incl. profession/category tag rows).
3. Add audit/event trail and better admin UX (filters, pagination) once volume increases.

## Notes

- Do not include secrets/tokens in this file.
