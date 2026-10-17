---
type: task
id: TASK-SKRIPT-39-04-08
title: One file per exam with Spara, Spara som and server-stored undo steps, and exports saved in Mina filer
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-13'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: ruthless-reviewer
  decided_at: '2026-10-17'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: 'Implementation review U1 requested changes in rounds 1 and 2 (F1-F6) and round 3 approved (evidence/reviews/u1-review-3.md; retained 01a149c9-5bc7-7713-ba64-12dee0470bdd); the parent-command seam review u2-review-2.md is approved. The walk defect U-4 (Spara after a parent command) was repaired in bc8c1071e and approved in review 4b135859 (evidence/reviews/TASK-SKRIPT-39-06-03 on Hemma). Focused runs: evidence/u1-focused.log 120 passed, u1-integration.log 22 passed, u1-lifecycle.log 25 passed, u1r2-focused.log 41 passed, u1r2-integration.log 10 passed; migration test u1-migration-storage-run.log 1 passed. Hemma staging API and Mina filer walk: evidence/staging-walk-u1-u3-1b417b64/walk.md (one file per exam, saved exports nested under it, Spara som, 10 pruned undo steps). U-4 re-walk, Spara after a part command then export then Exam.net import: evidence/staging-proof-1f9e4367/proof.md (revision 11 saved, QTI 200, Exam.net exam 5345261).'
task_kind: story
acceptance_criteria:
  - Each exam is one file in Mina filer that Spara overwrites, Spara som creates a separately edited copy under a given name with the questions, course and tags and an empty undo history, each autosave is one of at most 10 undo steps stored on the server that survive reload, reopening and Spara, and each export format is saved as one Mina filer file per exam, replaced on the next save and listed with the exam
story: ST-SKRIPT-39-04
backlog_document_profile: contract-derived
---

## Implementation Contract

Today every save of an exam writes a new immutable Mina filer row:

- `ExamWorkspaceDocumentStore.save_version` creates one `user_vault_files`
  row per revision, with `source_artifact_id`
  `documents.conversion_hub:exam-workspace:{lineage}:v{version}` and the
  partial unique index `uq_user_vault_files_document_version` on user,
  lineage and version.
- The workspace list shows the newest row per exam through
  `list_document_heads`, but Mina filer lists every active row through
  `list_for_user`, so one exam appears once per saved revision.
- `retire_version` soft-deletes a superseded row; only the conversion merge
  write in `exam_workspace_conversion_progress.py` calls it.
- `list_lineage_versions` has no production caller.
- Exports are download-only (`exam_workspace_exports.py`). There is no
  autosave and no undo history on the server.

This task delivers backend, data and API changes, plus one small Mina filer
list change outside the workspace:

- **One file per exam.** Each exam is one active Mina filer row. `Spara`
  overwrites that row's content and adjusts vault usage by the size change;
  the row keeps its id. There is no `Spara` version history. The existing
  stale-revision `CONFLICT` check (`expected_revision`) and the
  conversion-placeholder check stay, guarded by the revision counter on the
  one row.
- **Conversion writes.** The DOCX conversion's merge write overwrites the
  same row instead of adding a row and retiring the previous one.
- **Undo steps on the server.** An autosave route stores the editor's
  document as one undo step of the exam. The server keeps at most 10 steps
  per exam and prunes the oldest. Steps are not Mina filer files and do not
  change the exam file. `Spara` leaves the steps as they are, so the history
  continues past a save. The API returns the stored history and the document
  of a step, so undo and redo work after a reload and after reopening the
  exam. Reopening an exam shows its newest autosave. A new edit after an undo
  drops the redo steps. The import result is the starting point of the
  history, not an undo step. Each undo step keeps its own pictures: a picture
  asset stays stored while any undo step refers to it.
- **Spara som.** A route takes a name and the editor's current document and
  creates a new exam: its own lineage and its own file holding the questions,
  the course and the tags (tags as TASK-SKRIPT-39-08-03 defines them), with
  the pictures its questions reference, and an empty undo history. The name
  follows the Mina filer name rule the rename handler applies
  (`name_in_use`, code `vault_name_in_use`). The response returns the new
  exam's lineage and document. The original exam keeps its file and its undo
  history.
- **Exports saved in Mina filer.** A route saves one export format (QTI, PDF
  or DOCX) of the exam to Mina filer through the same export gate as the
  download route. Each exam has at most one saved file per format, linked to
  the exam's lineage; the next save of that format replaces it. The Mina filer
  list API returns each saved export with its exam, so it is listed next to
  the exam.
- **Mina filer list.** The Mina filer page (`VaultView.vue`,
  `useVaultFiles.ts`) shows each saved export with its exam. This is a small
  UI change outside the workspace, which G2 allows. TASK-SKRIPT-40-03-02
  restyles Mina filer; coordinate the list change with that task.
- **Old path deleted.** `save_version` gives way to the overwrite,
  `retire_version` and `list_lineage_versions` are deleted, the exam list no
  longer needs the `DISTINCT ON` head query, the `v{version}` suffix leaves
  `source_artifact_id`, and a unique index on user and lineage for exam files
  replaces `uq_user_vault_files_document_version`. The lineage rename in
  `rename_vault_file.py` then renames the one row.
- **Existing rows.** The migration that changes the index drops the existing
  per-version exam-workspace rows and their stored files and releases their
  bytes from vault usage. Production had 0 saved exam documents on
  2026-10-17; the staging rows are test data. No reader, backfill or
  conversion keeps them (repository invariant).
- **Landing order.** This task lands before TASK-SKRIPT-39-04-06; both change
  the stored exam document format.

Out of scope, owned by ST-SKRIPT-40-04 (G2, G14): the `Spara`,
`Spara som`, undo and redo controls, the `Ctrl+S`/`Cmd+S`,
`Ctrl+Z`/`Cmd+Z` and `Ctrl+Shift+Z`/`Cmd+Shift+Z` shortcuts, the name prompt
prefilled `<name> (kopia)`, opening the copy, and when the editor autosaves.
The exam index grouped by course is TASK-SKRIPT-39-08-04's.

## Contract Inputs

- Store and save: `src/skriptoteket/application/curated_apps/handlers/exam_workspace_document_store.py`
  (`save_version`, `retire_version`),
  `exam_workspace_documents.py` (`SaveExamWorkspaceDocumentHandler`,
  `ListExamWorkspaceDocumentsHandler`),
  `exam_workspace_conversion_progress.py` (merge write and retire).
- Mina filer: `src/skriptoteket/infrastructure/repositories/user_vault_file_repository.py`
  (`list_for_user`, `get_document_head`, `list_document_heads`,
  `list_lineage_versions`, `rename_lineage`, `name_in_use`),
  `infrastructure/db/models/user_vault_file.py`
  (`uq_user_vault_files_document_version`), `protocols/vault.py`,
  `application/scripting/handlers/list_vault_files.py`,
  `application/scripting/handlers/rename_vault_file.py`.
- Exports: `application/curated_apps/handlers/exam_workspace_exports.py`.
- Mina filer page: `frontend/apps/skriptoteket/src/views/VaultView.vue`,
  `frontend/apps/skriptoteket/src/composables/vault/useVaultFiles.ts`;
  restyle by TASK-SKRIPT-40-03-02.
- Landing order: TASK-SKRIPT-39-04-06 lands after this task.
- Routes: `src/skriptoteket/web/api/v1/apps_conversion_hub_exam_workspace.py`.
- Course and tags: TASK-SKRIPT-39-08-01 (done), TASK-SKRIPT-39-08-03.
- User decisions G2, G13, G14, G15, G16, G17, G18 and G28 and lead decisions
  L2, L3 and L4 (2026-10-17), retained in session
  `01a1495e-8398-75be-b2da-f0b08ba11afa`,
  `evidence/planning/decisions-2026-10-17.md`.

## Core Vertical And Performance

A teacher's editor autosaves twelve times; the server keeps the newest ten
steps. The teacher runs `Spara`; Mina filer lists the exam once, and the
history still has ten steps. After a reload the API returns the same history
and the previous step's document. `Spara som` with the name `Prov v.42 (kopia)` creates a second exam in Mina filer with the same questions, course
and tags and no undo steps. The teacher saves the QTI export twice; Mina
filer holds one QTI file listed with the exam. Storage per exam stays bounded:
one exam file, at most ten steps and at most one file per export format.

## Validation

- Focused backend tests: `Spara` overwrites the same row and adjusts vault
  usage; a stale `expected_revision` returns `CONFLICT`; the conversion merge
  write overwrites the same row; an eleventh autosave prunes the oldest step;
  `Spara` leaves the steps unchanged; history and step documents read the same
  in a new request; reopening returns the newest autosave; a new autosave after
  an undo drops the redo steps; the import result is not an undo step; a
  picture an undo step refers to stays stored after `Spara` removes it from
  the exam file; `Spara som` creates a new lineage with the copied
  questions, course and tags and an empty history, and a name in use is
  rejected with `vault_name_in_use`; saving an export runs the export gate and
  a second save of the same format replaces the first; the Mina filer list
  returns each exam once with its saved exports.
- Focused migration test: the migration deletes the old exam-workspace rows,
  releases their bytes and creates the new unique index.
- Focused frontend tests for the Mina filer list: each exam is listed once
  and each saved export is shown with its exam.
- Hemma staging, through the workspace and Mina filer APIs: save an exam
  twice and list it once; save the QTI export twice and list one QTI file
  with the exam.
- Hemma staging browser walk of the Mina filer page only: the exam is listed
  once with its saved QTI export.

## Stop Conditions

- TASK-SKRIPT-39-08-03 changes how tags are stored on the document: copy them
  as it defines them.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                                                                                                                                                                                 |
| --- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| M1  | `Spara` is a durable overwrite of the exam's current file; there is one file per exam in Mina filer and no `Spara` version history (G15).                                                                                                                                                                                                                                                                             |
| M2  | `Spara som` creates a separate copy that is edited on its own (G15); it takes a name, copies questions, course and tags, and starts its own empty undo history (G17).                                                                                                                                                                                                                                                 |
| M3  | Each autosave is one undo step stored on the server; at most 10 steps are kept and older steps are pruned; the history survives reload and reopening (G13).                                                                                                                                                                                                                                                           |
| M4  | The undo history continues past a `Spara` (G16).                                                                                                                                                                                                                                                                                                                                                                      |
| M5  | Exports saved to Mina filer are one file per format per exam, replaced on the next save and shown next to the exam (G18).                                                                                                                                                                                                                                                                                             |
| M6  | This task ships backend, data and API plus the small Mina filer list change (M13); controls, the prefilled name prompt, opening the copy and the keyboard shortcuts are ST-SKRIPT-40-04's (G2, G14, G17; amended lead 2026-10-17, L3).                                                                                                                                                                                |
| M7  | The per-revision row format and its code path are deleted, not kept beside the new format; existing saved exams are test data and are dropped (CLAUDE.md repository invariant; `exam_workspace_document_store.py`, `user_vault_file_repository.py`).                                                                                                                                                                  |
| M8  | Reopening an exam shows its newest autosave (user 2026-10-17, G28).                                                                                                                                                                                                                                                                                                                                                   |
| M9  | A new edit after an undo drops the redo steps (user 2026-10-17, G28).                                                                                                                                                                                                                                                                                                                                                 |
| M10 | The import result is the starting point of the undo history, not an undo step (user 2026-10-17, G28).                                                                                                                                                                                                                                                                                                                 |
| M11 | Undo steps keep their own pictures, so a picture asset stays stored while any undo step refers to it (user 2026-10-17, G28).                                                                                                                                                                                                                                                                                          |
| M12 | The migration drops the per-version exam rows; production had 0 saved exam documents on 2026-10-17 and the staging rows are test data (lead 2026-10-17, L2).                                                                                                                                                                                                                                                          |
| M13 | This task also changes the Mina filer list so saved exports show with their exam; it is a small UI change outside the workspace, allowed by G2, coordinated with TASK-SKRIPT-40-03-02, which restyles Mina filer (lead 2026-10-17, L3).                                                                                                                                                                               |
| M14 | This task lands before TASK-SKRIPT-39-04-06; both change the stored exam document format (lead 2026-10-17, L4).                                                                                                                                                                                                                                                                                                       |
| M15 | An export is active only while its exam is active: trashing the exam trashes its exports, trashing one export leaves the exam, restoring the exam restores the exports trashed with it, restoring an export whose exam is trashed restores the exam too, and permanently deleting the exam deletes every export payload; Mina filer lists exports only under their exam (lead 2026-10-17, L9, delegated by the user). |
| M16 | Autosave and the parent commands of TASK-SKRIPT-39-06-03 share one history cursor as their concurrency guard; it changes on every history, conversion and `Spara` change, and `Spara` keeps the file's `expected_revision` guard (lead 2026-10-17, L8).                                                                                                                                                               |
