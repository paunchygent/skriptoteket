---
type: task
id: TASK-SKRIPT-40-04-06
title: Exam texts edit as one document per field, exam instructions are editable and printed totals can be accepted
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
  approval_evidence: Independent ruthless-reviewer 1122a276 (Pi, Sol 6.1 high) approved 4f9f6945b on re-review after F1-F6 repairs; merged into main as af5b147a0 and published with a stale-spec fix in a0a81ab5a after the Hemma full typecheck and test pass; staging walk at a0a81ab5a on omprov_grammatik_sve2.docx deleted an underscore line, edited the exam instruction with a hard break (exported as br in QTI) and accepted a printed total with no layout shift (root 01a14e1f evidence/staging-walk-a0a81ab5a/walk.md).
task_kind: story
acceptance_criteria:
  - A teacher deletes a selection spanning paragraphs, gaps or pictures, merges paragraphs with Backspace and removes an underscore line in question text, part instructions and exam instructions; the change autosaves, survives reload and Ångra restores it
  - Clicking Instruktioner opens the exam instruction in the main editor; an exam without one shows Lägg till instruktioner
  - Each amber printed-total line offers Använd N p and the footer clears every printed total at once; both undo with Ångra
  - A question with empty text is a red export blocker before the click that one click reaches
story: ST-SKRIPT-40-04
backlog_document_profile: contract-derived
---

## Implementation Contract

Teachers cannot remove a line from an imported exam today. Every paragraph is its own editable box (`ExamWorkspaceBodyParagraph.vue`), an emptied paragraph is refused and restored on focus-out, the backend refuses an empty paragraph (`native_exam_body.py:96`), and no command deletes or merges paragraphs. The exam instruction is shown read-only above the question list, and the amber printed-total signal offers no action.

This task makes every exam text field (question text, part instruction, exam instruction) one TipTap 3 document that edits like a word processor (D1, D2), removes the never-empty rule end to end (D3), makes the exam instruction editable from the question list (D5), and lets teachers accept the computed total per level or everywhere at once (D6, D7). An empty question text blocks export through the existing red blocker path (D4).

Non-goals: the writing-area editor and dropping underscore answer lines on import (TASK-SKRIPT-40-04-07, D8); any converter change; editing a printed total to a new number.

## Contract Inputs

- User grilling 2026-10-18; staging walk at 36b1d352 (document 88cafb3d) reproducing the reverting line delete.
- Current code: `ExamWorkspaceBodyParagraph.vue:302-337`, `ExamWorkspaceBodyEditor.vue`, `ExamWorkspaceInstructionEditor.vue`, `ExamWorkspaceRichTextEntry.vue`, `ExamWorkspaceQuestionList.vue` (intro slot), `examWorkspaceTotals.ts`, `examWorkspaceBlockers.ts`, `ExamWorkspaceExportBlockers.vue`; backend `native_exam_body.py:96`, `native_exam_document.py:90`, `native_exam_parent.py:46`.
- Reference editor: HuleEdu `frontend/src/components/human-cj/HumanCJDocumentEditor.vue`, `lib/human-cj-editor-schema.ts`, `lib/human-cj-editor-document.ts` (TipTap 3.31.3, one ProseMirror document, explicit extensions, two-way mapping to the stored format).

## Core Vertical And Performance

The core vertical is one shared exam rich-text editor: a TipTap schema whose paragraphs and headings carry the existing marks, with gaps and pictures as inline atom nodes, and one mapping between the editor document and the stored body paragraphs. Question text, part instructions and the exam instruction all use it. Edits flow through the existing document edit, autosave and undo history; a gap deleted from a body leaves the question with no record of it. Printed-total accept clears `printed_total` on the header or a parent through ordinary document edits.

Units: (1) backend: drop the empty-paragraph rule and allow empty bodies and instructions, keep gap records consistent with the body, add the empty-question-text blocker; (2) the shared TipTap editor and mapping, replacing the per-paragraph editor in question text and part instructions; (3) the exam instruction entry and editor; (4) the per-line and footer printed-total actions. Performance is not material; one editor instance per open field.

## Validation

- Vitest for the editor mapping round trip (marks, headings, gaps, pictures, empty document), selection delete across paragraphs and atoms, paragraph merge, and Enter and Shift+Enter.
- Vitest for the exam instruction entry, the printed-total actions and their undo, and the empty-question-text blocker.
- Focused backend tests for empty bodies, empty instructions, gap consistency and the blocker.
- Frontend typecheck and build; lint and typecheck for the touched backend domain.
- A staging walk deleting an underscore line, editing the exam instruction and accepting a printed total on the omprov fixture.

## Stop Conditions

Stop and report to the parent when TipTap cannot represent a stored body construct without loss, when gap or picture records cannot follow a selection delete without changing the stored format beyond D1-D7, or when an export path reads `printed_total`.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                                                                                                                                  |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| D1  | Every exam text field (question text, part instruction, exam instruction) is one TipTap 3 document: selecting across paragraphs and pressing Backspace deletes the selection, Backspace at a paragraph start merges, an emptied paragraph can be removed, Enter starts a paragraph and Shift+Enter breaks the line, as in the HuleEdu CJ admin editor. |
| D2  | A highlighted selection deletes gaps and pictures in it without confirmation; Ångra restores them.                                                                                                                                                                                                                                                     |
| D3  | The never-empty paragraph rule is removed in the SPA and the backend; any text may be empty while editing and autosave keeps it.                                                                                                                                                                                                                       |
| D4  | A question with empty text is a red export blocker before the click that one click reaches; an empty part instruction is allowed and not printed; clearing the exam instruction removes it.                                                                                                                                                            |
| D5  | Clicking Instruktioner in the question list opens the exam instruction in the main editor with the part-instruction editor; an exam without one shows a quiet Lägg till instruktioner entry there.                                                                                                                                                     |
| D6  | Each amber printed-total line, exam or part, offers one-click Använd N p that clears that printed total; Ångra restores it; reaching the printed number stays a points edit.                                                                                                                                                                           |
| D7  | While any level differs, the footer offers one action that clears the exam and every part printed total at once; Ångra restores them.                                                                                                                                                                                                                  |
| D8  | The writing-area editor for printed DOCX and PDF and the converter dropping underscore answer lines belong to TASK-SKRIPT-40-04-07, planned in its own grilling; this task does not change the converter.                                                                                                                                              |
