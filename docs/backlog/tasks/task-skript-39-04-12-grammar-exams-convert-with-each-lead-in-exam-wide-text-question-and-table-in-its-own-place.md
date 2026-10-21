---
type: task
id: TASK-SKRIPT-39-04-12
title: Grammar exams convert with each lead-in, exam-wide text, question and table in its own place
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

## Progress

### Reconciliation 2026-10-20 (Mac parent, against main 114ca971)

- Status corrected from `ready` to `in_progress`: C1-C4 are on main (53 commits, latest merge `d3a62108`, review-4 lows L1-L4, 2026-10-18). Review rounds 1-4 are named in commit subjects; no verdict is recorded in this doc.
- Owed: the gold corpus rerun and the omprov_grammatik_sve2 staging walk (not recorded as run), then closeout.

### 2026-10-21 (Hemma orchestrator)

- Gold-corpus replay rerun on main `66b3dc8e` (recorded replies, no live model calls; deterministic over two runs) against the lead's last baseline at `4479c804`: 8 of 10 exams differ, 2 are byte-identical (`metodprov_vetenskaplig_metod`, `svenska_2_kursavslutande_prov`). Every difference is in an item body: underscore answer lines and the trailing `/` marker are gone (exempelprov and omprov grammatik), points wording such as `(1 point)` and `Poäng:` is gone, bracketed or lead text moves next to gaps or joins a body, and item 001 in both Svenska 2 omprov variants changes parse origin from `llm_parsed` to `source_fallback` with its `+` morpheme splits gone. No header, instructions or part line differs, and no item id, anchor or point value changes. Attributing these to TASK-SKRIPT-39-04-20, 39-04-21, 40-04-15 and the re-recorded label_b replies is unconfirmed: nobody bisected. Treated as information for the user's closure, not as a blocker (Mac orchestrator 2026-10-21). Evidence: retained root `01a15f48-0f71-77ba-b7df-f48c8e838efb`, `evidence/proof/39-04-12-gold/report.md`.
- Mac staging walk wave 1b on `a8de9ae6` passed: omprov placements, lead-ins, shared texts, DEL groupings 4/2/2/1, totals 20/20/15/15 (Mac record `.artifacts/staging-walk-l1b-a8de9ae6/walk-record.md`).
- Review status: round 4 approved code at `60fbb42a`. The later DEL 4 commits and the lows fix (`d74fae85`, `334354b9`, `33ee4112`, `37b70940`, `4479c804`) are under independent review; findings go to the user for triage before any action.

### 2026-10-21 (implementation lead, F1 repair)

- Repair of tail-review finding F1 (high) on the user's 2026-10-21 go-ahead ("Yes, if it does not affect other more important behavior negatively"). A part line admission moves out of an entry (`_without_part_lines`) now leaves the item body too: the item builder receives the moved lines as released chunks, and a reply paragraph whose whole text is a released line, whole or a fragment, and no text of the question's own source, leaves the body. A reply paragraph that merges a released line with question text sends the body to the existing rebuild from the question's own source, or to source review when that cannot be built. The rule reads source alignment, not wording: a stem paragraph the part line repeats stays. The parent still publishes the line once.
- Proof: new `test_exam_workspace_docx_moved_part_line_body.py` (15 cases through admission, batch merge and final publication: foreign entry with whole line and fragments, own child entry, merged paragraph, own stem kept, a question-heading part line listed by a foreign entry, DEL 4 fragment and whole line) fails 15/15 before the fix and passes after; part-line, one-question-part, one-item-per-question heading, part-heading-fragment and user-exam replay families pass (84, with the new file); 44 source-formatting consumer files pass (585). Gold corpus on recorded replies, before (`4dece25e`) and after the fix: no difference in any of the 10 exams. None of the replay's 331 item builds receives a released part line, so the gold shows no collateral change but does not exercise the new paths; the synthetic file is their only behavioral proof. Lint and typecheck pass. Evidence: retained root `01a15fce-eac1-7e89-96c5-e9d8efdc3fc9`, `evidence/gold-f1/` and `evidence/*.txt`.
- Next: independent rereview of the F1 repair. Status stays `in_progress`.
