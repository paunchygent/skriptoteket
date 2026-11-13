---
type: story
id: ST-SKRIPT-39-10
title: Teachers import exams from PDF files that contain text into the exam workspace
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-21'
status: ready
closeout_review:
  record: inline
  status: not_started
epic: EPIC-SKRIPT-39
acceptance_criteria:
- A teacher's exam saved as a PDF with text opens in the exam workspace with the same
  questions, points and types as the same exam imported from Word
links:
  decisions: []
backlog_document_profile: contract-derived
---

## Slice Contract

A teacher drops or chooses a PDF exam in the exam workspace import box, the same box that takes Word, DigiExam and QTI files, and the exam opens in the editor as a Word import does. The target is an exam the teacher wrote in Word or Google Docs and saved as a PDF with selectable text; publisher and textbook PDFs work on a best-effort basis.

- The PDF is read locally into the same chunk sequence the Word import produces (paragraphs, headings, tables, pictures), then runs the existing AI grouping, labeling, conversion, review, points warning and export path unchanged. PDF import adds no new AI call site, so ST-SKRIPT-41-01 carries it to the LLM provider door with the Word import.
- Repeated page headers, footers and page numbers are dropped, two-column pages read column by column, and drawn answer lines are dropped as in the Word import.
- Pictures placed in the PDF come along with their question. Figures drawn with lines (charts, geometry, shapes) are cut out of the page generously, with the whole drawing, its labels and a margin, and placed in their question as a picture.
- A PDF without text, or whose text layer is mostly unreadable, imports nothing and shows a clear stop message telling the teacher to save the exam as Word or as a PDF from the original. When only some pages lack readable text, the readable pages import and a note names the skipped pages.
- The question editor gains one picture control, "Lägg till bild": choosing a picture file inserts it at the cursor, or replaces the selected picture. It works in every exam, not only PDF imports.
- Access follows the Word import: signed-in teachers with AI access; guests get the sign-in prompt, which names PDF with DigiExam and Word. Behaviour is designed and judged as if AI is on for teachers; the temporary REP-0044 admin-only gate is not part of this story.

Out of this slice: scanned-PDF support (OCR), re-cutting a figure from the original page, picture resizing, and publisher-layout parity.

## Contract Inputs

- EPIC-SKRIPT-39 item 06 and E10 (digital PDFs parse locally; scanned PDFs deferred); ST-SKRIPT-39-04 task 12 (reuse the native document and review path).
- User grilling 2026-10-21 in the Mac orchestration session; retained root `01a1602d-173d-72ed-b3ac-83c6a24e9070`, plan `evidence/planning/ST-SKRIPT-39-10/plan.md`, decisions P1-P9.
- `infrastructure/documents/pdf_text_extraction.py` (pdfplumber; pypdf and pypdfium2 are also declared), `infrastructure/curated_apps/apps/conversion_hub/exam_workspace_docx_chunker.py`, `application/curated_apps/handlers/exam_workspace_docx_pipeline.py`, the import box in `views/apps/exam-workspace/ExamWorkspaceOpenDrawer.vue` and `useExamWorkspaceSourceFile.ts`, and the picture node in `examWorkspaceRichTextSchema.ts`.
- ST-SKRIPT-41-02 P1 (guests use no AI); ST-SKRIPT-41-01 (the LLM provider door).

## Tasks

The Hemma orchestrator owns this story and gives each task to its own lead, one task per lead.

1. Walking skeleton: one Word corpus exam saved as PDF goes through the import box and opens in the exam workspace on staging, text only, through the shared import path.
2. Embedded pictures and cut-out drawn figures land in their questions.
3. No-text and unreadable pages: the stop message and the skipped-pages note.
4. "Lägg till bild" in the question editor: a mock approved by the user first, then the build. It does not depend on tasks 1-3.
5. Proof pass: the proof set is compared with its Word imports on staging.

## Verification

Focused tests per task. The closing proof is one staging walk over the proof set: Word corpus exams saved as PDF from Microsoft Word, plus two or three real PDF exams the user supplies in `.artifacts/pdf-import-proof/`. Each PDF import gives the same questions, types and points as the Word import of the same exam, with pictures and cut-out figures in the right questions; any difference shows as a visible review item. Best effort, one pass, no repeated corpus runs.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| P1  | The target PDFs are teachers' own exams written in Word or Google Docs and saved as PDF with selectable text; publisher PDFs are best effort. Proof uses Word corpus exams saved as PDF plus two or three real PDF exams from the user. |
| P2  | A PDF with no text imports nothing and shows a clear stop message telling the teacher to save the exam as Word or as a PDF from the original; when only some pages lack text, the text pages import and a note names the skipped pages. Scanned-PDF support stays deferred. |
| P3  | Embedded pictures come along with their question, and figures drawn with lines are cut out of the page as a picture and placed in their question in the first version (user 2026-10-21, changing the first placeholder answer). |
| P4  | PDF import follows Word import access: signed-in teachers with AI access; guests get the sign-in prompt. Behaviour is judged as if AI is on for teachers; the REP-0044 admin-only gate is not part of this story. |
| P5  | Digital PDFs parse locally into the Word import's chunk sequence and run the existing conversion, review, points-warning and export path unchanged, with no new AI call site. |
| P6  | Closure bar: on the proof set each PDF import gives the same questions, types and points as the Word import of the same exam, with pictures and cut-out figures in the right questions; any difference shows as a visible review item. Best effort, judged on one staging walk pass, no repeated corpus runs. |
| P7  | Pages whose text layer is mostly unreadable follow the no-text rule of P2. |
| P8  | Figures are cut generously. The question editor gains "Lägg till bild", which inserts a chosen picture file or replaces the selected picture, in every exam; its look follows huleedu-ui-design and is shown to the user as a mock before it is built. |
| P9  | Five tasks in the order above, walking skeleton first; the Hemma orchestrator owns the story and runs one lead per task. |
