---
type: task
id: TASK-SKRIPT-39-04-14
title: Governing chunks leave items and left-out own chunks are marked by source alignment, never by wording
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-18'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
  - Which body paragraphs a governing chunk takes out of an item, and which of a question's left-out own chunks an item already shows, are decided from the per-paragraph source alignment; no whole-line, edge or token match remains; the ten recorded exam replays are unchanged except for proven fixes
story: ST-SKRIPT-39-04
backlog_document_profile: contract-derived
---

## Implementation Contract

TASK-SKRIPT-39-04-13 moved section placement onto the per-paragraph source
alignment and left two wording rules as follow-ups (its "Implementation state"
note):

- `docx_governing_chunks._item_without` (with `_paragraph_without`,
  `_removed`, `_without_lines`, `_without_edge`): when an item lists a chunk
  the grouping marks as governing, it removes the chunk's text from the item's
  body by whole-line or paragraph-edge regex matches, and reports
  `governing_text_kept` when the text stands anywhere else.
- `docx_own_instructions.wording_left_out`: whether an item already shows an
  own chunk of its question that it does not list, by an ordered token match
  of the chunk's lines against the body, choices, matching entries, gap values
  and criteria. Admission (`_with_left_out`) and the return of misplaced own
  instructions (`return_misplaced_own_chunks`) call it.

This task applies the 39-04-13 rule to both:

- A body paragraph aligned to a governing chunk the item lists is that chunk:
  the paragraph leaves the body with its alignment entry. Paragraphs aligned to
  any other chunk, or to none, stay unchanged, whatever their wording.
- An item shows a left-out own chunk if and only if a body paragraph, choice or
  matching entry is aligned to it (`AlignedItem.shows`, `AlignedItem.entry_chunks`).
  A source answer or facit line is the item's key, never left-out text. Any
  other left-out chunk goes under the check mark that shows it as printed (D41).

The wording code is deleted with no fallback.

## Contract Inputs

- Finding: TASK-SKRIPT-39-04-13 implementation-state note (two wording rules
  remain); parent brief 2026-10-18.
- Alignment authority: `docx_item_alignment.AlignedItem`, produced by
  `docx_ai_build.aligned_native_item`; since the 39-04-13 F1 repair
  (`cb3863f7d`) every body paragraph is split where its source chunk changes,
  so one paragraph never claims two chunks.
- Precondition checked: admission indexes the source over the reply's listed
  anchors and the question's own chunks (`exam_workspace_docx_build_admission`
  `build()`), so a listed governing chunk and every left-out own chunk can be
  aligned.

## Core Vertical And Performance

Assembly reads the alignment tuple each accepted item already carries; no new
data is produced. Removal is one pass over the body per governing anchor.

## Validation

- Adversarial unit tests: a reworded governing line aligned to the chunk
  leaves the item with no `governing_text_kept`; governing wording repeated
  inside a stem paragraph aligned to the stem stays; a reply that omits the
  governing chunk leaves the item unchanged with no event; an item whose whole
  body is aligned to the governing chunk keeps it and reports it; a left-out
  own chunk whose wording the reply repeats in an unaligned or other-chunk
  paragraph is marked; a left-out own chunk a body paragraph is aligned to is
  not marked; a choice aligned to a left-out chunk shows it, a choice that only
  repeats its wording does not; a source answer line is held unmarked while a
  stem line that mentions "svar:" is not.
- The ten recorded replays (eight `docx_key_provenance_v14` corpus exams and
  the two `docx_user_exams`) produce identical documents and events, or each
  difference is shown to be a fix.
- `PYTHONHASHSEED=0 pdm run test-parallel tests/unit/application/curated_apps tests/unit/domain/curated_apps tests/unit/web -q -p no:randomly`
  on Hemma, `pdm run lint`, `pdm run typecheck`, `pdm run docs-validate`.

### Replay outcome (2026-10-18)

The ten recorded replays, dumped with documents and events (UUIDs masked) at
the base `f2a00f3a3` (TASK-SKRIPT-39-04-13 head) and at `a51672799`, are
identical (`diff -r` empty; Hemma `~/logs/replays-39-04-14/`). No recorded
replay produces `own_chunks_left_out`, `governing_text_kept` or
`own_instruction_returned`, so the changed decisions are proven by the
adversarial unit tests, not by the replays.

### Implementation state (2026-10-18)

Implemented on local branch `claude/affectionate-payne-93506d` (merges
`claude/bold-dijkstra-162ba8` at `f2a00f3a3`). The suite above passes on Hemma
(4567 passed, 59 skipped; `~/logs/verify-39-04-14.log`); lint, mypy and
`docs-validate` pass. The first suite run failed 12 admission tests that
encoded the old token reading; D4-D7 record how each was decided. The task
awaits independent review; closeout stays with the reviewer.

## Stop Conditions

- A replay difference that is not a proven fix goes to the parent before merge.
- A body producer whose paragraphs cannot state their chunk goes to the
  parent; it never falls back to wording.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                                                                                                                                                                                                        |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | A body paragraph whose alignment entry is a governing chunk the item lists leaves the item's body together with that entry; no other paragraph changes.                                                                                                                                                                                                                                                                                      |
| D2  | When that removal would leave the body empty, the item keeps its body and `governing_text_kept` names the chunk; the parent still shows the chunk. This is the only case of the event. An item that lists no own chunk is dropped as before.                                                                                                                                                                                                 |
| D3  | A listed governing chunk no body paragraph is aligned to changes nothing in the item and reports nothing; wording in an unaligned or other-chunk paragraph stays.                                                                                                                                                                                                                                                                            |
| D4  | An item shows a left-out own chunk if and only if a body paragraph is aligned to it (`AlignedItem.shows`) or one of its choices or matching entries is (`AlignedItem.entry_chunks`, the chunk at the start of each aligned entry span from the entry ownership); every other left-out chunk is marked (D41), in admission and in the return of misplaced own instructions alike. Body edits keep the entry chunks (`AlignedItem.with_body`). |
| D5  | Gap-value and criterion text never counts as showing a left-out own chunk: neither carries chunk alignment, and wording is not evidence. A drawing chunk counts as shown when a body paragraph is aligned to it (its picture), not unconditionally left out.                                                                                                                                                                                 |
| D6  | A left-out own chunk whose every line is a source answer or facit line (`docx_source_rules.answer_line`: an optional number, letter or bullet, then `Svar:`, `Rätt svar:`, `Facit:`, `Svarsexempel:`, `Correct answer:`, `Answer key:` and the like) is the item's key and is held unmarked. This classifies the source line, like `points_line`; it compares no reply wording with the source.                                              |
| D7  | Detection is per chunk: a reply paragraph aligned to a chunk shows that chunk even when the reply shortens it, so a dropped sentence inside an aligned paragraph is no longer marked; a table or stem chunk whose words another paragraph repeats is marked. The admission tests that asserted the old token reading are rewritten to these rules.                                                                                           |
| D8  | `_item_without`, `_paragraph_without`, `_removed`, `_without_lines`, `_without_edge`, `_squash`, `_words`, `wording_left_out` and its token helpers are deleted; the marking-guide test that asserted criterion wording counts as shown is deleted with them. No wording comparison or fallback replaces them.                                                                                                                               |
| D9  | Replay identity is the regression bar: any difference in the ten recorded replays is classified as a proven fix or stops the task.                                                                                                                                                                                                                                                                                                           |
| D10 | Owning story is ST-SKRIPT-39-04; the task builds on TASK-SKRIPT-39-04-13 at `cb3863f7d`.                                                                                                                                                                                                                                                                                                                                                     |
