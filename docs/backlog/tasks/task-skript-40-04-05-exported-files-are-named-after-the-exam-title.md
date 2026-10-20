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
| D1  | Every export and its Mina filer copy is named after the exam title without punctuation plus the extension; all formats share that base name, with no -qti or -examnet suffix (T14). |

## Progress

### Reconciliation 2026-10-20 (Mac parent, against main 114ca971)

- Work on main through merge `2b5dcb94` (2026-10-18): export names from the exam title (`6ebfc01b`, merged at `8ad14147`) and the blank-title repair `c7226069` (a blank title saves and autosaves; only export refuses it). No review or staging walk is recorded.
- Owed: review, a staging walk of the export names, then closeout.
