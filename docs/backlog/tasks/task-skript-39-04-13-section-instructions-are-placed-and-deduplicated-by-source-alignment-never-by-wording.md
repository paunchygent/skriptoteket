---
type: task
id: TASK-SKRIPT-39-04-13
title: Section instructions are placed and deduplicated by source alignment, never by wording
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

Nine of the ten recorded replays produce byte-identical documents (document ids
aside). `chapter_4_poetry_and_lyrics_quiz_med_facit` changes in items 22-28 only,
and the change is a fix: each reply splits the heading "Part 3, Question N
(1 point)" into `printed_label` "Question N" and a body line "Part 3," that
the alignment maps to the heading chunk. The wording check did not match that
line and prepended a second copy, "Part 3, Question N". The item now shows its
heading once. The gold prompt for these questions has no heading line.

## Stop Conditions

- A replay difference that is not a proven fix goes to the parent before merge.
- A body producer that cannot state which chunk each paragraph shows goes to
  the parent; it never falls back to wording.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                            |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | Provenance is a per-body-paragraph tuple of chunk anchors (None for a paragraph aligned to no unique chunk) carried with each accepted item from admission to section placement; its length always equals the body's length.     |
| D2  | A source-review item's provenance is its chunks, one anchor per paragraph its source rendering produced.                                                                                                                         |
| D3  | An item shows a chunk if and only if some body paragraph's provenance is that chunk; this one rule decides the heading-run check and the omission of carried or joined source paragraphs.                                        |
| D4  | A joined instruction is inserted before the first body paragraph whose source place lies after the instruction's last chunk; an unaligned paragraph takes the place of the aligned paragraph before it (the `joined_body` rule). |
| D5  | `_printed`, `_renders_one_of`, `Joined.later` and `folded` are deleted; no wording comparison or fallback replaces them.                                                                                                         |
| D6  | Replay identity is the regression bar: any difference in the ten recorded replays is classified as a proven fix or stops the task.                                                                                               |
| D7  | Owning story is ST-SKRIPT-39-04, where the finding arose; ST-SKRIPT-39-05 is done.                                                                                                                                               |
