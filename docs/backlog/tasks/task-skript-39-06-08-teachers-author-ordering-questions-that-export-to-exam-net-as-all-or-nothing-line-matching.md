---
type: task
id: TASK-SKRIPT-39-06-08
title: Teachers author ordering questions that export to Exam.net as all-or-nothing line matching
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
  - A teacher creates or converts a standalone ordering question in the workspace editor, and its QTI export imports into Exam.net as all-or-nothing line matching worth 1 point by default
story: ST-SKRIPT-39-06
backlog_document_profile: contract-derived
---

## Implementation Contract

Teachers author standalone ordering questions in the exam workspace editor. A teacher writes the steps in the correct order; that list order is the answer key (D1). Each print shows the steps in one saved shuffled order with a number box per step, so every print and preview matches (D2, D5). A "Blanda om" button on the question draws a new saved order. The edit is one autosave history step and undoable (D5). With two or more steps, no drawn order equals the key order (D6).

A teacher adds an ordering question from the new-question menu, or changes an existing question's type to ordering. Changing from single or multiple choice keeps the option texts as steps (D3). Imports never detect ordering questions (D3). Ordering questions are standalone only; ordering inside a part belongs to a separate task (D4, story P3).

Grading is all-or-nothing with a default of 1 point, which the teacher can edit (story P21). The QTI 3.0 export writes a `qti-order-interaction` that Exam.net imports as "Matcha ihop": steps on the left, positions 1..N on the right, one all-correct rule (probe 39-06-02).

An ordering question with fewer than two steps, or with an empty step, is a red export blocker. It shows before the click with the export formats disabled, and one click jumps to the step to fix (D7). The server rule and the workspace readiness mirror match exactly.

Non-goals: ordering inside parts; partial credit; AI detection of ordering in imported documents.

## Contract Inputs

- ST-SKRIPT-39-06 decisions P3 and P21.
- TASK-SKRIPT-39-06-02 probe: Exam.net exam 5345282 and its retained PROBE.md.
- TASK-SKRIPT-39-05-07 D1/D2 export-blocker rules.
- Current code: `NativeExamItemKind` (`native_exam_vocabulary.py`), `NativeExamItem` shape and key checks, `change_item_type`, `examnet_qti_leaf_items.py`, PDF and DOCX kind branches, `native_exam_export_rules.py`, the workspace readiness and blocker modules, and `useExamWorkspaceHistory.ts`.

## Core Vertical And Performance

Core vertical, in this order:

1. Domain: an `ordering` kind with steps and a saved print order, its shape rules, and a key derived from list order.
2. Change type.
3. Export blocker reasons.
4. QTI order interaction.
5. PDF and DOCX print with number boxes plus a facit line.
6. Workspace editor: new-question menu, steps editor, "Blanda om", readiness mirror and blocker jump.

The first proof is one question authored in the editor, exported as QTI and imported into Exam.net.

Performance is not material, because each question has only a few steps.

Bounded units for juniors:

- the domain kind and rules;
- the QTI writer;
- the PDF/DOCX branches;
- the editor component.

The lead owns the print-order model and integration.

## Validation

- Focused backend tests for the domain item rules, change type, export blockers and QTI order XML. One adversarial test asserts that a draw never equals the key order, for 2 to 6 steps.
- PDF and DOCX ordering render tests.
- Frontend Vitest for the readiness mirror, the blocker focus and the ordering editor.
- Typecheck plus lint for the touched domains.
- One staging walk:
  1. author one ordering question;
  2. click "Blanda om" and undo it;
  3. export QTI;
  4. import it into Exam.net in the user's Edge;
  5. confirm "Matcha ihop" with all-or-nothing grading at 1 p.

## Stop Conditions

Stop and report to the parent in any of these cases:

- Exam.net does not import the exported `qti-order-interaction` as all-or-nothing line matching.
- The print-order model needs a decision that is not recorded here.
- The work would touch ordering inside parts.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                      |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | The order of the steps in the editor list is the answer key.                                                                                                               |
| D2  | Print shows the steps shuffled with a number box per step; the teacher can reshuffle at any time.                                                                          |
| D3  | Teachers create an ordering question new or by changing type; changing from a choice question keeps option texts as steps; imports never detect ordering.                  |
| D4  | Ordering questions inside a part are out of scope; a separate task covers them.                                                                                            |
| D5  | The shuffled order is saved with the exam; a "Blanda om" button draws a new order, undoable through autosave history.                                                      |
| D6  | With two or more steps, a shuffle never yields the answer-key order.                                                                                                       |
| D7  | Fewer than two steps or an empty step is a red export blocker before the click, formats disabled, with a one-click jump to the step.                                       |
| P3  | Ordering questions are standalone only (story ST-SKRIPT-39-06).                                                                                                            |
| P21 | Grading is all-or-nothing with a default of 1 point the teacher can edit (story ST-SKRIPT-39-06).                                                                          |
| D8  | Exports always print their added words in Swedish (Fråga, Lucka, Bild, Poäng, Rätt svar, Rätt ordning); user decision 2026-10-18, supersedes TASK-SKRIPT-39-05-03 D18/D21. |

## Progress

### T1 repair 2026-10-21 (tail review `e88796c5`, user-triaged medium quick fix)

- Repaired finding T1 in `frontend/apps/skriptoteket/src/views/apps/exam-workspace/useExamWorkspaceHistory.ts`: a structural flush (`flushOutcomeInner` with `structural = true` from `noteEdit`) drains owed snapshots at once but leaves a working copy whose typing pause still runs until the pause, so the burst keeps its pause and one-step undo grouping; the `flushNewer` acknowledgement hook likewise leaves newer typing to a running pause instead of queueing an eager store. Explicit flush, undo, departure, retry and settle paths still force the working-copy store.
- Added `useExamWorkspaceEditing.typingBurstUndo.spec.ts`: type B, add an ordering step, type C at 10 ms, assert only the two owed steps exist at 200 ms, extend to CD, assert 3 steps after the pause, and assert one undo restores the pre-burst body (first step `B`, second step empty). The spec fails before the fix (premature `C` step) and passes after.
- Proof: the new spec, the existing `typingPause`/`ordering`/`history`/`structuralRetry` editing specs and the `useExamWorkspaceHistory.*` plus loader specs (69 tests passed), `pdm run fe-type-check` and `pdm run fe-lint`. Logs under the repair session's `evidence/t1-fix/`.
- Task status unchanged; no rereview claimed here — the parent owns review closeout.

### Reconciliation 2026-10-20 (Mac parent, against main 114ca971)

- Work on main through merge `bacdd0d0` (2026-10-18, typing-pause undo fix). Review-1 F1-F4 and review-2 F1 repairs are named in commit subjects; no verdict is recorded here.
- Owed: the staging walk with the Exam.net import (Validation), not recorded as run; then closeout. TASK-SKRIPT-39-06-09 waits on this task.
