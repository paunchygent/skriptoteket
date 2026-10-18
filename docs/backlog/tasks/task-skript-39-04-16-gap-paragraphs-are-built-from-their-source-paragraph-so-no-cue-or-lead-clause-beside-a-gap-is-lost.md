---
type: task
id: TASK-SKRIPT-39-04-16
title: Gap paragraphs are built from their source paragraph, so no cue or lead clause beside a gap is lost
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
  - A gap_fill body paragraph aligned to a source paragraph with blank runs is that source paragraph's text with the reply's gaps in its blank runs, in order; a gap count that differs from the blank-run count sends the item to review; no wording is compared and no fallback remains
story: ST-SKRIPT-39-04
backlog_document_profile: contract-derived
---

## Implementation Contract

The TASK-SKRIPT-39-04-14 drop audit (Validation, "Drop audit", 2026-10-18)
found that the converter model rewrites gap sentences: it drops the bracketed
Swedish cue beside a gap in 13 of 795 cue-bearing sentences, and sometimes a
lead clause or verb. The final documents show the loss. The prompt already
says every cue stays (`exam_workspace_docx_build_prompt.py`, "What stays
text"), so only a structural rule fixes it.

Root cause (R1). `SourceFormatting._paragraph` projects each reply text
segment onto the source by a forward cursor search (`SourceFormatting.span`),
and `_skip_gap` consumes only the blank right after the preceding text. Source
text between the consumed blank and the next matched reply segment is skipped
and recorded nowhere. The only loss signals in the formatting layer, `lost` in
`source_format_alignment.align_paragraph` and `missing` in
`source_format_coverage.complete_source_formatting`, look at marked
characters. A cue such as "(ett eget hus)" is unmarked text, so its loss is
invisible on every path. Base replay dumps at `6e3453b2e` show it:
`bf26_diagnostic` item_072 "We live in [gap].", item_078 "[gap] left the
party at midnight.", item_103 "You [gap] more careful about your health.",
and `bf26_english` item_019 " [gap] (emellertid), it kept me warm.".

This task makes the source paragraph the text of every gap_fill body
paragraph aligned to a source paragraph with blank runs. The reply supplies
only its gaps and their accepted values.

## Contract Inputs

- Finding: TASK-SKRIPT-39-04-14 drop audit and its interpretive audit
  (`~/.cache/claude-prompts/drop-audit-39-04-14/` on Hemma, `SUMMARY.md`,
  `cues.out`); parent brief, user request 2026-10-18.
- Alignment authority: `SourceFormatting.output_anchors`, the start of the
  source paragraph each body paragraph was aligned to, after every body
  producer (exact, aligned, single-paragraph rebuild, whole-body rebuild and
  the coverage restore); `docx_item_alignment.paragraph_chunks` reads it.
- Builder: `docx_ai_build.aligned_native_item`; admission:
  `exam_workspace_docx_build_admission._built`.
- Planning probe over the ten base replays (retained root
  `01a14f3e-11d5-7745-90e8-6323496fbf74`, `evidence/probes/blank_defs.py`):
  211 gap_fill items have blank runs in their own source paragraphs. Under a
  definition that counts every ellipsis, 35 `sa24` items show 2 blank runs for
  1 gap, because `sa24` prints letter hints such as "(s…t)" inside its cues.
  Under D3, none differ.

## Core Vertical And Performance

One pass over the final body after source formatting; each built paragraph
reads its source paragraph once. No new data is stored, and the document and
event formats are unchanged except the new admission code `gap_count_mismatch`.

## Validation

- Adversarial unit tests: a reply that drops the cue beside a gap gets the cue
  back; a reply that drops the lead clause before a gap gets it back; a reply
  with one gap more and one gap fewer than the paragraph's blank runs sends the
  item to review with `gap_count_mismatch`, never through the whole-body
  rebuild; two reply paragraphs aligned to one source paragraph become one
  built paragraph; a letter-hint ellipsis "(s…t)" next to an underscore blank
  is no blank run; a dot run with no underscore run in its paragraph is one; a
  recovered points annotation and the printed question label stay out of the
  built text; source text from an inline answer label onward stays out; a
  free_text item with a printed answer line keeps its current body; a
  paragraph aligned to no source paragraph keeps the reply's wording.
- The ten recorded replays (eight `docx_key_provenance_v14` corpus exams and
  the two `docx_user_exams`) restore the bf26 cues "(skulle vara)", "(ett eget
  hus)", "(De flesta av oss)" and "The jacket looked thin."; every other
  replay difference is classified as a fix.
- On Hemma: the touched-domain suite
  `PYTHONHASHSEED=0 pdm run test-parallel tests/unit/application/curated_apps tests/unit/domain/curated_apps -q -p no:randomly`,
  `pdm run lint`, `pdm run typecheck`, `pdm run docs-validate`.

### Replay outcome (2026-10-18)

The ten recorded replays, dumped with documents and events (UUIDs masked) at
the base `6e3453b2e` and at `d6c2f9af`, differ in 11 item bodies in 4 exams
and in nothing else: no event, item set, key or review state changes, and no
`gap_count_mismatch` (Hemma `~/logs/replays-39-04-gap-source/`,
`classified.txt`). Every difference is a fix:

- Cue or lead clause restored: `bf26_diagnostic` item_072 "(ett eget hus)",
  item_078 "(De flesta av oss)", item_103 "(skulle vara)"; `bf26_english`
  item_019 "The jacket looked thin.", item_006 "(självfallet)" back beside
  its gap instead of at the sentence end.
- Source wording restored: `sa24` item_034 loses a comma the reply inserted
  after the cue; `chapter_4` Part 3 Question 4 (item_025) gets back its word
  bank, "Use the best word or phrase." and "Two words are extra.", as
  Questions 1-3 and 5-7 already show.
- Whitespace: `bf26_english` item_044 drops a trailing space and `sa24`
  item_020 a leading space.
- Paragraph shape: `bf26_english` item_045 and item_047 show their source
  paragraph as one paragraph with its line breaks, as items 034-046 of the
  same exam already did, where the reply had split it.

Two intermediate states were repaired before this outcome: the edge trim
removed the space after a paragraph-initial gap (38 items), and a split at
source line breaks changed 10 correct items.

### Implementation state (2026-10-18)

- D2-D4, D6, D7: `source_gap_paragraphs.py` (`blank_runs`, `source_paragraph`,
  `gap_paragraphs_from_source`), wired in `docx_ai_build.aligned_native_item`
  for gap_fill items after `complete_source_formatting`;
  `ChunkProvenance.pictures_in`; `SourceFormatting.visible_text_segments` and
  `content_start` made public. `source_paragraph` also builds a gapless
  paragraph, for TASK-SKRIPT-39-04-15 to reuse.
- D5: `GapCountMismatchError`; `exam_workspace_docx_build_admission._built`
  records `gap_count_mismatch`.
- Tests: `test_source_gap_paragraphs.py`,
  `test_exam_workspace_docx_gap_count_admission.py`.
- `test_exam_workspace_docx_label_kinds` tested reply-printed part labels by
  prefixing "a) " to a gap_fill stem the source does not label; D4/D8 discard
  that wording, so the test now uses the matching item `body:0059` (a choice
  stem strips a leading enumeration) and selects the reply by the recording
  served.
- On Hemma at `f4dfe336`: the touched-domain suite passes (4118 passed, 59
  skipped; `~/logs/suite-39-04-16-final.log`); lint, typecheck and
  `docs-validate` pass.

## Stop Conditions

- A replay difference that is not a proven fix goes to the parent before merge.
- A body producer whose paragraphs cannot state their source paragraph goes to
  the parent; it never falls back to wording.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | The rule applies to gap_fill items. Other kinds carry no gap segments (`aligned_native_item` prints a reply gap as a blank in them) and keep their current body. Decided by the implementation lead under the contract's "the reply's gap".                                                                                                                                                                                                                                                                                                                                                     |
| D2  | A gap_fill body paragraph whose alignment (`SourceFormatting.output_anchors`, after every body producer) is a source paragraph with blank runs is built from that source paragraph: its visible source text (entry-owned and recovered carrier spans excluded), starting after the printed question label, ending before an inline answer label (`ANSWER_LABEL`), with leading and trailing whitespace trimmed, and the source marks and heading level. Table cells that `sourced_fragments` joins into one row paragraph (" \| " separator, same heading) count as one source paragraph.       |
| D3  | Blank runs, by character class only: in a source paragraph with any run of 2 or more underscores, those runs are its blank runs. In any other paragraph, a run of ellipses or of 2 or more dots that no letter touches on either side is a blank run. Adjacent blank characters form one run. This refines the contract's blank-run definition (2+ underscores, ellipsis or dot runs): `sa24` prints letter hints such as "(s…t)" inside its cues. Mac parent ruling 2026-10-18.                                                                                                                |
| D4  | Every body paragraph aligned to the same blank-run source paragraph is replaced by the one built paragraph, at the place of the first. The gaps of those paragraphs, in body order, fill the blank runs in source order; the reply's wording in those paragraphs is discarded. Gap ids, accepted values and the item's gap declarations are unchanged.                                                                                                                                                                                                                                          |
| D5  | When the gap count of those paragraphs differs from the blank-run count, the build raises `GapCountMismatchError`. It is no `FormattingTransferError`, so the whole-body rebuild never runs for it. Admission records `gap_count_mismatch` with the two counts and sends the question's source to review, like `native_contract_invalid`.                                                                                                                                                                                                                                                       |
| D6  | A built paragraph shows the source pictures whose source place lies in its source paragraph, each at its source place (a place before the build span's start stands at the start). The pictures of the reply paragraphs it replaces must be exactly those pictures, by asset id and count; otherwise the build raises `FormattingTransferError("cannot rebuild picture placement")` and admission sends the item to the existing formatting review. Decided by the implementation lead 2026-10-18 after a refusal for every picture regressed an admitted item (`test_source_surface_repair2`). |
| D7  | Paragraphs aligned to no source paragraph (-1), or to a source paragraph without blank runs, keep their current rendering. `_skip_gap` and `gap_spans` keep their own blank patterns for projection and rebuild placement; the new rule decides the final text of every blank-run paragraph after them.                                                                                                                                                                                                                                                                                         |
| D8  | No wording comparison and no fallback: the source paragraph is chosen by alignment alone, and a count mismatch never keeps the reply's wording.                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| D9  | Owning story is ST-SKRIPT-39-04; the task builds on main at `6e3453b2e`. Replay identity outside the restored paragraphs is the regression bar.                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
