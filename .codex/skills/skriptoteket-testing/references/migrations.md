# Migrations

Use this reference for Alembic revisions, schema drift, and migration safety
tests.

## Read First

- `.codex/skills/skriptoteket-backend-dev/SKILL.md`
- `docs/runbooks/run-skript-runbook-testing-pytest-vitest-playwright-runbook-testing-pytest-vitest-playwright.md`
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

Use the migration command surfaces in `docs/runbooks/run-skript-runbook-testing-pytest-vitest-playwright-runbook-testing-pytest-vitest-playwright.md` and `local-devops` plus its Skriptoteket reference.
Run the docker-marked test lane before applying the migration to the dev DB.
