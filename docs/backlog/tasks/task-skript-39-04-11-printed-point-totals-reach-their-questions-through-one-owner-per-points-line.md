---
type: task
id: TASK-SKRIPT-39-04-11
title: Printed point totals reach their questions through one owner per points line
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
- Replaying the recorded Svenska 2 conversion gives 24 questions and 36 points with
  the exam total 36, whether the grouping tags the Del 1 heading as a part total or
  an instruction and whether it tags the per-question points lines
story: ST-SKRIPT-39-04
backlog_document_profile: contract-derived
---

## Implementation Contract

A DOCX import gives the same point totals whichever way the AI grouping tags
the lines that print them. Today the totals depend on those tags. On the
Svenska 2 exam, the grouping's tags decide between 36 and 21 points, and
between an exam total of 36 and none (replay of the recorded conversion,
retained `01a14bdc-65b7-73e1-a8ee-3c75001a36fa` `evidence/carried/`). The
causes are three code defects, which this task fixes at their source with no
fallback paths (user 2026-10-17):

- **Part totals take one path (D1).** A part heading that prints one total,
  such as "Del 1: litteraturhistoria, 15 poäng", splits that total over the
  part's questions that print no points, marked as estimated (D38, D6). This
  holds whether the grouping tags the heading as a part total or as an
  instruction.
  - Today a `part_total` tag removes the heading from the chunks the split
    sees (`exam_workspace_docx_build_state.py:303`).
  - `apply_header` then only sets `parent.printed_total`
    (`docx_header.py:110-117`), so questions 1-15 get no points.
  - After this task both tags reach the same split, and the parent still
    records its printed total.
- **One owner per points line (D2).** A points line after a question, such as
  "Poäng: 2 poäng", belongs to that question in all three stages: batching
  (`docx_batches.py:104-109`), AI-reply admission (`admission.py:361-373`,
  where the question's own chunks are chosen for `with_printed_points`) and
  the section split's member spans (`docx_section_points.py`). One shared rule
  decides it. The line never becomes a separate question or review item, and
  the question takes its printed points.
- **Code owns the exam total (D3).** `header.printed_total` is read from the
  one total line printed before the first question, such as "Total: 36 poäng".
  The grouping prompt, schema and manifest no longer have an `exam_total` kind.
  With no such line, or with two different totals, the total stays empty.
- **Dead configuration goes (D4).** The never-sent `temperature` of the DOCX
  conversion profile is deleted. OpenAI rejects temperature when the reasoning
  effort is not `none`, and this profile runs at `low`.

Out of scope (D5): variation in how the grouping splits the exam into parts,
and in question kinds.

## Contract Inputs

- Recorded conversion:
  `tests/fixtures/exam_conversion/docx_key_provenance_v14/svenska_2_kursavslutande_prov_med_facit/`,
  replayed through `build_replay(exam, root=tmp_path)` with a rewritten
  `docx_grouping_1.json` (pattern: `test_exam_workspace_docx_build.py:136-151`).
- Source fixture: `tests/fixtures/exam_conversion/docx_corpus/svenska_2_kursavslutande_prov_med_facit.docx`.
  It prints "Total: 36 poäng" (body:0004, paragraph style), the Del 1-3
  headings with 15, 16 and 5 points (Heading 2), "Poäng: 15 poäng" after Del 1,
  and one "Poäng: N poäng" line after each Del 2 and Del 3 question.
- Replay outcomes before this task (retained `evidence/carried/replay-probe.py`):

  | Case | Change to the grouping | Result |
  | --- | --- | --- |
  | A | baseline | 25 items, 37 p, no total |
  | B | Del 1 heading tagged `part_total` | items 1-15 get no points, 22 p |
  | C | `exam_total` anchor added | total 36 |
  | D | `question_total` anchor on each points line | 24 items, 36 p |
  | E | B, C and D together | 21 p, total 36 |

- Existing rules to reuse: `POINT_LABEL`, `points_line` and `printed_points` in
  `docx_source_rules.py`.

## Core Vertical And Performance

The core vertical is the real conversion pipeline: chunker, grouping,
batching, admission, section split, header application and the published
document. It is exercised through the replay of the recorded Svenska 2
conversion, and through one import on staging (D6). No AI call is added, and
the changes are linear passes over the chunks, so there is no material
performance concern.

Bounded units:

1. The shared points-line owner, used by batching, admission and the split (D2).
2. `part_total` headings feed the section split (D1).
3. The code-owned exam total, and removal of `exam_total` from the grouping
   prompt, schema and manifest (D3).
4. Deletion of the temperature field from the DOCX profile and its settings (D4).
5. Replay tests for each case (D6).

## Validation

- New replay tests over the recorded Svenska 2 conversion, one for each case
  A, B, D and E (C no longer applies once `exam_total` is gone).
  - Each case yields 24 items, 36 points and `header.printed_total` 36.
  - Items 1-15 are marked as estimated.
  - The Del 2 and Del 3 questions keep their printed points.
- Unit tests for the points-line owner and the exam-total reader.
  - Two different total lines, or none, give an empty total.
  - A total line after the first question is not the exam total.
- Focused suites: `tests/unit/domain/curated_apps/exam_workspace/test_docx_header.py`,
  `test_docx_section_points.py`, `test_exam_workspace_docx_section_points_replay.py`
  and `test_exam_workspace_docx_build.py`.
- `pdm run lint` and `pdm run typecheck`.
- One Svenska 2 import on staging after integration: 24 questions, 36 points,
  exam total 36.

## Stop Conditions

- Stop if a recorded conversion other than Svenska 2 changes its question
  count or points under the new owner rule. Report it before changing the rule.
- Stop if removing `exam_total` from the grouping schema needs a new recording
  for a replay test. Report it, because new recordings cost live AI calls.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| D1 | A part heading's one printed total is split over its part's questions that print no points, marked as estimated, whether the grouping tags the heading as a part total or as an instruction; the parent keeps its printed total. |
| D2 | One shared rule gives a points line after a question to that question in batching, admission and the section split; the line never becomes a separate question or review item. |
| D3 | Code reads `header.printed_total` from the one total line printed before the first question; the grouping has no `exam_total` kind; no line, or conflicting lines, leave it empty. |
| D4 | The never-sent temperature is deleted from the DOCX conversion profile and its settings. |
| D5 | Variation in grouping shape and question kinds is out of scope. |
| D6 | Proof is replay tests over the recorded Svenska 2 conversion for each tagging case, plus one Svenska 2 import on staging; no corpus rerun. |
