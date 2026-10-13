---
type: task
id: TASK-SKRIPT-39-05-08
title: Stop producing question titles at import and turn printed group headings into instructions
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-13'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
  - Imported questions carry no title and a printed heading above a group of questions becomes that group's instruction
  - The stored exam item has no title field, and nothing reads one (labels, answer-key prompts, exports); no compatibility path (user decision 2026-10-13)
story: ST-SKRIPT-39-05
backlog_document_profile: contract-derived
---

## Implementation Contract

Exam questions imported from Word get a title that the model invents from
printed text, and the converter and its readers depend on it. Exam.net
discards a QTI item title (HuleEduOS probe round 12, exam 5325595), so the
title is never seen by students and only causes faults. The 2026-10-13
import replay of `biology_cells_energy_quiz.docx` also found these faults:

- q4 (matching) put its stem in `title` and an empty body text, which
  admission rejected (2 of 10 replies);
- q15 replied with `null` text to mark a gap, and its kind flipped between
  gap_fill and free_text, because the labeler and the converter define the
  gap_fill/free_text boundary in different words;
- the type-conflict resend dropped the answer-key chunks, so the resent
  item had no accepted values or marking guide;
- the source-text fallback set no points, so q15 showed "Poäng saknas".

This task removes the native exam item's title and fixes those faults:

- **No title.** `NativeExamItem` loses `title`. The converter's output
  schema and prompt ask for none, and no source rule writes one. Every
  reader stops using it: the editor's "Rubrik" field, the question list
  and Filer labels, the conversion merge, answer-key prompts, QTI export
  and language detection.
- **Printed headings.** A printed heading over one question is copied
  verbatim as the first paragraph of that question's body. A printed
  heading over two or more consecutive questions becomes the first line of
  their parent's instruction, followed by any printed instruction text; a
  heading with no instruction line still forms the parent.
- **QTI item title.** The QTI item title attribute carries the
  exam-language question label ("Fråga N").
- **One gap_fill/free_text definition.** One written definition, owned in
  one place, generates both the labeler's label descriptions and the
  converter's kind rule. It keeps D15 of TASK-SKRIPT-39-05-04 and adds: an
  answer key that lists alternative sentences for one answer line is
  gap_fill.
- **No empty question text.** The reply schema forbids empty or null text
  in text segments, and the prompt says a printed blank or answer line in a
  kind without gaps is not the question text; the printed question goes in
  the body.
- **Resend keeps the key.** The single type_conflict resend keeps the
  question's answer-key chunks.
- **Fallback keeps points.** The source-text fallback item keeps the
  question's printed points.

Out of scope: the DigiExam lane's items, which keep the names the teacher
typed in DigiExam (correction source, DigiExam QTI adapter, DXE
enrichment). Saved exams that still carry a title are not migrated and no
longer open; on deploy to staging every saved exam-workspace exam there is
deleted with its versions and stored files. Production is untouched.

## Contract Inputs

- ST-SKRIPT-39-05 and TASK-SKRIPT-39-05-04 (D15, D32: admission never
  retries; one type_conflict resend).
- Import replay evidence: retained session
  `01a13559-bf2e-760d-a690-3a3dea446cd5`, `evidence/import-replay/README.md`.
- HuleEduOS `examnet-qti3-contract.md` and probe ledger round 12
  (2026-10-13): Exam.net discards the item title, and a parent's
  instruction becomes the task's information block.
- Code: `native_exam_document.py` (`NativeExamItem.title`),
  `docx_ai_contracts.py` (`ProducedItem.title`),
  `exam_workspace_docx_build_rounds.py` (`_PROMPT` title rules),
  `docx_source_rules.py` and `docx_governing_chunks.py` (title writes),
  `docx_section_instructions.py` (parents), `decisions_item_labeler.py`
  (label descriptions), `docx_ai_build.py` (`review_source_item`),
  `answer_key_view.py` and `answer_key_prompts.py`, `examnet_qti_export.py`
  and `exam_language_labels.py`, and the exam-workspace frontend.

## Core Vertical And Performance

One vertical:

1. The teacher imports `biology_cells_energy_quiz.docx`.
2. Questions 8–10 show "Facts", "DNA base pairing" and "Classification" as
   the first line of their question text, and no question has a title.
3. Question 4 converts as matching and question 15 as gap_fill with its
   accepted sentences.
4. The QTI export imports into Exam.net with the headings in the question
   text.

The change removes prompt and schema text and adds no model call.

## Validation

- `pdm run lint` and `pdm run typecheck`.
- Focused pytest for the native item model, the build schema and
  admission, heading placement (one question and a group, with and without
  an instruction line), the type_conflict resend, the source-text fallback,
  answer-key prompts and QTI export.
- A script deletes `title` from the recorded replies; no live re-recording.
  The two title-only replay tests (`low24_own_title`, `low26_item_held_title`)
  are deleted (user decision 2026-10-13).
- Vitest for the editor, question list, Filer labels and conversion merge
  without a title; `pdm run fe-type-check`, `pdm run fe-lint` and the
  frontend build.
- Replay of the q4 and q15 requests against the real provider, 10 runs
  each: no reply is rejected for empty or null text, and q15 is gap_fill
  with accepted sentences in every run.
- Staging walk on Hemma after merge and the staging exam deletion:
  1. The exam list is empty before the first import.
  2. Import the biology quiz: no title field in the editor; questions 8–10
     start with their printed headings; question 4 is matching; question
     15 is gap_fill with its accepted sentences and printed points.
  3. A heading over a group shows as the group's instruction.
  4. Export QTI and import it into Exam.net; the headings appear in the
     task text.

## Stop Conditions

- A reader of the native item title is found that the contract does not
  name.
- The shared gap_fill/free_text definition cannot generate both the
  labeler and the converter texts.
- A fix would need admission to retry, against D32.
- Deleting the staging exams would touch production or another app's data.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                                                                                                |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| D1  | One written definition of the gap_fill/free_text boundary, owned in one place, generates both the labeler's label descriptions and the converter's kind rule (user decision 2026-10-13).                                                                                                                                             |
| D2  | D15 of TASK-SKRIPT-39-05-04 stays, and an answer key that lists alternative sentences for one answer line is gap_fill (user decision 2026-10-13).                                                                                                                                                                                    |
| D3  | The import faults found on 2026-10-13 are fixed in this task together with title removal (user decision 2026-10-13).                                                                                                                                                                                                                 |
| O1  | The reply schema forbids empty or null text in text segments, and the prompt says a printed blank or answer line in a kind without gaps is not the question text; the printed question goes in the body (user decision 2026-10-13).                                                                                                  |
| O2  | The type_conflict resend keeps the question's answer-key chunks (user decision 2026-10-13).                                                                                                                                                                                                                                          |
| O3  | The source-text fallback item keeps the question's printed points (user decision 2026-10-13).                                                                                                                                                                                                                                        |
| T1  | A printed heading over one question is copied verbatim as the first paragraph of that question's body (user decision 2026-10-13).                                                                                                                                                                                                    |
| T2  | A printed heading over two or more consecutive questions becomes the first line of their parent's instruction; a heading without an instruction line still forms the parent (Exam.net probe round 12, 2026-10-13).                                                                                                                   |
| T3  | Only the native exam item loses its title; the DigiExam lane keeps its item names (2026-10-13).                                                                                                                                                                                                                                      |
| T4  | The QTI item title attribute carries the exam-language question label "Fråga N"; Exam.net discards it (probe round 12, 2026-10-13).                                                                                                                                                                                                  |
| T5  | Saved exams that carry a title are not migrated and no longer open (user decision 2026-10-13).                                                                                                                                                                                                                                       |
| T6  | On deploy to staging, every saved exam-workspace exam there is deleted with its versions and stored files; production is untouched (user decision 2026-10-13).                                                                                                                                                                       |
| T7  | Parents are flat. A heading the grouping marks as governing part of a run that already has a parent (for example q2-q3 inside a q1-q3 parent) opens the body of every question it governs instead of forming a parent; this narrows T2 and D40 for overlapping scopes only. Nested parents are not built (user decision 2026-10-14). |
