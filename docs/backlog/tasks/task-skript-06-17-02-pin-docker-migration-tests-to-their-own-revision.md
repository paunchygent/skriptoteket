---
type: task
id: TASK-SKRIPT-06-17-02
title: Pin docker migration tests to their own revision
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-20'
status: proposed
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
  - The 13 docker migration tests that failed on f574d453 pass, each pinned to its own revision from an empty database, and each repaired pattern fails against a deliberately broken migration.
story: ST-SKRIPT-06-17
backlog_document_profile: contract-derived
---

## Resume here

- 2026-10-20, lead a239b10a (implementation-specialist) in worktree `skriptoteket-migration-tests-remote`, branch `codex/task-skript-migration-test-drift-remote`, base `4951dec2`. Retained root `01a1586c-edd0-77d4-a64f-fe236646aa05`: work orders in `evidence/work-orders/`, proof in `evidence/proof/`.
- Root cause named and sent to the orchestrator (mechanisms M1-M3 below). Orchestrator answers (2026-10-20): Q1, both tranches in this task, with 67c02402930c and c8a1f7e42d90 first in tranche 2; Q2, raw SQL at e7b3 replaces the resolver check; Q3, re-pin e6a9 to its revision; D3 accepted; 06-17-01 folds in here. The user approved the pre-push stage (D6); U13 and its repair U14 are integrated, with proof in `evidence/proof/lead-pre-push/`.
- Integrated and lead-reviewed (2026-10-20, commit `613fb45e`): U1-U5 (the 13), U6-U9 (tranche 2 head-copy and head tests), U13+U14 (pre-push stage). Lead findings `evidence/lead-review/findings.md` go to repair unit U15 (e6a9, 67c0, c8a1, e7b3, support module). Adversarial breaks run under `migration-break.lock` in the retained root, because a live break poisons every other run's upgrade chain.
- U10-U12, U15 and U16 integrated. The orchestrator accepted the 0016 and 0020 nullable corrections and D7 (2026-10-20).
- Domain suite (2026-10-20, orchestrator slot): `pdm run test-migrations`: 117 passed, 1 failed (`evidence/proof/domain-suite-test-migrations.log`). The failure is 4e9b7d1c6a02, out of scope here; its fix `ed269299` lives on the 41-02-06 branch. Pre-push unit tests: 8 passed.
- Review 749a17aa of `613fb45e` (changes requested, three mediums, admitted on focused proof by the orchestrator):
  - R1 (rename skips the stage) is repaired with `git diff --no-renames`.
  - R2 (a first push in pre-commit all-files mode aborted) is repaired: the hook takes the pushed local ref and runs the stage.
  - R3 is repaired by U18, which pins 4e9b7d1c6a02 on this branch.
  - Unit tests drive the real pre-commit adapter: 12 passed, red first. `pdm run test-migrations`: 118 passed (`evidence/proof/domain-suite-test-migrations-r2.log`).
- Next: the orchestrator hands the branch to the Mac.

## Implementation Contract

Thirteen `docker`-marked migration tests fail on main (observed by the 41-02-06 lead on `f574d453`, log `domain-suite-integration-base-f574d453.log` in retained root `01a1583c-81a1-70fd-9e49-fbc30a80d89f`). They fail through three mechanisms, and further passing tests carry M1 or M2 without failing (tranche 2):

- M1: the test upgrades to `head`, then seeds or asserts schema that later migrations changed. This covers 0010, 0011, 0013, 0017, 0018, 0019, 0020 and 0021, which seed `users.external_id` (dropped by `e7b3a9c4d1f2`). It also covers 0030, which asserts `sessions.allow_remote_fallback` (dropped by `c1d2e3f4a5b6`), and e6a9c2f4b8d1 `test_fresh_head_rerun_and_downgrade_delete_only_import_rows`, which asserts an index at head that `a3e7c9d1f4b6` changed.
- M2: the test runs on the module's copy of the migrated template, which is already at head, so `upgrade <parent>` does nothing and the seed meets the head schema. This covers e8f2c4a6b1d3, which fails on `exam_workspace_history.content`. 4e9b7d1c6a02 had the same bug and is repaired on the 41-02-06 branch (`ed269299`).
- M3: `migration_idempotency_support._parent_revision` raises on the merge revision `6a1e9d3c4b7f`. This was TASK-SKRIPT-06-17-01; this task absorbs its acceptance.
- e7b3a9c4d1f2 runs today's `PostgreSQLProfileRepository` and resolver against the schema at e7b3, and fails on `user_profiles.classroom_planner_smart_enabled`, which `b6c9f2a1d4e8` adds later.

Every repaired test exercises its own migration on the schema at its own revision. The test creates an empty database (`fresh_database` or `empty_module_database`) and upgrades to the parent. It seeds only columns that exist at the parent, read from the migration files and never from today's ORM models or repositories. It then upgrades to its own revision twice, asserts, downgrades to the parent, upgrades to its revision again and asserts. No repaired test names `head`.

Why the drift went unnoticed: the default pytest `addopts` deselects `docker`, and no hook or CI lane runs them. Pre-commit `migration-test-coverage` only checks statically that every revision has a test, and the only CI workflow is `docs-validate.yml`.

The pre-push stage in D6 keeps them exercised from now on.

Non-goals: changing any migration or product code; changing the default suite selection.

## Contract Inputs

- Base failure log above; reference fix `ed269299` (start from base).
- Alembic `command.upgrade` / `command.downgrade` semantics for branch and merge revisions (fetched through ctx7 before M3 work).

## Core Vertical And Performance

The vertical is one migration test file: start from an empty database, run its own revision against seeded data from the parent, and run the downgrade and re-upgrade cycle. Starting from an empty database costs one upgrade chain to the parent. That is cheaper than a full `downgrade base` from a head copy, which also runs every unrelated downgrade.

## Validation

- Adversarial check, at least once per mechanism: temporarily break the target migration's `upgrade()` and confirm that the focused test fails on the intended assertion. Then revert the migration, with `git diff --exit-code -- migrations/` clean.
- Focused: `pdm run test-sequential -m docker <file>` for each repaired file; `pdm run lint`, `pdm run typecheck`.
- Domain: every `tests/integration/test_migration_*.py` under `-m docker`, after the orchestrator gives the go.

## Stop Conditions

- A seed or assertion cannot be expressed at the test's own revision: stop and propose deletion with evidence.
- Any repair would require editing `migrations/` or product code: stop and ask the orchestrator.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                                                                                                                                                                                                  |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | Every migration test starts from an empty database and pins to its own revision and its parent; no repaired test uses `head`.                                                                                                                                                                                                                                                                                                          |
| D2  | Seeds use the parent revision's columns from the migration files; tests never use today's ORM, repositories or resolvers on an old schema.                                                                                                                                                                                                                                                                                             |
| D3  | An M2 test uses `fresh_database` plus `upgrade <parent>` instead of `downgrade base` on the head copy (same start from base, without unrelated downgrades).                                                                                                                                                                                                                                                                            |
| D4  | The merge revision is handled in the shared helper by resolving its parent revisions; no revision mapping or assertion is dropped (ST-SKRIPT-06-17 acceptance).                                                                                                                                                                                                                                                                        |
| D5  | A test that cannot be meaningful at its own revision is proposed for deletion with evidence; it is never weakened.                                                                                                                                                                                                                                                                                                                     |
| D6  | User decision 2026-10-20: the Hemma pre-push check (`scripts/hemma_pre_push_check.sh`) also runs `pdm run test-migrations` (`-m docker tests/integration/test_migration_*.py`) when the pushed range changes `migrations/versions`, a migration test or helper, or `tests/fixtures/database_fixtures.py` (`scripts/pre_push_touches_migrations.sh`); a helper error blocks the push. Other pushes and the default suite are unchanged. |
| D7  | A trailing block that upgrades to `head` and re-asserts data (d7e4b9a12c80) is removed: it checks later migrations, not the test's own revision.                                                                                                                                                                                                                                                                                       |
