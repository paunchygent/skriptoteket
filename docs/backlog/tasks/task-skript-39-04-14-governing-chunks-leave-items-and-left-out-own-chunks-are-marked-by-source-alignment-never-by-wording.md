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

### D5-D7 measurement over all recorded captures (2026-10-18)

Recorded data only, no model calls. Base `f2a00f3a3`, head `4d7929bf6`. The
probe ran the old and the new rule side by side on the same calls. Evidence:
`evidence/drop-audit/` in retained root `01a14ea8-b0ba-7df0-ab14-f557d25edebc`,
and Hemma `~/logs/probe-39-04-14/`.

- 15 captures replay at head: 8 `docx_key_provenance_v14`, the 2
  `docx_user_exams` and 5 user re-records (2026-10-17/18). Item counts are equal
  at base and head. Left-out marks: 0 at base and 0 at head in every capture.
  There are no `own_chunks_left_out`, `own_instruction_returned` or
  `governing_text_kept` events, and no governing paragraph is removed.
- All 19 left-out chunks examined are blank answer lines aligned to a paragraph.
  Both rules leave them unmarked.
- No recorded data exercises D5, D6 or D7. No mark appears, disappears or
  changes.
- 319 older captures cannot replay at head: 233 `d26`, 36 `live-run`, 22 `u1`
  and 28 `snap` exam runs. Their grouping replies use `other_anchors`, which the
  grouping contract replaced with `header_anchors` (TASK-SKRIPT-39-05-14). 32
  `snap` runs have no grouping at all. Translating these replies would invent
  grouping decisions, so the drop audit below reads their reply items directly.

### Drop audit: what converted items leave out of the source (2026-10-18)

Collection: for every recorded converted reply item, the probe compared each
source sentence of the chunks the item lists, and each own chunk no item lists,
with the item's text: body, choices, gaps, entries, key and criteria. A
sentence counts as an instance when its text does not appear in the item.
Points lines and blank answer lines were skipped. This yields 1,091 instances
in 442 distinct items. An item is counted once per distinct exam, anchors and
converted text, however many runs recorded it.

Junior-implementation-specialist children read every instance with the source
and the converted text side by side, in 23 batches. For each one they gave the
kind of change and whether the item works the same or worse for a student, with
a reason. No score or wording rule decided a verdict. The lead reviewed the
"worse" verdicts and settled the 2 unclear ones as over-gapping, which is worse
(`settled.json`). For every "worse" instance from a capture that replays at
head, the lead also checked the final document item built from the same chunks.

| Kind of change                     | Same | Worse, recorded 2026-10-11..15 | Worse, recorded 2026-10-16..18 |
| ---------------------------------- | ---: | -----------------------------: | -----------------------------: |
| Key moved to key fields            |  360 |                              2 |                              0 |
| Label or numbering                 |  118 |                              0 |                              0 |
| Heading text dropped               |   88 |                             59 |                              0 |
| Blank line or gap                  |   83 |                              0 |                              0 |
| Other (matching rows, word bank)   |   75 |                             10 |                              3 |
| Instruction sentence dropped       |   39 |                             22 |                             11 |
| Context or stem sentence dropped   |    6 |                             33 |                              7 |
| Content altered                    |    3 |                             20 |                              8 |
| Key content lost or changed        |    0 |                            131 |                              0 |
| Subquestion or lead-in dropped     |    0 |                              6 |                              0 |
| Wording, section placement, points |    7 |                              0 |                              0 |

Two kinds dominate the older captures: lost keys (131) and dropped headings
(59). Both come from the `svenska_2` facit exams. Current captures of the same
exams (`v14` and four live runs) show neither, so the current prompt and
grouping no longer produce them. The 29 "worse" instances recorded since
2026-10-16 come from 2 recurring defects:

1. **The model rewrites gap sentences around the gap** (bf26 diagnostic, bf26
   unit test, sa24). It drops the bracketed cue next to the gap, or the clause
   before it.

   - "You \_\_\_ (skulle vara) more careful…" became "You [gap] more careful…"
     (`v14`, live-run-1, live-run-2).
   - "We live in \_\_\_ (ett eget hus)." became "We live in [gap]." (`v14`).
   - "The jacket looked thin. \_\_\_ (emellertid), it kept me warm." lost its
     first sentence (`v14`).
   - "She is \_\_\_ (den enda)…" lost "is" (live-run-2, live-run-3).

   Across current captures, 13 of 795 cue-bearing gap sentences lose their
   cue (`cues.out`). The final documents show the loss too. Without the cue
   the student cannot tell which phrase to translate, and the key accepts only
   that phrase. The prompt already says every cue stays where it is printed
   (`exam_workspace_docx_build_prompt.py`, "What stays text"), so the prompt
   rule alone does not hold.

2. **A listed chunk no paragraph shows goes unmarked.**

   - In chapter 4, Part 3 Question 4 lost its word bank, "Use the best word or
     phrase." and "Two words are extra." in `v14` and in live runs 1-3. The
     final item shows only the gap sentence, while Questions 1-3 and 5-7 keep
     all three.
   - In chapter 4, q8 (`v14`) lists its own chunks but carries q7's stem word
     for word ("Which term names the tired nurse?") with q8's choices and key.
     The stanza and "Read the stanza:" are gone.

   Cause: admission examines only own chunks that no item lists
   (`_with_left_out` reads `state.pending`). A chunk that the item lists but no
   body paragraph, choice or entry is aligned to is never checked.

Four reply-level drops are not defects in the output: the pipeline places the
instruction back in the final item. These are "Write most or the most." and
"Stryk under bisatsen." (both checked against the item's own final text), and
the q6 instruction in exempelprov. The unlisted-chunk batch has 6 "worse"
instances, all from 2026-10-11..15 captures. Current captures leave only blank
lines, keys and points unlisted.

**Judgment on D7: accept as is.** The old wording rule marked none of these
defects. Base and head both give 0 marks on all 15 replayable captures,
including `v14`, which holds the cue drops, q8 and Question 4. D7 therefore
loses no signal that the recorded data shows the old rule giving. The 29
defects sit upstream of D7, in places neither rule examines.

Proposed fixes, as follow-up tasks; neither compares wording:

- **Gap paragraphs from the source.** When an item's aligned source paragraph
  has blank runs, build the body paragraph from the source text and replace
  each blank run, in order, with the reply's gap. The reply supplies only the
  accepted values. A gap count that differs from the blank-run count sends the
  item to review. Cues, lead clauses and verbs then cannot be lost, and the
  prompt's cue rule becomes a structural guarantee.
- **Check listed chunks too.** Extend the left-out check (D4) from unlisted own
  chunks to every own chunk the item lists. A chunk that no body paragraph,
  choice, matching entry or key field is aligned to, and that is not an answer
  line or a points line, is marked. This catches Question 4 and q8 by
  alignment alone.

### Implementation state (2026-10-18)

Implemented on local branch `claude/affectionate-payne-93506d` (merges
`claude/bold-dijkstra-162ba8` at `f2a00f3a3`). The suite above passes on Hemma
(4567 passed, 59 skipped; `~/logs/verify-39-04-14.log`); lint, mypy and
`docs-validate` pass. The first suite run failed 12 admission tests that
encoded the old token reading; D4-D7 record how each was decided. Review
`b313b2b1` (changes requested: F1 orphaned gaps, F2 invalid choice fixture) was
repaired at `62e178088` (D11); review `5d0e4e46` approved `62e178088`
(`evidence/reviews/` in retained root `01a14ea8-b0ba-7df0-ab14-f557d25edebc`).
The Hemma suite passes at `62e178088` (4569 passed, 59 skipped;
`~/logs/suite-39-04-14-62e.log`).

## Stop Conditions

- A replay difference that is not a proven fix goes to the parent before merge.
- A body producer whose paragraphs cannot state their chunk goes to the
  parent; it never falls back to wording.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| D1  | A body paragraph whose alignment entry is a governing chunk the item lists leaves the item's body together with that entry; no other paragraph changes.                                                                                                                                                                                                                                                                                                                              |
| D2  | When that removal would leave the body empty, or would take every response gap of the item (D11), the item keeps its body and `governing_text_kept` names the chunk; the parent still shows the chunk. These are the only cases of the event. An item that lists no own chunk is dropped as before.                                                                                                                                                                                  |
| D3  | A listed governing chunk no body paragraph is aligned to changes nothing in the item and reports nothing; wording in an unaligned or other-chunk paragraph stays.                                                                                                                                                                                                                                                                                                                    |
| D4  | An item shows a left-out own chunk if and only if a body paragraph is aligned to it (`AlignedItem.shows`) or one of its choices or matching entries is (`AlignedItem.entry_chunks`, the chunk at the start of each aligned entry span from the entry ownership); every other left-out chunk is marked (D41), in admission and in the return of misplaced own instructions alike. Body edits keep the entry chunks (`AlignedItem.with_body`).                                         |
| D5  | Gap-value and criterion text never counts as showing a left-out own chunk: neither carries chunk alignment, and wording is not evidence. A drawing chunk counts as shown when a body paragraph is aligned to it (its picture), not unconditionally left out.                                                                                                                                                                                                                         |
| D6  | A left-out own chunk whose every line is a source answer or facit line (`docx_source_rules.answer_line`: an optional number, letter or bullet, then `Svar:`, `Rätt svar:`, `Facit:`, `Svarsexempel:`, `Correct answer:`, `Answer key:` and the like) is the item's key and is held unmarked. This classifies the source line, like `points_line`; it compares no reply wording with the source. User approved 2026-10-18: answer-label lines count as the key and are never flagged. |
| D7  | Detection is per chunk: a reply paragraph aligned to a chunk shows that chunk even when the reply shortens it, so a dropped sentence inside an aligned paragraph is no longer marked; a table or stem chunk whose words another paragraph repeats is marked. The admission tests that asserted the old token reading are rewritten to these rules. User accepted 2026-10-18: a sentence dropped inside an aligned paragraph is not flagged; a wholly dropped paragraph still is.     |
| D8  | `_item_without`, `_paragraph_without`, `_removed`, `_without_lines`, `_without_edge`, `_squash`, `_words`, `wording_left_out` and its token helpers are deleted; the marking-guide test that asserted criterion wording counts as shown is deleted with them. No wording comparison or fallback replaces them.                                                                                                                                                                       |
| D9  | Replay identity is the regression bar: any difference in the ten recorded replays is classified as a proven fix or stops the task.                                                                                                                                                                                                                                                                                                                                                   |
| D10 | Owning story is ST-SKRIPT-39-04; the task builds on TASK-SKRIPT-39-04-13 at `cb3863f7d`.                                                                                                                                                                                                                                                                                                                                                                                             |
| D11 | A removed paragraph takes the response gaps it places: their declarations leave the item with it, so the item stays a valid native item (review F1, 2026-10-18). When the removed paragraphs place every gap of the item, the item keeps them, as in D2. Decided by the implementation lead under D1 and D2; no wording is compared.                                                                                                                                                 |
