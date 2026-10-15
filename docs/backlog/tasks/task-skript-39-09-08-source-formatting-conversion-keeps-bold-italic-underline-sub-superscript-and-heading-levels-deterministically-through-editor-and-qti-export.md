---
type: task
id: TASK-SKRIPT-39-09-08
title: 'Source formatting: conversion keeps bold, italic, underline, sub/superscript
  and heading levels deterministically through editor and QTI export'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-15'
status: ready
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
- Converting a DOCX keeps bold, italic, underline, superscript and subscript on every student-visible text run, copied by code from the source runs and never chosen by the model.
- Title and Heading 1-3 paragraphs, and whole paragraphs set clearly larger than the body text, become heading levels 1-3.
- When the model's text cannot be matched to the source runs, the text is rebuilt from the source runs with their formatting; if that also fails the question goes to Granska with a formatting reason. Formatting is never dropped silently.
- The editor shows the formatting and lets the teacher toggle it with Ctrl/Cmd+B/I/U and a compact glyph toolbar (B, I, U, sup, sub, heading level).
- The QTI export writes the formatting as strong, em, u, sup, sub and h1-h3, and an Exam.net import of a walked export shows it.
story: ST-SKRIPT-39-09
backlog_document_profile: contract-derived
---

## Implementation Contract

Conversion keeps the source document's formatting on all student-visible
text, deterministically. The model never decides whether formatting survives:
code copies it from the DOCX runs.

**Kept marks:** bold, italic, underline, superscript and subscript. Colour and
highlight are not kept.

**Heading levels:** a paragraph styled Title or Heading 1-3 becomes heading
level 1-3. A whole paragraph whose text is set clearly larger than the
document's body size also becomes a heading level, by fixed size thresholds
the implementation lead chooses and documents. Larger words inside a sentence
keep only their marks, because Exam.net does not render inline font sizes
(probe r20).

**Where:** question text, shared instructions for grouped questions, exam
instructions, choice options and matching entries. Criteria and facit stay
plain because students never see them.

**Deterministic copy:** the DOCX reader records each run's marks and each
paragraph's heading level with source offsets. After the model returns its
segments, code matches every returned text segment to the source text and
applies the source formatting to the matched span. An inline facit answer
that becomes a gap carries no formatting. When a returned text cannot be
matched, code rebuilds that text from the source runs with their formatting
and keeps the model's gaps; if that also fails, the question goes to
Granska with the Swedish reason "Formateringen kunde inte föras över". Formatting is never dropped
silently.

**Stored document:** the native document stores marks on text and heading
levels on paragraphs. The repository has no backward compatibility: the old
plain format and its readers are removed, not kept beside the new one.

**Editor:** the exam workspace editor renders the formatting and lets the
teacher add and remove it on selected text with Ctrl/Cmd+B, I and U and a
compact glyph toolbar (B, I, U, superscript, subscript, heading level),
following `huleedu-ui-design`. Editing text keeps the marks of the text it
edits.

**Export:** the QTI export writes the marks as `strong`, `em`, `u`, `sup` and
`sub` and heading levels as `h1`-`h3`, in item bodies, prompts, shared
instructions, choice options and matching entries. Probe r20 (Exam.net
5339086) proved that Exam.net keeps and renders `em`, `i`, `strong`, `b`,
`u`, `h1`-`h3` and `small`, and does not render inline font-size styles.
Superscript and subscript are not yet proven in Exam.net and are proven by
this task's walk.

Out of scope: colour, highlight, fonts, lists, tables and alignment; the
DigiExam converter lane.

## Contract Inputs

- Story `ST-SKRIPT-39-09`; user decisions 2026-10-15 (formatting round).
- Probe r20 evidence: `.orchestration/context/sessions/01a13c92-d70e-765f-ae36-b6583539e201/evidence/probe-r20/readback.md`.
- DOCX reader `src/skriptoteket/infrastructure/curated_apps/apps/conversion_hub/exam_workspace_docx_chunker.py`
  (`_paragraph_render` reads only `run.italic`; heading by style prefix) and
  chunk shapes `src/skriptoteket/domain/curated_apps/exam_workspace/docx_chunks.py`
  (`marked_text` wraps italics for the model).
- Mark and style lookup with style fallback already exists in
  `exam_workspace_labeler_block_image.py` (`_font_flag`) and
  `exam_workspace_labeler_markdown.py`.
- Producer contract `src/skriptoteket/domain/curated_apps/exam_workspace/docx_ai_contracts.py`
  and admission `src/skriptoteket/application/curated_apps/handlers/exam_workspace_docx_build_admission.py`.
- Native model `src/skriptoteket/domain/curated_apps/exam_workspace/native_exam_body.py`
  (`NativeTextSegment`, `NativeParagraph`), choices and matching entries.
- Export `src/skriptoteket/domain/curated_apps/exam_workspace/examnet_qti_prompt.py`
  (`prompt_paragraphs`) and `src/skriptoteket/domain/curated_apps/exam_conversion/examnet_qti_inline_prompt.py`.
- Editor `frontend/apps/skriptoteket/src/views/apps/exam-workspace/ExamWorkspaceBodyEditor.vue`
  and `examWorkspaceBodySegments.ts` (`renderParagraphElement`, contenteditable).
- Fixture: `svenska_2_kursavslutande_prov_med_facit.docx` (Fråga 17: italic
  phrases "tre korta svar", "på skolgården", "kan vila").

## Core Vertical And Performance

A teacher uploads the Svenska 2 exam. Fråga 17 shows its three phrases in
italics in the editor, the teacher makes one word bold with Ctrl/Cmd+B and
saves, exports QTI, and the Exam.net import shows the italics, the bold word
and the exam's headings. Matching and copying formatting is linear in the
source text; no material performance concern.

## Validation

- Focused unit tests: reader marks and heading levels (direct, character-style
  and paragraph-style formatting; size-based headings); the deterministic
  copy on recorded corpus replies, including an inline facit answer that
  becomes a gap, a model text that does not match and is rebuilt, and the
  Granska fallback; export XHTML for every mark and heading level.
- Focused Vitest for rendering, shortcut and toolbar toggling, and keeping
  marks while editing.
- Agent-driven staging walk and an Exam.net import of the walked package,
  including superscript and subscript.

## Stop Conditions

- Exam.net drops or does not render superscript or subscript.
- Model replies cannot be matched to source text often enough that rebuilt or
  Granska items appear on ordinary corpus questions.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| F1  | Bold, italic, underline, superscript and subscript are kept; colour and highlight are not. |
| F2  | Title and Heading 1-3 styles, and whole paragraphs clearly larger than body text by fixed thresholds, become heading levels 1-3; inline size changes keep only their marks. |
| F3  | Code copies formatting from the source runs; the model never decides it. An unmatched text is rebuilt from source runs, else the question goes to Granska; formatting is never dropped silently. |
| F4  | Formatting applies to question text, shared and exam instructions, choice options and matching entries; criteria and facit stay plain. |
| F5  | The editor shows formatting and toggles it with Ctrl/Cmd+B/I/U and a compact glyph toolbar (B, I, U, sup, sub, heading level). |
| F6  | The QTI export writes strong, em, u, sup, sub and h1-h3; the old plain format is removed without compatibility readers. |
