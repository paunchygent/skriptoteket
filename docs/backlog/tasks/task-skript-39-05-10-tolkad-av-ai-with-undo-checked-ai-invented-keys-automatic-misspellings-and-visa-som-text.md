---
type: task
id: TASK-SKRIPT-39-05-10
title: Tolkad av AI with undo, checked AI-invented keys, automatic misspellings and
  Visa som text
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-14'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
- An AI-interpreted key carries the AI glyph with an undo that clears it and shows the teacher's facit text
- A key the AI invented without a facit carries the AI glyph and the review warning and blocks export until marked reviewed
- Gap answers from the facit carry removable automatic misspellings that reach the QTI export
- Visa som text turns a gap into plain text, disabled on the item's last gap
- The staging walk and the Exam.net import of its QTI export pass
story: ST-SKRIPT-39-05
backlog_document_profile: contract-derived
---

## Implementation Contract

Delivers ST-SKRIPT-39-05 item 5 (story terms A8-A11): the teacher sees what
the AI decided and can take it back, and is asked only about keys the AI
invented.

- **Key source.** The DOCX conversion model states each item's key source:
  copied from the teacher's facit, interpreted from it, or invented without
  a facit. Today `docx_ai_build.py` saves every returned key as
  `source_provided`, so invented keys pass export unchecked.
- **Interpreted keys.** Copying the facit's own answer words is not
  interpretation: a letter mapped to its option, or listed alternatives
  ("Stockholm/Sthlm", "eller") split into accepted answers. Extracting a
  gap word from a facit sentence or building matching pairs from prose is.
  An interpreted key is export-eligible and the item shows the AI glyph
  established in the DOCX-to-QTI converter (`IconAi` status symbol, one per
  item, with an accessible label) plus an undo.
- **Undo** clears the interpreted key, shows the teacher's original facit
  text beside the item and leaves the key empty; the existing missing-key
  blocker stops export until the teacher sets it.
- **Glyph lifetime.** The glyph on an interpreted key goes away when the
  teacher clicks undo, changes the key, or clicks "Markera som granskad".
- **Invented keys** are saved as `machine_proposed`: the item shows the AI
  glyph and the existing review-required warning, has no undo, and blocks
  export until "Markera som granskad".
- **Misspellings.** At conversion, for gap answers from the facit, the
  model proposes likely misspellings and code keeps those within the A10
  distance in `answer_spelling.py` (1 edit up to 6 characters, 2 longer),
  at most 3 per answer. They show as extra accepted answers marked
  "automatisk", each removable by the teacher, and carry no AI glyph.
- **Visa som text.** The gap popover gets a "Visa som text" button that
  replaces the gap with its first accepted answer as plain text in the
  sentence. On the item's last gap the button is disabled with an
  explanation. Item points stay unchanged.
- **QTI accepted values.** The export writes every accepted value of a gap,
  also when the gap has no own points (`examnet_qti_xml.py` drops all but
  the first today).

Out of scope: adding misspellings after conversion when the teacher edits
an answer (a later feature), redoing an undone interpretation (per-question
retry already exists), and keys from the answer-key suggestion button.

## Contract Inputs

- ST-SKRIPT-39-05 terms A8-A12 and A14.
- Conversion: `domain/curated_apps/exam_workspace/docx_ai_build.py`,
  `docx_ai_contracts.py`, `docx_ai_schema.py`,
  `application/curated_apps/handlers/exam_workspace_docx_build_rounds.py`.
- Native model and export rules: `native_exam_document.py`,
  `native_exam_vocabulary.py` (`NativeAnswerKeyOrigin`),
  `native_exam_export_rules.py`, `answer_spelling.py`.
- QTI: `exam_conversion/examnet_qti_xml.py` (`_append_gap_response_declaration`).
- Frontend: `exam-workspace/ExamWorkspaceGapPopover.vue`,
  `ExamWorkspaceBodyEditor.vue`, `ExamWorkspaceItemEditor.vue` ("Markera som
  granskad"), `ExamWorkspaceItemTable.vue`, `examWorkspaceItemEdits.ts`; the
  glyph precedent in `exam-converter-authenticated/ExamConverterQuestionTable.vue`
  and `ExamConverterQuestionNavigator.vue`.
- Retained plan: Skriptoteket session `01a13a87-acac-7730-bb4e-746618d73cfd`.

## Core Vertical And Performance

Walking skeleton: one corpus DOCX with facit uploads on staging, converts in
the background job, and opens with at least one interpreted key, one gap
with automatic misspellings, and one invented key; the teacher works through
them in the editor, saves, and the QTI export imports into Exam.net with the
expected keys. Key source and misspelling candidates come from the existing
batched conversion calls; no extra model call per item.

## Validation

Done means a green agent-driven staging walk on the pushed `main` revision,
with the result read back from Exam.net:

1. Upload a corpus exam with facit and wait for the conversion.
2. An interpreted key shows the AI glyph; undo clears the key, shows the
   facit text, and export is blocked until the teacher sets the key.
3. Another interpreted key loses its glyph on "Markera som granskad".
4. A gap answer shows its "automatisk" misspellings; remove one.
5. An item whose key was invented shows the AI glyph and the review warning,
   export is blocked, and "Markera som granskad" unblocks it.
6. "Visa som text" turns one gap into text; on a last gap the button is
   disabled with its explanation.
7. Save, export QTI, import it into Exam.net: the kept misspellings are
   accepted answers of their gap, the removed one is absent, and the gap
   turned into text is plain text.

The corpus eval run stays at its current pass level.

## Stop Conditions

- The conversion model cannot state key source reliably on the corpus
  (interpreted or invented keys misreported in the eval run).
- Exam.net does not accept several accepted values for a gap without own
  gap points.
- A change needs a term outside this contract.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| D1 | An AI-interpreted key is marked with the AI glyph and status semantics of the DOCX-to-QTI converter, one per item with one undo (user decision 2026-10-14). |
| D2 | Undo clears the interpreted key, shows the teacher's facit text beside the item and leaves the key empty, so the missing-key blocker stops export (user decision 2026-10-14). |
| D3 | Automatic misspellings are visible extra accepted answers marked "automatisk", each removable, with no AI glyph (user decision 2026-10-14). |
| D4 | The conversion model states each key's source; a key invented without a facit is `machine_proposed` and blocks export until marked reviewed (user decision 2026-10-14). |
| D5 | Only real interpretation gets the glyph: copying the facit's answer words, including splitting listed alternatives, does not (user decision 2026-10-14). |
| D6 | "Visa som text" replaces a gap with its first accepted answer as text; disabled with an explanation on the item's last gap; points unchanged (user decision 2026-10-14). |
| D7 | Misspellings are added at conversion only, for facit gap answers, within the A10 distance, at most 3 per answer; adding them after conversion is a later feature outside the current stories (user decision 2026-10-14). |
| D8 | The glyph on an interpreted key goes away on undo, a teacher change of the key, or "Markera som granskad" (user decision 2026-10-14). |
| D9 | An invented key shows the AI glyph plus the review-required warning and has no undo (user decision 2026-10-14). |
| D10 | The QTI export writes every accepted value of a gap, also without own gap points (parent decision 2026-10-14, defect found in discovery). |
