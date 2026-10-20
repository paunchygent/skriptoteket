---
type: task
id: TASK-SKRIPT-41-02-06
title: A saved exam the app cannot read is offered for download or removal
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-20'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
  - A saved exam whose format version is below the oldest readable version shows in the Öppna list as a row that cannot be opened, with one line stating that, and glyph-only download and remove actions named in tooltip and aria-label
  - Clicking such a row opens nothing, sends no open request and shows no error
  - Download saves the stored file unchanged, the exam and its pictures in one zip, for a saved exam and for a guest draft
  - Remove moves the saved exam to the papperskorg like any other Mina filer delete; nothing is deleted automatically
  - One code constant names the oldest readable format version; every stored document below it is unreadable, and every version from it up to the current one is read through the upgrade chain
  - A safeguard test fails when the current format version is raised without an upgrade step and a sample file for each version from the oldest readable one up to the current one
story: ST-SKRIPT-41-02
backlog_document_profile: contract-derived
---

## Resume here

- 2026-10-20, lead 2203a0c2 (retained root `01a1583c-81a1-70fd-9e49-fbc30a80d89f`), branch
  `codex/task-skript-41-02-unreadable-exam-files-remote` from `f574d453`.
- Done: code map (explorers e01-e22 in the root's `discovery/explorer/`), ledger D1-D16 below.
- Orchestrator accepted the ledger, the backfill (D7) and copy S1-S6 on 2026-10-20; D15 became the
  last unit U5.
- Committed: U1 format versions and safeguard (`3d87b9ef`, `330fe2ae`); U2 index column,
  migration `74adf10e2441` and unreadable route (`c931d6ee`); U3 shared file notice and guest zip
  (`a7edf784`); U6 Boy Scout repair of the `4e9b7d1c6a02` migration test (`ed269299`); U4 drawer
  rows with U4b view-spec mocks (`71330b6a`).
- Committed after U4: U7 per-row busy guard for the unreadable rows (repair of U4).
- Backend domain suite at `92942fd1`, accepted by the orchestrator on 2026-10-20: unit 5780
  passed; integration 168 passed and 13 failed. The same 13 old migration tests also fail at the
  branch base `f574d453` (schema drift in their seed data). The orchestrator routed them to a
  separate repair (assignment `a239b10a`, branch `codex/task-skript-migration-test-drift-remote`);
  this task does not touch them. Logs: the root's `evidence/proof/domain-suite-*.log`.
- Running: U8 component-rendered screenshots for copy review.
- Next: copy review with screenshots and the string inventory (root
  `evidence/copy-review/`); domain suite on the orchestrator's go; U5 deep link waits until the
  orchestrator reports the 40-04 address and open repair on main.
- Work orders in the root's `work/orders/`; proof logs in the root's `evidence/proof/`.

## Implementation Contract

Root cause. `parse_native_exam_document`
(`domain/curated_apps/exam_workspace/native_exam_document_json.py:36`) accepts exactly the
current `schema_version` and raises 422 `DOCUMENT_SCHEMA_OUTDATED` for anything else. The saved
list (`exam_workspace_saved_index.py`) reads only `exam_index` and `user_vault_files` metadata, so
it cannot tell a readable exam from an unreadable one. `ExamWorkspaceOpenDrawer.openEntry`
(`ExamWorkspaceOpenDrawer.vue:147-156`) emits `open` for every row, and the open path shows the
toast `OPEN_OUTDATED_COPY` (`useExamWorkspaceDocument.ts:218`). The teacher can neither open such
an exam nor keep or remove it from the workspace.

This task changes four things:

1. **Format versions and the upgrade chain (domain).** One module holds the oldest readable
   format version, the version number of the current format and an ordered, empty registry of
   upgrade steps. `parse_native_exam_document` reads the stored `schema_version`: a value below
   the oldest readable version, above the current one or not of the form
   `native_exam_document_v<N>` raises `DOCUMENT_SCHEMA_OUTDATED`; a value from the oldest readable
   version up to the current one runs the upgrade steps in order and then validates. Every reader
   of a stored document (container, undo-history steps, guest draft requests, public exports)
   goes through this one function.
2. **Readability in the index.** `exam_index` gains `document_format_version`, written on every
   save, and backfilled once by the migration from each head file's `document.json`. The saved
   list returns only readable exams; a new route lists the unreadable ones.
3. **Download and remove in the Öppna list.** The drawer loads the unreadable exams itself and
   shows each as a row with the shared file notice: download through the existing vault download
   route (the stored `.provdokument.zip`, unchanged), remove through the existing vault delete
   (to the papperskorg).
4. **One notice, one complete download.** The guest-draft notice becomes the shared file notice,
   and the guest download becomes one zip with the stored draft record and its picture bytes.

## Contract Inputs

- Assignment 2203a0c2 from the Hemma orchestrator 944b5a5a, 2026-10-20, carrying the user decision
  of the same day (items 1-5: one rule, Mina filer row, complete download, one setting, the
  safeguard test and a short ADR).
- TASK-SKRIPT-41-02-05 (done, main `8be9aefa`): the guest notice, its download and D10.
- Explorer maps e01-e22 in the retained root `discovery/explorer/`.
- Orchestrator acceptance of D1-D16, the backfill and copy S1-S6, 2026-10-20 (D15 changed to a last unit).
- Policy note: ADR-SKRIPT-0093.

## Copy

| ID  | Where                           | String                                                                                                               |
| --- | ------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| S1  | State line of an unreadable row | Provet är sparat i ett äldre format och kan inte öppnas. Ladda ner det som en fil eller ta bort det från Mina filer. |
| S2  | Remove tooltip and aria-label   | Ta bort provet från Mina filer                                                                                       |
| S3  | Download tooltip and aria-label | Ladda ner provet som fil (existing, approved)                                                                        |
| S4  | Remove success toast            | Provet flyttades till papperskorgen.                                                                                 |
| S5  | Remove failure toast            | Det gick inte att ta bort provet. Försök igen.                                                                       |
| S6  | Download failure toast          | Det gick inte att ladda ner provet. Försök igen.                                                                     |

The unreadable-list load failure reuses "Det gick inte att hämta dina sparade prov.". S1-S6 go to
ui-copy review with component-rendered screenshots and a string inventory before code review.

## Core Vertical And Performance

The list stays one indexed query; readability is a column comparison, with no file read per row.
The unreadable list is the same query with the opposite predicate. The migration reads each head
file once. The guest zip is built in the browser from bytes already held there.

## Validation

- Backend focused: the safeguard test, `test_native_exam_document.py`, the migration test, the
  index repository and saved-index handler tests, the unreadable-list route test.
- Frontend focused Vitest: the file notice spec, the guest controller spec,
  `ExamWorkspaceTeacherHost.spec.ts`, the unreadable-files composable spec and the open drawer spec.
- `lint`, `typecheck`, `fe-type-check`, `fe-lint`, `fe-build`; one domain suite on the
  orchestrator's go.
- Copy: the new strings go to the orchestrator first, then to ui-copy review.
- Fail-first: each unit's new tests are run before its implementation and the failing run is kept
  in the root's `evidence/fail-first/`.

## Stop Conditions

Stop and report in any of these cases:

- the work needs a change to `useExamWorkspaceHistory*`, `useExamWorkspaceDocument*`,
  `useExamWorkspaceSyncGate*`, the edit lease files, `examWorkspaceSyncFence*` or
  `examWorkspaceFencedTransport*` (the 40-04 gap lane owns them);
- the migration cannot read the head files where it runs;
- a saved exam's file and its undo history hold different format versions on staging.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | Root cause as stated in the Implementation Contract: a strict equality gate, a list without readability, and a drawer row that always opens.                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| D2  | The oldest readable version is a code constant `OLDEST_READABLE_NATIVE_EXAM_DOCUMENT_VERSION` in `domain/curated_apps/exam_workspace/native_exam_document_versions.py`, an `int`, today 10, equal to the current version. It is not an environment setting: raising it is one reviewed code edit, and the safeguard test pins it.                                                                                                                                                                                                                                                                                |
| D3  | Version numbers are parsed from `schema_version` with a full match of `native_exam_document_v(\d+)`. The current version number is derived from `NATIVE_EXAM_DOCUMENT_SCHEMA_VERSION`.                                                                                                                                                                                                                                                                                                                                                                                                                           |
| D4  | Upgrade steps live in one ordered registry in the same module, keyed by the version they read; each step takes the JSON object of version N and returns the JSON object of version N+1. The registry is empty today. Steps operate on `dict[str, object]`; no `Any`.                                                                                                                                                                                                                                                                                                                                             |
| D5  | `parse_native_exam_document` is the one reader: missing `schema_version` stays `VALIDATION_ERROR`; a version outside `[oldest, current]` or of another form is `DOCUMENT_SCHEMA_OUTDATED` with `details.schema_version`; a version inside runs the chain, then validates against the current model.                                                                                                                                                                                                                                                                                                              |
| D6  | Samples live in `tests/fixtures/exam_workspace/document_versions/native_exam_document_v<N>.json`, one per version from the oldest readable one up to the current one, today only v10. The safeguard test fails unless: oldest ≤ current; the registry keys equal `range(oldest, current)`; a sample exists for every version in `[oldest, current]` and no other; every sample parses through `parse_native_exam_document` into the current model.                                                                                                                                                               |
| D7  | `exam_index.document_format_version` is an `INTEGER NOT NULL`. Every `ExamIndexRepository.upsert` writes the saved head document's version. The migration backfills each existing row from its head file, read at `VAULT_ROOT/<owner_user_id>/<head_vault_file_id>` as migration `4e9b7d1c6a02` reads that root: the version number of `document.json`'s `schema_version`, or 0 when the file is missing, is not a zip, or has no parsable version. 0 is below every readable version, so such an exam is listed as unreadable. A migration test covers a readable file, an old-version file and a missing file. |
| D8  | Readable means `oldest ≤ document_format_version ≤ current`. `list_for_owner` returns readable exams only; `list_unreadable_for_owner` returns the rest with the same join and filters.                                                                                                                                                                                                                                                                                                                                                                                                                          |
| D9  | New route `GET /api/v1/apps/{APP_ID}/exam-workspace/unreadable-documents`, conversion-hub access as the list route, returns `documents: [{lineage_id, vault_file_id, name, title, saved_at}]`, newest first. `ExamWorkspaceDocumentSummary` and the saved-list response are unchanged, so the 40-04 files are untouched.                                                                                                                                                                                                                                                                                         |
| D10 | Mina filer download reuses `GET /api/v1/vault/files/{vault_file_id}/download`: the stored head file `<titel>.provdokument.zip` (manifest, `document.json`, `assets/<asset_id>`), byte for byte, with no parse. No new download route.                                                                                                                                                                                                                                                                                                                                                                            |
| D11 | Remove reuses `POST /api/v1/vault/files/{vault_file_id}/delete`: one click, no confirm (as 41-02-05 D11), the exam moves to the papperskorg and follows its retention like every other Mina filer file. The drawer then reloads the unreadable list.                                                                                                                                                                                                                                                                                                                                                             |
| D12 | The guest download (41-02-05 D9, D10) becomes one zip `<titel>.zip` with `draft.json` (the stored draft record, unchanged) and `assets/<asset_id>` (the stored picture Blobs, unchanged), built with `fflate` `zipSync`. The two zips differ inside because the stored things differ; neither converts anything. This closes D10 of 41-02-05.                                                                                                                                                                                                                                                                    |
| D13 | `ExamWorkspaceGuestHandoffNotice.vue` becomes `ExamWorkspaceFileNotice.vue` with `reason: "guest_permanent" \| "guest_vault_full" \| "saved_unreadable"`; its copy file maps each reason to the state line and the remove name. The guest host and the drawer render the same component.                                                                                                                                                                                                                                                                                                                         |
| D14 | The drawer loads the unreadable exams through its own composable `useExamWorkspaceUnreadableFiles` when it mounts and after each remove; it renders them after the saved list as rows that are not buttons, each with the title and the file notice. A failed load shows the existing list failure toast.                                                                                                                                                                                                                                                                                                        |
| D15 | A deep link to an unreadable exam goes through `useExamWorkspaceAddress` → `openDocument` (40-04-owned) and shows the outdated toast. It is fixed in the last unit (U5): once the 40-04 gap lane is on origin/main, main is merged into this branch and the deep link lands on the same download-or-remove state with no toast. Until then those files are untouched. Undo-history steps are read through the same parser; a file whose head is readable but whose history holds a step below the oldest readable version can only arise after a future raise and is a follow-up then.                           |
| D16 | Policy note ADR-SKRIPT-0093 records the rule, the upgrade-step contract, the constant and the safeguard test, accepted on the user decision of 2026-10-20 (`agent-planning:user-closure-gate`).                                                                                                                                                                                                                                                                                                                                                                                                                  |
