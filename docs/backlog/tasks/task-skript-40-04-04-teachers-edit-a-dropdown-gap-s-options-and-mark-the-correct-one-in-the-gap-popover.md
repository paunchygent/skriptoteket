---
type: task
id: TASK-SKRIPT-40-04-04
title:
  Teachers edit a dropdown gap's options and mark the correct one in the gap
  popover
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: "2026-10-18"
status: ready
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
  - A teacher opens a dropdown gap's popover, adds, edits, removes and reorders options,
    marks the correct one, and export blocks in red with a one-click jump while a gap
    has fewer than two options, an empty option or none marked correct
story: ST-SKRIPT-40-04
backlog_document_profile: contract-derived
---

## Implementation Contract

Under W14 each dropdown Lucktext gap has its own option list with one correct option, but no workspace screen shows it. This task adds the editor. Clicking a gap chip opens the existing gap popover, which lists one row per option with a radio for the correct one, and lets the teacher add, edit, remove and reorder options (D1). Each edit is an undoable autosave step.

When a fill-in (Lucktext) question changes type to dropdown, each gap's accepted values become its options and the first is marked correct (D2). Imports never detect dropdown gaps.

A gap with fewer than two options, an empty option or no option marked correct is a red export blocker before the click, with formats disabled and a one-click jump that opens that gap's popover (D3). The server rule and the workspace readiness mirror match exactly. Print and Exam.net show options in the teacher's order (D4).

Non-goals: AI detection of dropdowns in imports; option shuffling.

## Contract Inputs

- TASK-SKRIPT-40-04-03 terms W2 and W14.
- TASK-SKRIPT-39-06-04 (the dropdown kind and its QTI writer).
- TASK-SKRIPT-39-05-07 D1/D2 (export blocker rules).
- Current code: `NativeGap.options` / `correct_option_id` (`native_exam_values.py:53-55`); `ExamWorkspaceGapPopover.vue` (edits only accepted values); `native_exam_change_type.py:100-105`; `native_exam_export_rules.py:73,96-104`; `examWorkspaceItemReadiness.ts:118-132`; `examWorkspaceBlockers.ts:62-86,155-160`.

## Core Vertical And Performance

Core vertical, in this order:

1. The gap popover's option editor, with edits through the document edit path, so autosave history applies.
2. Change type from gap fill to inline choice, seeding options from accepted values.
3. The server blocker rule plus the readiness mirror and a popover jump.
4. Teacher-ordered options in the QTI, PDF and DOCX writers.

Performance is not material. The bounded junior units are the popover editor, the change-type seed, and blockers plus mirror. The lead integrates.

## Validation

- Focused backend tests for change type and the dropdown export blockers.
- Frontend Vitest for the popover option editor, readiness and blocker focus.
- Typecheck and lint for the touched domains.
- One staging walk: a teacher fixes a dropdown gap through the blocker jump and exports QTI.

## Stop Conditions

Stop and report to the parent when a needed decision is absent, or when the popover cannot hold the option list without a layout decision.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                             |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | A dropdown gap's options are edited in the gap popover: one row per option, a radio for the correct one, add, edit, remove and reorder.           |
| D2  | Changing a Lucktext question to dropdown turns each gap's accepted values into its options, first marked correct; imports never detect dropdowns. |
| D3  | Fewer than two options, an empty option or no correct option is a red export blocker with a one-click jump to that gap's popover.                 |
| D4  | Students see options in the teacher's order in print and Exam.net; no shuffling.                                                                  |
