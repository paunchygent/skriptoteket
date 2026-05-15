# Migrations

Use this reference for Alembic revisions, schema drift, and migration safety
tests.

## Read First

- `.codex/rules/054-alembic-migrations.md`
- `.codex/rules/053-sqlalchemy-patterns.md`
- `docs/runbooks/runbook-testing.md`
- `local-devops` plus its Skriptoteket reference for dev DB/container lanes

## Rules

- Every migration change needs a Docker/Testcontainers integration test.
- Prove `alembic upgrade head` on a fresh database and that a second upgrade is
  a no-op success.
- Prefer also proving `downgrade base` then `upgrade head` when the migration
  supports it.
- Once a revision has been applied to any persistent dev or staging database,
  do not rewrite it in place; add a forward repair migration.
- Keep migration tests small and focused on the schema/data contract the
  revision guarantees.

## Commands

Use the exact migration command surface in `.codex/rules/054-alembic-migrations.md`.
Run the docker-marked test lane before applying the migration to the dev DB.
