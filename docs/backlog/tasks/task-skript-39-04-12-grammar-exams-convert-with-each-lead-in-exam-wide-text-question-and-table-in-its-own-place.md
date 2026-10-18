---
type: task
id: TASK-SKRIPT-39-04-12
title: Grammar exams convert with each lead-in, exam-wide text, question and table in its own place
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
  - omprov_grammatik_sve2 and exempelprov_grammatik_sve2_v2_1 convert with each question's lead-in in its own question, exam-wide text in the exam instructions once, every grouped question as one item and every table in its question, and the gold corpus results are unchanged
story: ST-SKRIPT-39-04
backlog_document_profile: contract-derived
---

## Implementation Contract

The user's grammar exams `omprov_grammatik_sve2.docx` and `exempelprov_grammatik_sve2_v2_1.docx` convert with misplaced content, although the AI grouping and the build replies are correct. This task fixes the four traced causes structurally, with each piece of text owned by its position in the document.

- C1: A question's lead-in, meaning the lines before its first numbered line, belongs to the question whose span contains it. It never lands in the next question. Today `docx_instruction_runs` starts the run inside the owning question and its span reaches the following one.
- C2: Exam-wide text governing every question, such as the "Instruktioner" box and "Kontrollera dina svar", goes into the exam instructions once. It is never copied into items and never forms a parent over all items, so part (DEL) parents form whether the DEL lines are paragraphs or Word headings. Exam metadata lines (Namn, Klass, Datum) are header metadata (TASK-SKRIPT-39-05-14) and never item text.
- C3: A question the grouping declares is admitted as one item. The lead traces why a build reply splits it into one item per numbered sentence, and why its printed points then reach none of them, and fixes the cause. A change that needs a product decision goes to the parent.
- C4: A chunk that lies between a question's first and last anchor belongs to that question. A table inside a question's span is never orphaned.

Non-goals: new question kinds; changes to the points contract of TASK-SKRIPT-39-04-11.

## Contract Inputs

- Root cause: retained root 01a14bdc, `evidence/omprov-grammatik/root-cause.md` and `trace_place.py`; reruns in `rerun/` and `../exempelprov-v2-1/rerun/`.
- Code: `docx_instruction_runs.py` and `docx_section_instructions.py` (`place_section_instructions`, `parent_groups`), plus the build admission path for C3.
- TASK-SKRIPT-39-05-14 (header lines become metadata).
- The printed-points structural rule: ownership is decided from document structure, never from AI placement or tags.

## Core Vertical And Performance

The core vertical is the offline replay of both user recordings through the production pipeline. After the fix, every item body is right. Then the gold corpus recordings are rerun unchanged, and one staging conversion of omprov is done. Performance is not material.

The bounded junior units are C1 (instruction runs), C2 (exam-wide placement) and C4 (span ownership). C3 is lead-owned.

## Validation

- Focused DOCX unit tests with adversarial cases per cause, including `1.`-style subparts, DEL as paragraphs and as headings, and a table inside a span.
- The offline replays of both user files match the expected bodies, and the gold corpus replays are unchanged.
- Lint and typecheck.
- One staging walk converting omprov_grammatik_sve2.

## Stop Conditions

Stop and report to the parent when a fix needs a product decision (for example C3's item shape), or would change 39-04-11's points ownership.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                            |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| C1  | A question's lead-in belongs to the question whose span contains it, never the next question.                                                    |
| C2  | Exam-wide governing text goes to the exam instructions once, never into items or an all-items parent; Namn, Klass and Datum are header metadata. |
| C3  | A question the grouping declares is admitted as one item; the cause of split replies is traced and fixed.                                        |
| C4  | A chunk between a question's first and last anchor belongs to that question.                                                                     |
