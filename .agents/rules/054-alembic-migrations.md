---
id: "054-alembic-migrations"
type: "implementation"
created: 2025-12-13
scope: "backend"
---

# 054: Alembic Migrations

## Required workflow (non-negotiable)

When you add or change a migration under `migrations/versions/` you **MUST**:

1. Add a docker-based integration test (Testcontainers) that validates migrations are safe to re-run:
   - `alembic upgrade head` succeeds on a fresh database
   - running `alembic upgrade head` again is a no-op and still succeeds
   - (recommended) `alembic downgrade base` then `alembic upgrade head` succeeds again
2. Run the docker integration test locally:
   - `pytest -m docker --override-ini addopts=''`
3. Apply the migration to the dev database once tests pass:
   - `docker compose up -d db`
   - `pdm run db-upgrade`
   - If the DB volume was initialized with different credentials, reset via `pdm run dev-db-reset`.
4. Once a revision has been applied to any persistent dev/staging database, treat that migration file as immutable:
   - never rewrite an already-applied revision in place
   - add a new forward repair migration for follow-up schema changes or drift recovery

## Docker dev workflow

- `pdm run dev-start`, `pdm run dev-build-start`, `pdm run dev-rebuild`, and `pdm run dev-db-reset`
  must leave the Docker dev lane at `alembic upgrade head`; do not rely on a
  separate manual migration step after containers are already serving.
- If Docker dev still reports impossible schema drift after auto-upgrade,
  prefer a forward repair migration when the state may exist on another
  teammate/staging DB. Use `pdm run dev-db-reset` only for disposable local
  cleanup.

## Testing conventions

- Place migration tests under `tests/integration/`.
- Mark them with `@pytest.mark.docker` (they require Docker).
- Keep them small and focused: validate schema exists + any seed data assumptions required by the app.
- Do not couple tests to implementation details beyond what the migration guarantees.
