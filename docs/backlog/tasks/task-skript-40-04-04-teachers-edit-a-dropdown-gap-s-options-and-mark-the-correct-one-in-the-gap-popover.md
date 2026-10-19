---
type: task
id: TASK-SKRIPT-40-04-04
title: Teachers edit a dropdown gap's options and mark the correct one in the gap popover
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: "2026-10-18"
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: ruthless-reviewer
  decided_at: '2026-10-19'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: 'Independent ruthless-reviewer e7dac097 (Pi) approved the review-1 repair F1-F5 at 471f2209 with no findings (retained 01a14c27 evidence/reviews/TASK-SKRIPT-40-04-04/review-2.md); merged to main as 36ca27c0. The D3 walk failure was repaired under TASK-SKRIPT-40-04-08 WR1 (4885c37d, review cd5a1b4c, merged be979cd7). The Mac staging walk at cf9547fa passed the owed Validation walk: blocker jump, fix, then QTI export 200 (Mac .artifacts/staging-walk-cf9547fa/walk-record.md).'
task_kind: story
acceptance_criteria:
  - A teacher opens a dropdown gap's popover, adds, edits, removes and reorders options, marks the correct one, and export blocks in red with a one-click jump while a gap has fewer than two options, an empty option or none marked correct
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

## Walk Repair

2026-10-19: done. The Mac staging walk at `cf9547fa` passed this task's Validation walk as the proof user, on a fresh import of the Svenska 2 rev11 QTI package (doc `807d5e7b`). Lucka 1 reduced to one option showed the blocker "Fråga 2: rullista med färre än två alternativ" and disabled every export. The jump focused Fråga 2, adding an option cleared the blocker, and the QTI export returned 200 (record: Mac `.artifacts/staging-walk-cf9547fa/walk-record.md`).

The staging walk on 2026-10-19 (main eba9d0f2) failed D3: the jump for "rullista med färre än två alternativ" left every gap closed and focus on the page. Root cause: `useExamWorkspaceSaveFlow.ts` opened the gap with `chip.click()`, which never reaches ProseMirror's `handleClickOn`. The repair runs under TASK-SKRIPT-40-04-08 Walk repair unit WR1 (term R1 there): the jump dispatches a bubbling DOM event on the chip, the body editor opens that gap's popover, and the popover focuses its first option input. Proof: a fail-first Vitest spec through the real jump path, then the Mac re-walk. The task stays `in_progress` until review and the re-walk pass.

## Validation

- Focused backend tests for change type and the dropdown export blockers.
- Frontend Vitest for the popover option editor, readiness and blocker focus.
- Typecheck and lint for the touched domains.
- One staging walk: a teacher fixes a dropdown gap through the blocker jump and exports QTI.

## Stop Conditions

Stop and report to the parent when a needed decision is absent, or when the popover cannot hold the option list without a layout decision.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                             |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | A dropdown gap's options are edited in the gap popover: one row per option, a radio for the correct one, add, edit, remove and reorder.                           |
| D2  | Changing a Lucktext question to dropdown turns each gap's accepted values into its options, first marked correct; imports never detect dropdowns.                 |
| D3  | Fewer than two options, an empty option or no correct option is a red export blocker with a one-click jump to that gap's popover.                                 |
| D4  | Students see options in the teacher's order in print and Exam.net; no shuffling.                                                                                  |
| D3r | The D3 jump opens the gap's popover through a bubbling DOM event on the chip and focuses its first option input (walk repair 2026-10-19, TASK-SKRIPT-40-04-08 R1) |
