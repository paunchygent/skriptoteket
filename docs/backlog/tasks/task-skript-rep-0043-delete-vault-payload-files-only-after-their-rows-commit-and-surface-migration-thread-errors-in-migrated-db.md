---
type: task
id: TASK-SKRIPT-REP-0043
title: Delete vault payload files only after their rows commit and surface migration-thread
  errors in migrated_db
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-18'
status: ready
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
- A purge whose row commit fails leaves every payload file in place, and a migration
  error inside the migrated_db fixture fails the test setup with that error
backlog_document_profile: contract-derived
---

## Implementation Contract

Two defects found during the wave-2 closeout reviews (2026-10-17).

- **Vault purge order.** `purge_expired_vault_files` deletes each payload file
  (`storage.delete_file`) inside the unit of work, before the group's row
  deletion commits (`cleanup_vault_files.py:114-126`). When the commit fails,
  the rows survive and point at files that are gone. After this task, a group
  first deletes and commits its rows, and only then deletes its payload files.
  A failed file deletion is logged with the file id and owner, and leaves an
  orphaned file, never a row without its file. The group's byte recomputation
  and the restore race guard (TASK-SKRIPT-39-04-10) keep working.
- **Migration errors in tests.** The `migrated_db` fixture runs
  `alembic upgrade head` in a thread and ignores the thread's exception
  (`tests/fixtures/database_fixtures.py:86-101`), so a failed migration shows
  up later as unrelated test failures. After this task, the fixture re-raises
  the migration's exception after `join`, so test setup fails with that error.

## Contract Inputs

- `src/skriptoteket/cli/commands/cleanup_vault_files.py` and its tests.
- `tests/fixtures/database_fixtures.py`.
- TASK-SKRIPT-39-04-10, the restore-versus-expiry guard that must keep holding.

## Core Vertical And Performance

The purge runs in the real cleanup command against PostgreSQL. No
performance concern: the same work runs in a different order.

## Validation

- An adversarial test where the row commit fails: every payload file of the
  group is still present, and the rows are still there.
- A test where a file deletion fails after the commit: the rows are gone, the
  failure is logged, and the purge continues with the next group.
- The existing cleanup and restore-race tests pass.
- A test where `migrated_db`'s migration raises: setup fails with that
  exception.
- `pdm run lint`, `pdm run typecheck` and the focused tests.

## Stop Conditions

- Stop if the restore guard of TASK-SKRIPT-39-04-10 needs the file deletion
  inside the transaction.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| D1 | A purge group deletes payload files only after its row deletion commits; a failed file deletion is logged and leaves an orphaned file, never a row without a file. |
| D2 | `migrated_db` re-raises the migration thread's exception after join. |
