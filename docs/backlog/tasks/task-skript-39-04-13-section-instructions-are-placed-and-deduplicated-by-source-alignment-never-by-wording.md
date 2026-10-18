---
type: task
id: TASK-SKRIPT-39-04-13
title: Section instructions are placed and deduplicated by source alignment, never by wording
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-18'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: ruthless-reviewer
  decided_at: '2026-10-18'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: Independent ruthless-reviewer 7a083063 (Pi, Sol 6.1 high) approved f2a00f3a3 on second re-review after F1-F4 repairs; merged into main as b365fdefd and published in a0a81ab5a after the Hemma full typecheck and test pass; staging walk at a0a81ab5a on omprov_grammatik_sve2.docx showed each section instruction once in its own part, in the editor and in the QTI export (root 01a14e1f evidence/staging-walk-a0a81ab5a/walk.md).
task_kind: story
acceptance_criteria:
  - Whether a section, part or heading instruction is already shown in an item, and where a joined instruction stands in an item's body, are decided from the per-paragraph source alignment; no whole-line, prefix or casefold text match remains; the ten recorded exam replays are unchanged except for proven fixes
story: ST-SKRIPT-39-04
backlog_document_profile: contract-derived
---

## Implementation Contract

The R4 rereview of TASK-SKRIPT-39-04-12 (finding 3, low) found that
`docx_section_instructions.py` still decides two things from wording, a rule
dating from TASK-SKRIPT-39-05-03:

- `_printed`: whether an item already shows an instruction or heading line,
  by a whole-line text match against the item's body lines. It decides at the
  heading-run check (line ~415) and in `_body_paragraphs` (line ~273).
- `_renders_one_of`: where a joined instruction, printed inside an item's own
  chunks, stands in that item's body, by a casefold prefix match of each body
  paragraph against the item's later own chunks (`Joined.later`).

TASK-SKRIPT-39-04-12 replaced the equivalent match in `joined_body` with the
per-paragraph source alignment (`AlignedItem.chunks`, `docx_item_alignment`),
and the parent ruled that alignment is admissible structural provenance while
wording matches are not. This task applies the same rule here:

- An item shows a source chunk if and only if one of its body paragraphs is
  aligned to that chunk. A heading or instruction chunk an item shows is not
  added again; any other is added.
- A joined instruction stands before the first body paragraph whose source
  place comes after the instruction's last chunk, with the source-place rule
  `joined_body` already uses for unaligned paragraphs.

Both text matches, `Joined.later` and `folded` are deleted with no fallback.

An instruction chunk the item shows stands in its source form, keeping each
response gap the item placed there at its unique source location. When a gap
has no unique source location, the item's paragraphs aligned to that chunk
stay in their native form (parent ruling 2026-10-18, D10).

## Contract Inputs

- Finding: R4 rereview of TASK-SKRIPT-39-04-12, finding 3 (Hemma, 39-04-12
  lead retained root `evidence/39-04-12/R4/rereview.md`).
- Alignment authority: `docx_item_alignment.AlignedItem`, produced by
  `docx_ai_build.aligned_native_item` and extended by
  `exam_workspace_docx_context_join.joined_body`.
- Probe 2026-10-18 over the ten recorded replays: the heading-run check decides
  30 distinct times (28 on source-review items holding their heading, 2 on a
  converted item whose joined "Text A"/"Text B" contexts it shows), the
  `_body_paragraphs` check never decides, and `_renders_one_of` decides in
  variant 2 and exempelprov.

## Core Vertical And Performance

Every accepted item carries, beside its body, the anchor of the source chunk
each body paragraph shows. Admission records it from the alignment; a
source-review item records its chunks by construction; every later body change
records it too. Section placement reads it. The cost is one tuple per item.

## Validation

- Adversarial unit tests: a reply line that rewords an instruction but is
  aligned to it is not duplicated; a reply that omits the instruction gets it;
  a reworded, unaligned reply line still gets the instruction; an instruction
  whose text also stands as a whole line in a question stem is still added;
  joined placement follows alignment when the reply rewords later lines.
- The ten recorded replays (eight `docx_key_provenance_v14` corpus exams and
  the two `docx_user_exams`) produce identical documents, or each difference is
  shown to be a fix.
- `PYTHONHASHSEED=0 pdm run test-parallel tests/unit/domain/curated_apps tests/unit/application/curated_apps -q`,
  `pdm run lint`, `pdm run typecheck`, `pdm run docs-validate`.

### Replay outcome (2026-10-18)

Before merging `main` at 69ac991ae, nine of the ten recorded replays were
byte-identical (document ids aside). `chapter_4_poetry_and_lyrics_quiz_med_facit`
changed in items 22-28: each reply splits the heading "Part 3, Question N
(1 point)" into `printed_label` "Question N" and a body line "Part 3," aligned
to the heading chunk; the wording check missed that line and prepended a
second copy. TASK-SKRIPT-39-04-12 DEL 4 on `main` fixes the same fragment, so
after the merge all ten replays are byte-identical to `main`.

### Implementation state (2026-10-18)

Implemented on branch `claude/bold-dijkstra-162ba8`; the text matches
`_printed` and `_renders_one_of` are deleted with no fallback. Validation above
passes; the full domain suite runs on Hemma (`~/logs/verify-39-04-13.log`).
Review 7a083063 (changes_requested at df38071df) found F1-F3; the repairs are
D9, D8's gap rule and D4's per-chunk placement, each with a regression test in
`test_exam_workspace_docx_instruction_source_form.py` and
`test_docx_source_form.py`, and the rereview F1 case in
`test_source_provenance.py`. The ten replays stay identical to `main`. F1 and F2
await independent re-review; closeout stays with the reviewer.
Two other wording rules remain outside this contract and are follow-ups:
`_item_without` in `docx_governing_chunks.py` and `wording_left_out` in
`docx_own_instructions.py`.

## Stop Conditions

- A replay difference that is not a proven fix goes to the parent before merge.
- A body producer that cannot state which chunk each paragraph shows goes to
  the parent; it never falls back to wording.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| --- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | Provenance is a per-body-paragraph tuple of chunk anchors (None for a paragraph aligned to no unique chunk) carried with each accepted item from admission to section placement; its length always equals the body's length.                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| D2  | A source-review item's provenance is its chunks, one anchor per paragraph its source rendering produced.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| D3  | An item shows a chunk if and only if some body paragraph's provenance is that chunk; this one rule decides the heading-run check and the omission of carried or joined source paragraphs.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| D4  | A joined instruction is placed as one source-ordered unit: a chunk the item shows keeps its place, and each other chunk stands right after the instruction's paragraphs that precede it in the source; with none, first when the instruction opens the item, otherwise before the first body paragraph whose source place lies after it. An unaligned paragraph takes the place of the aligned paragraph before it (the `joined_body` rule). Review 7a083063 F3.                                                                                                                                                                                                                        |
| D5  | `_printed`, `_renders_one_of`, `Joined.later` and `folded` are deleted; no wording comparison or fallback replaces them.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| D6  | Replay identity is the regression bar: any difference in the ten recorded replays is classified as a proven fix or stops the task.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| D7  | Owning story is ST-SKRIPT-39-04, where the finding arose; ST-SKRIPT-39-05 is done.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| D8  | A carried or joined instruction chunk (not a heading) that the item shows stands in its source form: the body paragraphs aligned to it give way, at the first one's place, to its source paragraphs with marks and pictures, so an echo that drops a picture never loses it. A response gap the item placed there stays at its unique source location (`docx_source_form.source_form`); with no unique location the item's paragraphs stay as they are (review 7a083063 F2; without a unique location, D10). A heading keeps the reply's line, which carries the printed label.                                                                                                         |
| D9  | Each emitted body paragraph carries the source paragraph it was projected from: the exact path names the source block each fragment came from, and the aligned and rebuilt paths their one source paragraph; a paragraph that keeps the model's wording names none. No origin is inferred from an output paragraph's ordinal within a projected span. Source formatting then splits a paragraph where its source chunk changes, a picture taking its own source place (`source_provenance.ChunkProvenance`), so no paragraph is aligned to a chunk whose content it only partly holds and restoring a source form never removes another chunk's text (review 7a083063 F1, rereview F1). |
| D10 | When a response gap the item placed in a shown instruction chunk has no unique source location (`gap_spans` returns None, for example two gaps over one blank), the item's paragraphs aligned to that chunk stay in their native form: no error is caught, nothing is refused, and no content or gap is lost. Parent ruling 2026-10-18 on review 7a083063 F2.                                                                                                                                                                                                                                                                                                                           |
| D11 | `source_formatting.py` stays under the 500-line limit by responsibility: chunk provenance lives in `source_provenance.py` and the word-overlap ranking of source paragraphs, shared by the aligned and rebuilt paths, in `source_paragraph_match.py` (rereview 7a083063 F4).                                                                                                                                                                                                                                                                                                                                                                                                            |
