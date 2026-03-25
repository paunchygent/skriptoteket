---
type: pr
id: PR-0145
title: "Alembic migration integrity and full idempotency coverage"
status: done
owners: "agents"
created: 2026-03-25
updated: 2026-03-25
stories:
  - "ST-26-03"
  - "ST-27-01"
tags: ["backend", "ops", "testing", "migrations", "remediation"]
acceptance_criteria:
  - "Given `pdm run db-upgrade` runs against a database that is already at the current head revision, when Alembic is invoked again, then the command no-ops cleanly instead of attempting to recreate `alembic_version`."
  - "Given a migration exists under `migrations/versions/`, when the integration suite or coverage guard runs, then the repo fails if there is no matching migration integration test for that revision."
  - "Given the current migration chain extends beyond `0031` into `0032` and the newer classroom-planner revisions, when migration coverage is reviewed, then those newer revisions have explicit integration coverage instead of relying on the older numbered subset only."
  - "Given a developer brings up a fresh local database, when they run the documented migration/bootstrap flow, then the resulting DB reaches the current head revision and the app-specific columns expected by current code are present without manual catalog surgery."
---

## Problem

The original local `db-upgrade` failure was not the same thing as the earlier `smart_enabled`
schema drift. The recovered local database already contained
`classroom_planner_plan_drafts.smart_enabled`, and the current `alembic_version` row already
reported head revision `4a9d7c1e2b34`.

What was missing was deterministic coverage for the newer migration chain. Once explicit revision
coverage was added for every previously uncovered migration, the first real reproducible defect was
not a multiple-head problem and not the old `smart_enabled` drift:

- `0032_user_file_vault` reused a stale SQLAlchemy inspector after `op.create_table(...)`
- on a fresh upgrade path, `user_vault_files` and `user_vault_usage` were created, but the
  `user_vault_files` indexes were silently skipped because the stale inspector still believed the
  table did not exist

That meant the repo had a real migration-integrity defect, but it was narrower and more concrete
than the earlier local symptom suggested.

The validated migration graph findings so far are:

- one base revision: `0001_init`
- one current head revision: `4a9d7c1e2b34`
- the local recovered DB already reports `alembic_version.version_num = 4a9d7c1e2b34`

The repo also has a process gap: migration integration coverage currently stops at the older
numbered subset (`0002` through `0031`). The newer chain, including `0032_user_file_vault` and the
classroom-planner revisions from `57a6ea32ef0a` through `4a9d7c1e2b34`, does not have matching
integration tests. Because of that gap, the newer migration chain was never held to the same
idempotency standard as the older one.

## Goal

Identify and fix the Alembic/version-table idempotency defect, then make migration coverage
complete and enforceable so every revision in `migrations/versions/` has matching integration
coverage.

## Non-goals

- Replanning EPIC-26 or EPIC-27 feature scope.
- Shipping product behavior changes unrelated to migrations.
- Relying on one-off local catalog cleanup as the long-term answer.

## Root cause summary

- Immediate technical issue:
  - `0032_user_file_vault` used a stale inspector after creating new tables, so the fresh-upgrade
    path skipped the `user_vault_files` indexes.
- Process/root-cause issue:
  - the repo did not maintain the "every migration gets integration coverage" rule past the older
    numbered migrations, so the newer chain was never exercised under the same head-on-head and
    downgrade/re-upgrade conditions.
- Ruled-out explanation:
  - current evidence does not point to multiple Alembic heads or a detached migration branch; the
    observed graph is linear from `0001_init` to `4a9d7c1e2b34`.
  - after the DB was recovered, repeated local `pdm run db-upgrade` invocations no-oped cleanly,
    so the earlier `alembic_version` catalog error was not the deterministic migration defect.

## Implementation summary

- Added `scripts/check_migration_test_coverage.py` and wired it into `pdm run lint` so every
  migration revision must have explicit integration coverage.
- Added `tests/integration/test_migration_revision_coverage_idempotent.py` plus shared support in
  `tests/integration/migration_idempotency_support.py` and
  `tests/integration/migration_schema_assertions.py`.
- Covered every previously uncovered revision:
  - `0001_init`
  - `0012_tool_owner_user_id`
  - `0014_tool_versions_settings`
  - `0022_email_verification_tokens`
  - `0026_profile_ai_settings`
  - `0032_user_file_vault`
  - the classroom-planner chain from `57a6ea32ef0a` through `4a9d7c1e2b34`
- Fixed `migrations/versions/0032_user_file_vault.py` so it refreshes inspection state before
  deciding whether to create the `user_vault_files` indexes.

## Test plan

- `pdm run docs-validate`
- `pdm run python -m scripts.check_migration_test_coverage`
- `pdm run pytest -m docker tests/integration/test_migration_revision_coverage_idempotent.py`
- `pdm run db-upgrade`
- `pdm run db-upgrade`

## Rollback plan

- Revert the migration-coverage guard and new migration tests if they prove incorrectly specified.
- Revert the Alembic remediation if it introduces a broader migration regression.
- Preserve the documented root-cause notes so the failure mode is not rediscovered from scratch.
