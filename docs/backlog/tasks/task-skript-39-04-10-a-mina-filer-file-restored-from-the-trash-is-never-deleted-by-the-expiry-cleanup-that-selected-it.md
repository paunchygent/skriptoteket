---
type: task
id: TASK-SKRIPT-39-04-10
title: A Mina filer file restored from the trash is never deleted by the expiry cleanup that selected it
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-17'
status: ready
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
  - When a teacher restores a trashed Mina filer file while the expiry cleanup is deleting expired files, the file stays restored with its content, and a file the cleanup deletes cannot be restored half-deleted; exam files and their exports keep the 39-04-08 lifecycle
story: ST-SKRIPT-39-04
backlog_document_profile: contract-derived
---

## Implementation Contract

The expiry cleanup (`cleanup_vault_files.py`) selects trashed Mina filer files
past retention and then deletes their rows and payloads. Restore
(`restore_vault_file.py`) shares no lock with it for plain files, which have no
lineage. A restore that lands between selection and deletion is undone: the
cleanup still deletes the row and payload, and the teacher loses a file they
just restored. TASK-SKRIPT-39-04-08 serializes exam files and their exports by
the lineage lock and re-reads them under it; plain files have no such
serialization.

This task makes cleanup and restore serialize on the same rows for every
Mina filer file: the cleanup re-reads each selected file under that
serialization and deletes it only if it is still trashed and expired, and a
restore that wins keeps its row and payload. One mechanism covers plain files,
exam files and exports, with one lock order; the exam aggregate rule of
39-04-08 stays as it is. Payload deletion happens only for rows the cleanup
actually deleted. The Unit of Work owns commit; repositories never commit.

## Contract Inputs

- `src/skriptoteket/application/**/cleanup_vault_files.py` and
  `restore_vault_file.py` after TASK-SKRIPT-39-04-08 lands (it changes both).
- U1 evidence of the race: retained root
  `01a149c9-5bc7-7713-ba64-12dee0470bdd`, `evidence/u1-save-and-cursor-seams.md`
  and the lead message log for 2026-10-17.

## Core Vertical And Performance

A plain file is trashed and past retention. The cleanup selects it; before it
deletes, a restore commits. The cleanup then leaves the file: the row is
active and the payload is readable. In the reverse order the restore finds no
file and reports it as gone. Cleanup batches keep their current size; the
added serialization holds row locks only for the batch being deleted.

## Validation

- Focused integration tests against real PostgreSQL with two sessions, for
  both orders, for a plain file and for an exam with an export.
- The existing cleanup and restore tests stay green.

## Stop Conditions

- Serialization needs a schema change beyond row locks: report to the lead
  before adding one.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                                  |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| R1  | Cleanup and restore serialize on the same rows with one lock order for every Mina filer file; the cleanup deletes a selected file only after re-reading it as still trashed and expired (lead 2026-10-17, Boy Scout repair of a defect found in TASK-SKRIPT-39-04-08). |
| R2  | This task starts after TASK-SKRIPT-39-04-08 is on main, because both change the cleanup and restore handlers.                                                                                                                                                          |
