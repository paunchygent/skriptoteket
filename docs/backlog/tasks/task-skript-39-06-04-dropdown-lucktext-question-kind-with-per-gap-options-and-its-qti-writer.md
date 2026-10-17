---
type: task
id: TASK-SKRIPT-39-06-04
title: Dropdown Lucktext question kind with per-gap options and its QTI writer
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
  - A Lucktext question whose gaps each hold their own option list with one correct option saves through the workspace API and exports as QTI 3.0 that Exam.net imports with each gap's correct option as the key
story: ST-SKRIPT-39-06
backlog_document_profile: contract-derived
---

## Implementation Contract

Lucktext with dropdown is one of the six types this story plans (story P2).
The document model cannot hold it: `NativeGap` stores typed accepted values
only, and the QTI writer's `ExamNetQtiInteractionType` has no inline-choice
interaction. Exam.net imported dropdown Lucktext as a parent with children on
2026-10-10, and the HuleEduOS round 11 table records
`qti-inline-choice-interaction` as a keyed Lucktext gap with a selectable
list. This task adds the kind and its writer. It follows
TASK-SKRIPT-39-06-02 in order and is not gated on it. It is backend, API and
export work; it adds no workspace control (story P18).

This task delivers:

- A new `NativeExamItemKind` value for Lucktext with dropdown. Each gap holds
  its own option list and exactly one option marked as the correct key (story
  P20). The body places every declared gap exactly once, as the Lucktext body
  rule does today.
- Model validation that refuses a gap without an option list, a gap with no
  or more than one correct option, and a correct option that is not in the
  gap's list.
- The document saves and reopens through the workspace API with the new kind,
  standalone and as a child of a parent.
- A QTI writer path: each gap becomes a `qti-inline-choice-interaction` in its
  paragraph with a single identifier response, the correct option as the
  correct response, and a mapping that carries the gap's points through the
  same per-gap point values the Lucktext writer uses (`gap_point_values`).
  As a child, the item follows the parent layout, including the empty
  `SEPARATOR` gap-match before the child sentence that story P12 records for
  Lucktext children.
- The new interaction added to `ExamNetQtiInteractionType`, to the export
  rules and to the export checklist where they list kinds.

Out of scope: the controls that edit options and pick the key
(ST-SKRIPT-40-04), conversion producing this kind from DOCX, and ordering.

## Contract Inputs

- Story ST-SKRIPT-39-06 terms P2, P4, P12, P18 and P20.
- Model: `src/skriptoteket/domain/curated_apps/exam_workspace/native_exam_vocabulary.py:26`
  (`NativeExamItemKind`), `native_exam_values.py:43` (`NativeGap`),
  `native_exam_item.py` (kind, answer-key and body-gap invariants).
- Writer: `src/skriptoteket/domain/curated_apps/exam_conversion/examnet_qti_contracts.py:38`
  (`ExamNetQtiInteractionType`), `examnet_qti_xml.py`
  (`append_response_declaration`, `gap_point_values`), `examnet_qti_item_xml.py`
  (`_append_parent_item`, `_append_child_body`), and
  `src/skriptoteket/domain/curated_apps/exam_workspace/examnet_qti_export.py`.
- Proven construction: HuleEduOS `examnet-qti-import` contract, round 11 table
  row for `qti-inline-choice-interaction`.
- Evidence: the all-types import of 2026-10-10 (dropdown Lucktext parent with
  children a) and b)) and the TASK-SKRIPT-39-06-02 screenshots of its student
  view and grading.

## Core Vertical And Performance

The agent saves through the workspace API a standalone dropdown Lucktext
question with two gaps, each with three options and one correct, and a parent
with two dropdown Lucktext children. The exported package imports into
Exam.net through the teacher's browser: each gap shows its own list, the
correct option is the key, and the points match the saved document.

## Validation

- Focused domain tests: the validation refusals listed above; a valid item
  saves and reads back unchanged.
- Focused writer tests on a real saved workspace document: the standalone item
  and the parent's children write one inline-choice interaction per gap with
  the correct response and the per-gap mapping; the child carries the
  `SEPARATOR` before its sentence.
- Exam.net proof on Hemma staging: the package imported through the teacher's
  browser, with screenshots of each gap's list, the key and the points in the
  grading preview retained in the retained root's `evidence/`.

## Stop Conditions

- TASK-SKRIPT-39-06-02 shows that Exam.net's student view or grading of
  dropdown Lucktext differs from the round 11 record: report to the user
  before building the writer.
- Exam.net merges dropdown children with or without the `SEPARATOR`
  differently from the 2026-10-10 import: stop and report with screenshots.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                               |
| --- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| P1  | Lucktext with dropdown gives each gap its own option list with one correct option marked as the key (story P20, user 2026-10-17 G23).               |
| P2  | Lucktext with dropdown is one of the six types the story plans (story P2).                                                                          |
| P3  | A question is standalone or a parent with child questions of any mix of types (story P4).                                                           |
| P4  | Lucktext children export with the empty `SEPARATOR` gap-match before every child sentence (story P12).                                              |
| P5  | The Exam.net probe walks dropdown Lucktext's student view and grading; this task follows it in order and is not gated on it (user 2026-10-17).      |
| P6  | This story ships backend, data, API and export only; the current workspace screens are frozen except for bug fixes (story P18, user 2026-10-17 G2). |
