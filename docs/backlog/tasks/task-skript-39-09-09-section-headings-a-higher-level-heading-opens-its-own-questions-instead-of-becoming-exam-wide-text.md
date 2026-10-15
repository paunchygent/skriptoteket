---
type: task
id: TASK-SKRIPT-39-09-09
title: 'Section headings: a higher-level heading opens its own questions instead of
  becoming exam-wide text'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-15'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
- A DOCX whose Heading 1 section titles each sit above Heading 2 subsections converts
  with every section title placed once, before the first question of its own section,
  in the editor and in the Exam.net QTI export
story: ST-SKRIPT-39-09
backlog_document_profile: contract-derived
---

## Implementation Contract

DOCX conversion places each printed section heading before its own questions.
Today a heading's reach ends at the next section heading of any level, so a
Heading 1 section title ("Del A") directly above a Heading 2 subsection
("Flervalsfrågor") reaches no question. It then becomes document-level text,
which the editor stacks at the top and the QTI export repeats above every
question group (walk evidence: document 08446719, Exam.net import 5339805).

- A heading's reach ends at the next section heading of the same or a higher
  level. A heading chunk without a known level (Heading 4 and deeper) counts as
  deeper than level 3, so documents whose headings share one level keep their
  current placement.
- A section heading whose reach starts at the first question of a parent opens
  that parent's instruction, ahead of the subsection heading. A section heading
  over a single question opens that question's body, as today.

## Contract Inputs

- `docx_instruction_runs.py` (`_span`, `parent_groups`) and
  `docx_section_instructions.py`.
- `DocxSourceParagraph.heading_level`, set by the chunker from TASK-SKRIPT-39-09-08.
- Fixture `formateringsprov_t08.docx` from the TASK-SKRIPT-39-09-08 staging walk.

## Core Vertical And Performance

DOCX chunks with heading levels go through section placement into the native
document, the editor and the QTI export. Placement stays linear in the number
of runs.

## Validation

- Focused unit tests in `test_docx_heading_placement.py`: an H1 above H2
  subsections lands once before its own questions, and same-level headings keep
  their placement.
- Staging walk: convert the fixture, check heading order in the editor, export
  QTI and import it into Exam.net.

## Stop Conditions

- The fix needs a change to the model prompt or the envelope.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| D1  | A heading's reach ends at the next section heading of the same or a higher level; an unknown level counts as deeper than 3. |
| D2  | A section heading whose reach starts at a parent's first question opens that parent's instruction, ahead of the subsection heading. |
| D3  | No other placement rule changes. |
