---
type: task
id: TASK-SKRIPT-40-04-24
title: A Word import whose question has only a points heading converts instead of crashing
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-21'
status: ready
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
  - When the grouping gives a question only a points-bearing heading, the DOCX import converts the exam, with that question kept, instead of raising IndexError in question_families
story: ST-SKRIPT-40-04
backlog_document_profile: contract-derived
---

## Implementation Contract

Found by the TASK-SKRIPT-39-10-01 lead on 2026-10-21 in a replay probe. When the AI grouping gives a question only one anchor, and that anchor is a points-bearing heading such as "Vocabulary Matching (9 points)", `assign_points_lines` moves the heading away. The question then has no anchors, and `question_families` (`domain/curated_apps/exam_workspace/docx_batches.py`, `positions[q.anchors[0]]`) raises `IndexError`. That is not a validation error, so the whole import fails. Real model output for a Word file can do the same.

The repair makes this case convert: the question is kept and placed at its heading, and no exception escapes. The fix is the smallest one in the existing code: either the points-line assignment leaves a heading that is a question's only anchor with that question, or the family builder handles a question with no remaining body anchor. Map the existing code first; the 40-04-23 change to `docx_points_lines.py` (heading values over one question) is on main.

Non-goals: other grouping defects, PDF reading (TASK-SKRIPT-39-10-01), prompt changes.

## Contract Inputs

- The 39-10-01 lead report: retained root `01a1605d-572d-70b4-aa95-dc8d05125933`, `evidence/report-39-10-01.md` (recorded questions q24 and q47 with only `body:0053` and `body:0123`).
- `docx_points_lines.py`, `docx_batches.py`, `application/curated_apps/handlers/exam_workspace_docx_pipeline.py:215`.

## Core Vertical And Performance

A manifest whose question holds only a points-bearing heading goes through `assign_points_lines` and `question_families`, and the pipeline builds the exam with that question present. No performance change.

## Validation

- A fail-first focused test with a manifest shaped like the recorded case: it raises `IndexError` before the fix, and after it the question is present with its points.
- The neighbouring DOCX points and batches tests, lint and typecheck.

## Stop Conditions

Stop and report if keeping the question needs a prompt change, a manifest schema change or a change to which lines count as points headings.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                             |
| --- | --------------------------------------------------------------------------------------------------------------------------------- |
| R1  | Light route (user rule 2026-10-21): one junior unit with a focused fail-first test, admitted on that proof with no review rounds. |
| R2  | The question is kept and placed at its points heading; the import never fails on this shape.                                      |

## Progress

### Repair 2026-10-21 (branch codex/task-skript-40-04-24)

- Kept the heading-only question: `assign_points_lines` no longer joins a question's only anchor to another question, so the question stays at its points heading and `question_families` converts instead of raising `IndexError`. Proof: `test_docx_points_heading_only_question.py` (fail-first `IndexError` at `docx_batches.py:84`, then 2 passed), 172 neighbouring domain plus 230 handler/application tests passed, lint/typecheck/docs-validate exit 0.
