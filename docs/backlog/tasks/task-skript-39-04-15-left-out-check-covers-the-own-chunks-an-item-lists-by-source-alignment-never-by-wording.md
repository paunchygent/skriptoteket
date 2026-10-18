---
type: task
id: TASK-SKRIPT-39-04-15
title: Gapless body paragraphs show their aligned source paragraph's text, so a reply cannot
  drop or replace stem sentences
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-18'
status: proposed
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
- A gapless body paragraph aligned to a source paragraph shows that paragraph's text; q8 of
  the v14 chapter_4 replay shows its own stem and metodprov 1 keeps its second sentence;
  every replay difference is read interpretively and classified
story: ST-SKRIPT-39-04
backlog_document_profile: contract-derived
---

## Implementation Contract

Scope by user ruling 2026-10-18 (relayed by the orchestrator): fix the q8 drop at its root.
No new flag and no coverage threshold. TASK-SKRIPT-39-04-14 D7 stands. Question 4 is fixed by
Task 1 (TASK-SKRIPT-39-04-16, gap paragraphs built from the source paragraph).

Root cause (R1). A converted item's body text comes from the reply. Source alignment only
carries typography onto it (`source_formatting.SourceFormatting.body`):

- The `exact` path accepts any reply text that is a span of the source. Source text after
  or around that span is dropped with no signal.
- The `aligned` path picks the source paragraph by token overlap
  (`source_paragraph_match.overlap_scores`). `source_format_alignment.align_paragraph`
  keeps the reply's insertions and refuses only when a marked source character is lost.
  Unmarked source text the reply replaces goes with no signal.

The prompt already says the body is "the wording of its own source_anchors: every word, in
order" (`exam_workspace_docx_build_prompt.py`). The recorded reply breaks that rule, and no
structural rule holds it. Instances:

- q8 of chapter_4 (`v14`, `aligned` path): the reply's q8 body is q7's stem word for word
  (`docx_key_provenance_v14/chapter_4_poetry_and_lyrics_quiz_med_facit/docx_w1-01.json`).
  The final item asks q7's question with q8's choices and key, and the stanza is gone.
- metodprov 1 (`exact` path): "Gruppen har slumpat fram 120 tvåor från en fullständig
  elevlista." is dropped from body paragraph `body:0006`. It appears nowhere in the
  final item except its import record.

Fix: a gapless body paragraph aligned to a source paragraph is built from that source
paragraph's text and marks. The reply's paragraph only selects which source paragraph it
shows. The built text leaves out what other fields of the item show or what the body never
prints: the question label (`label_span`), the excluded intervals (points), the spans the
item's choices and matching entries are aligned to, and any paragraph holding an inline
answer label (`ANSWER_LABEL`), which stays as today. Pictures keep their place. Paragraphs
with gaps belong to Task 1. The listed-chunk check from the first scope (D1, D2 of the
previous revision) is kept as written: the left-out check also covers the own chunks an item
lists, by alignment only. It marks neither Question 4 nor q8, because a paragraph is
aligned to each (lead's reading of "the listed-chunk rule is kept as written").

## Contract Inputs

- User ruling 2026-10-18 (orchestrator `115dbf9f`, mailbox to lead `bb15ad98`).
- TASK-SKRIPT-39-04-14 Validation, "Drop audit" (2026-10-18), and the interpretive
  audit method in `~/.cache/claude-prompts/drop-audit-39-04-14/brief.md`.
- Probes at `6e3453b2e` (retained root `01a14f3e-12df-7020-8c18-18ad39a131cf`,
  `evidence/probes/`): `align_probe.py` (body and entry alignment per item) and
  `coverage_detail_probe.py` (the visible source characters each body-aligned chunk's
  alignment covers, with source, uncovered text and body for each chunk below 1.0).
  The ten replays hold 472 body-aligned chunks. 451 take the `exact` path, 15 `aligned` and
  6 `rebuilt`. 21 chunks are covered below 1.0.

## Core Vertical And Performance

The source paragraph and its marks are already indexed by `SourceFormatting`. Building a
paragraph from them is one pass over its characters.

## Validation

- Classification of the 21 chunks covered below 1.0 at base (lead, to be confirmed by
  the interpretive read):
  - Gap paragraph rewritten around the gap, Task 1: bf26 diagnostic 72, 78 and 103;
    bf26 english 6 and 19; chapter_4 Question 4 (`body:0130`).
  - Question heading "Part 3, Question n": the reply shows "Part 3," and the label
    stands in `printed_label`; the heading join shows it at its source place (7, chapter_4).
  - Gapless stem text dropped or replaced, this task: chapter_4 q8 (`body:0028`) and
    metodprov 1 (`body:0006`).
  - Inline answer-key paragraphs (`Svar:`) in svenska_2 omprov variants 1 and 2 Fråga 1
    a-c (6): the reply shows the morpheme split and drops the word. The interpretive read
    decides whether this is worse.
- Adversarial unit tests: a reply paragraph that repeats another question's stem
  shows its own source paragraph; a reply that drops a sentence of a gapless paragraph
  shows the whole paragraph; the label, the points and the inline options a choice is
  aligned to stay out of the built paragraph; marks carry over from the source; a paragraph
  with an inline answer label is unchanged; the listed-chunk check marks a listed word-bank
  chunk no paragraph shows, does not mark a listed chunk a paragraph shows, and does not
  mark a listed facit line.
- Interpretive read by a fresh junior, source and converted item side by side (drop-audit
  method): the 21 chunks at base, and every replay difference after the fix. A
  meaning-preserving edit is fine; a drop with no improving reason is a defect.
- The ten recorded replays: q8 shows its own stem, metodprov 1 keeps its second
  sentence, and every other difference is classified.
- On Hemma: `PYTHONHASHSEED=0 pdm run test-parallel tests/unit/application/curated_apps tests/unit/domain/curated_apps tests/unit/web -q -p no:randomly`,
  `pdm run lint`, `pdm run typecheck`, `pdm run docs-validate`.

## Stop Conditions

- A replay difference that the interpretive read finds worse goes to the parent before
  merge.
- Task 1 (TASK-SKRIPT-39-04-16) merges first. This branch merges `origin/main` when the
  parent says Task 1 has landed, and the replays and the interpretive read run again.
- A gapless paragraph that cannot name its source paragraph keeps the reply's text, as
  today; it never falls back to a wording match.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| D1  | The left-out check (`docx_own_instructions.left_out_chunks`, called from `_with_left_out`) also runs on every own chunk of the question that a converted item lists. It marks a chunk under D41 when no body paragraph, choice or matching entry is aligned to it. |
| D2  | A listed chunk is never marked when it is a source answer or facit line (`answer_line`), a points line (`is_points_line`), a grouped key (`state.grouped_keys`), a chunk the grouping marks as governing, or an instruction that section placement places. |
| D3  | No coverage threshold and no new flag. TASK-SKRIPT-39-04-14 D7 stands (user ruling 2026-10-18). |
| D4  | A body paragraph with no gap, aligned to a source paragraph, is built from that source paragraph's text and marks. The reply's paragraph only selects which source paragraph it shows. |
| D5  | The built paragraph leaves out the question label, the excluded intervals (points) and the spans the item's choices and matching entries are aligned to. A paragraph holding an inline answer label keeps today's projection. Pictures keep their source place. |
| D6  | Paragraphs with gaps are Task 1's (TASK-SKRIPT-39-04-16). The two builders share one source-text path after Task 1 merges. |
| D7  | Decisions read the source alignment and the source classification only; no reply wording is compared, and no fallback reads wording. |
| D8  | Proof is the interpretive replay read by a fresh junior (drop-audit method) plus the adversarial unit tests; every replay difference is classified. |
| D9  | Owning story is ST-SKRIPT-39-04; the task builds on TASK-SKRIPT-39-04-14 at `6e3453b2e` and merges after Task 1. |
