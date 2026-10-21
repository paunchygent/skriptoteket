---
type: task
id: TASK-SKRIPT-40-04-05
title: Exported files are named after the exam title
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: "2026-10-18"
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
  - QTI, PDF and DOCX exports and their Mina filer copies are named after the exam title without punctuation plus the extension
story: ST-SKRIPT-40-04
backlog_document_profile: contract-derived
---

## Implementation Contract

T14 (TASK-SKRIPT-40-04-01) decided that an export's file name is the exam title without punctuation plus the extension. Today the backend names exports after the saved workspace file (`{base}-qti.zip`, `{base}-examnet.pdf`, `{base}.docx`) and never reads the title. This task makes QTI, PDF and DOCX exports, and their Mina filer copies, use the exam title without punctuation plus the format's extension, with one shared base name and no format suffix (D1).

Non-goals: an editable export file-name field; renaming the workspace document.

## Contract Inputs

- TASK-SKRIPT-40-04-01 T14.
- Current code: `exam_workspace_exports.py:105-180` (names and the Mina filer save), `apps_conversion_hub_exam_workspace.py:236-240` (Content-Disposition), `useExamWorkspaceExports.ts:84-87,255-272` (frontend fallbacks).

## Core Vertical And Performance

The core vertical is one owner that derives the export base name from the exam title. The QTI, PDF and DOCX exports and the Mina filer save use it, and the frontend fallbacks match it. Performance is not material. It is one junior unit.

## Validation

- Focused backend tests for the export names, including a title with punctuation and Swedish letters (å, ä, ö kept).
- A Vitest for the frontend fallback names.
- Lint and typecheck for the touched domains.

## Stop Conditions

Stop and report to the parent when the exam title can be empty in a saved document and no decided term covers the name.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                               |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | Every export and its Mina filer copy is named after the exam title without punctuation plus the extension; all formats share that base name, with no -qti or -examnet suffix (T14). Amended by user decision 2026-10-21: the three PDF variants of TASK-SKRIPT-40-04-07 carry a suffix after the base name: `<titel>.pdf`, `<titel> facit.pdf` and `<titel> Exam.net.pdf`; the QTI `.zip` and the `.docx` carry none. |

## Progress

### Reconciliation 2026-10-20 (Mac parent, against main 114ca971)

- Work on main through merge `2b5dcb94` (2026-10-18): export names from the exam title (`6ebfc01b`, merged at `8ad14147`) and the blank-title repair `c7226069` (a blank title saves and autosaves; only export refuses it). No review or staging walk is recorded.
- Owed: review, a staging walk of the export names, then closeout.

### 2026-10-21 (Hemma orchestrator)

- User decision 2026-10-21 (relayed by the Mac orchestrator): the PDF variant suffixes stay as main names them; D1 is amended to match. No code change.
- Mac staging walk wave 1b on `a8de9ae6` (app code equal to main `b9ad44a4`) passed: export names follow the title; a blank title and "???" both save, and export is refused with 422 `title_without_text` (Mac record `.artifacts/staging-walk-l1b-a8de9ae6/walk-record.md`).
- Review f9239f80 (2026-10-21, changes_requested, two medium findings: titles long enough to overflow the 255-character Mina filer name column, and the size of `user_vault_file_repository.py`) is held for user triage (retained root `01a15f48-0f71-77ba-b7df-f48c8e838efb`, `evidence/reviews/task-skript-40-04-05-review-f9239f80.md`).

### 2026-10-21 (repair owner, review f9239f80)

- F1 repair on branch `codex/task-skript-40-04-05` per the user's 2026-10-21 triage (cap the export base name so every export file name, including the longest ` Exam.net.pdf` variant suffix and its extension, fits within 255 characters): `export_file_base_name` in `exam_workspace_exports.py` now caps the shared base at 242 characters, so the download name and the Mina filer name stay the same; the title itself and the schema are unchanged. Focused proof: new 252-character-title boundary test (fails before with a 256-character QTI name, passes after), the existing export-name and Content-Disposition tests, `pdm run lint` and `pdm run typecheck`.
- The user's triage of 2026-10-21 accepted F2 (the 665-line `user_vault_file_repository.py`) unfixed; no decomposition was done here.
