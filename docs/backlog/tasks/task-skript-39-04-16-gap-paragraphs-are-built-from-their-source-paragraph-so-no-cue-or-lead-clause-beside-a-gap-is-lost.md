---
type: task
id: TASK-SKRIPT-39-04-16
title: Gap paragraphs are built from their source paragraph, so no cue or lead clause
  beside a gap is lost
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

## Stop Conditions

- A replay difference that is not a proven fix goes to the parent before merge.
- A body producer whose paragraphs cannot state their source paragraph goes to
  the parent; it never falls back to wording.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| D1  | The rule applies to gap_fill items. Other kinds carry no gap segments (`aligned_native_item` prints a reply gap as a blank in them) and keep their current body. Decided by the implementation lead under the contract's "the reply's gap". |
| D2  | A gap_fill body paragraph whose alignment (`SourceFormatting.output_anchors`, after every body producer) is a source paragraph with blank runs is built from that source paragraph: its visible source text (entry-owned and recovered carrier spans excluded), starting after the printed question label, ending before an inline answer label (`ANSWER_LABEL`), with leading and trailing whitespace trimmed, and the source marks and heading level. Table cells that `sourced_fragments` joins into one row paragraph (" \| " separator, same heading) count as one source paragraph. |
| D3  | Blank runs, by character class only: in a source paragraph with any run of 2 or more underscores, those runs are its blank runs. In any other paragraph, a run of ellipses or of 2 or more dots that no letter touches on either side is a blank run. Adjacent blank characters form one run. This refines the contract's blank-run definition (2+ underscores, ellipsis or dot runs): `sa24` prints letter hints such as "(s…t)" inside its cues. Mac parent ruling 2026-10-18. |
| D4  | Every body paragraph aligned to the same blank-run source paragraph is replaced by the one built paragraph, at the place of the first. The gaps of those paragraphs, in body order, fill the blank runs in source order; the reply's wording in those paragraphs is discarded. Gap ids, accepted values and the item's gap declarations are unchanged. |
| D5  | When the gap count of those paragraphs differs from the blank-run count, the build raises `GapCountMismatchError`. It is no `FormattingTransferError`, so the whole-body rebuild never runs for it. Admission records `gap_count_mismatch` with the two counts and sends the question's source to review, like `native_contract_invalid`. |
| D6  | A built paragraph whose reply paragraphs hold a picture raises `FormattingTransferError("cannot rebuild picture placement")`, as `SourceFormatting._rebuild` does, and admission sends the item to the existing formatting review. |
| D7  | Paragraphs aligned to no source paragraph (-1), or to a source paragraph without blank runs, keep their current rendering. `_skip_gap` and `gap_spans` keep their own blank patterns for projection and rebuild placement; the new rule decides the final text of every blank-run paragraph after them. |
| D8  | No wording comparison and no fallback: the source paragraph is chosen by alignment alone, and a count mismatch never keeps the reply's wording. |
| D9  | Owning story is ST-SKRIPT-39-04; the task builds on main at `6e3453b2e`. Replay identity outside the restored paragraphs is the regression bar. |
