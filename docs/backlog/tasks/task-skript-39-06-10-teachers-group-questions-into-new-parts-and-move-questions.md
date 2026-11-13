---
type: task
id: TASK-SKRIPT-39-06-10
title: Teachers group questions into new parts and move questions into, out of and between parts
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: "2026-10-18"
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: ruthless-reviewer
  decided_at: '2026-10-18'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: Independent ruthless-reviewer 47f15e2d review changes_requested (F1 high, F2-F8; root 01a14e6d evidence/reviews/47f15e2d-1489-4434-8fcf-e662fe6bb770.md); F2-F8 admitted on focused proof (evidence/lead-2061895e/final-report.md); re-review cleared F1 and found F9 high (-rereview.md); second re-review approved F9 at 7667692c (-rereview2.md); merged into main. Staging walk follows with the 40-04-07 merge (v8 seam).
task_kind: story
acceptance_criteria:
  - A teacher groups marked standalone questions into a new part, adds an empty part with Ny del, and moves a question into, out of and between parts with Flytta till, each as one undoable step
  - A part with no questions stays in the exam, exports to Exam.net as an information block holding its instruction, prints as an instruction block, and never blocks export
story: ST-SKRIPT-39-06
backlog_document_profile: contract-derived
---

## Implementation Contract

Teachers cannot restructure parts today. A part (`NativeExamParent`) has no stored place in the document: it sits where its first question sits (`native_exam_parent.py:30-46`), its `item_ids` needs at least one question, and the commands from TASK-SKRIPT-39-06-03 and 39-06-07 only add, delete and reorder questions inside one part. Deleting a part's last question also removes the part (39-06-07 D5).

This task lets the teacher group questions into new parts and move questions between parts, and it makes a part with no questions a valid instruction block (G1, G5, G8). In "Markera" mode the teacher ticks standalone questions and creates a part from them (G2, G10, G11). "Ny del" adds an empty part (G9), and "Flytta till…" in the question menu moves one question (G3, R3). A new part opens its empty instruction in the editor (G4). A part gets its own place in the document order (R1). A part with no questions exports to Exam.net as an information block and prints as an instruction block. If its instruction is also empty, it is skipped (G5, R2).

Non-goals: drag and drop; marking questions that already sit in a part; converter changes.

## Contract Inputs

- User grilling 2026-10-18 through lead f193466c and in this session; this reverses story ST-SKRIPT-39-06 P7 and replaces TASK-SKRIPT-39-06-07 D5.
- Exam.net probe 2026-10-18 (exams 5345638 and 5345641): an item whose body holds text and no interaction imports as an unnumbered Informationsblock. A lone rubric block loses its text.
- Current code:
  - model: `native_exam_parent.py:30-91`, `native_exam_document.py:112-164`;
  - commands and routes: `native_exam_parent_commands.py`, `handlers/exam_workspace_parents.py`, `web/api/v1/apps_conversion_hub_exam_workspace_parents.py`;
  - first-question readers: `examnet_qti_export.py:64-88,158-215`, `examnet_pdf_export.py:319`, `exam_workspace_docx_writer.py:109`, `docx_section_points.py:127-130`;
  - frontend: `examWorkspaceStructure.ts:37`, `examWorkspaceListEntries.ts:129-138`, `useExamWorkspaceStructure.ts`, `ExamWorkspaceQuestionList.vue`, `ExamWorkspaceQuestionRow.vue`, `ExamWorkspaceQuestionHead.vue`, `src/api/examWorkspace.ts`.

## Core Vertical And Performance

The core vertical is a part with its own place in the document order. One ordering owner decides where each part and question sits, and every reader uses it: the commands, QTI, PDF, DOCX, printed totals and the left column. That replaces the first-question lookups.

The vertical is proven end to end through the API. It groups two non-adjacent questions, moves one question out and deletes the other. It then exports QTI, PDF and DOCX, and the Exam.net import shows one information block.

Units:

1. **Document model:** the part's stored place, zero-question parts, and the validators (consecutive questions, no ordering questions as children).
2. **Commands and routes:** group marked questions, move a question (into a part, out of it, or between parts), create an empty part, and keep the part when its last question is deleted. Each command uses the 39-06-03 pattern: one route, the concurrency guard, one undo step and no file write until Spara.
3. **Exports:**
   - QTI writes a childless part as a plain item whose body holds the instruction and no interaction.
   - PDF and DOCX print the instruction block in place.
   - An empty childless part is skipped everywhere.
4. **Frontend:** Markera mode with checkboxes and "Skapa del av markerade", "Ny del", "Flytta till…", and rows for childless parts.
5. **Staging walk and Exam.net import.**

No material performance concern.

## Validation

- Focused backend tests:
  - the model and validators, including zero questions and ordering questions refused;
  - each command, including non-adjacent grouping, the first-marked placement, delete of the last question keeping the part, the concurrency conflict, and one undo step restoring the exact state;
  - QTI, PDF and DOCX for a childless part and for an empty childless part.
- Vitest for Markera mode, "Flytta till…", "Ny del" and childless part rows. Frontend typecheck and build. Lint and typecheck for the touched backend domains.
- A staging walk that:
  - groups two non-adjacent omprov questions, moves one out and deletes the other;
  - adds a "Ny del";
  - exports QTI, PDF and DOCX;
  - imports the QTI into Exam.net and finds one information block.

## Stop Conditions

Stop and report to the parent in any of these cases:

- implementation would start before TASK-SKRIPT-40-04-06 is merged;
- a shared PDF or DOCX printing file conflicts with TASK-SKRIPT-40-04-07 in a way the two leads cannot settle;
- Exam.net does not import a childless part as an information block.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                                                                         |
| --- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| G1  | Teachers group one or more standalone questions into a new part with a shared instruction. They move a question into a part, out of a part to standalone, and from one part to another (user 2026-10-18; reverses story P7).                  |
| G2  | A teacher marks several questions with checkboxes in the question list, and a toolbar action creates a part from them (user 2026-10-18).                                                                                                      |
| G3  | "Flytta till…" in a question's menu lists the parts and "Ingen del (fristående)" (user 2026-10-18).                                                                                                                                           |
| G4  | A new part starts with an empty instruction and opens in the instruction editor. An empty instruction is allowed, not printed and has no printed total (user 2026-10-18; 40-04-06 D4).                                                        |
| G5  | A part may hold no questions. It then exports to QTI as a plain item whose body holds its instruction text and no interaction, which Exam.net imports as an information block, and it never blocks export (user 2026-10-18 after the probe).  |
| G6  | A part's questions stay consecutive, so grouping non-adjacent questions moves them together. Ordering questions are never part members, and the action is refused with a named reason (story P3).                                             |
| G7  | Every command has one API route, the concurrency guard and one undo step, and none writes the file before Spara. The task ships workspace controls and a real-browser walk (39-06-03 pattern).                                                |
| G8  | Deleting a part's last question keeps the part as an instruction block, like moving the question out. "Ta bort instruktion" removes the part. This replaces TASK-SKRIPT-39-06-07 D5 (user 2026-10-18).                                        |
| G9  | "Ny del" in the add menu creates an empty part at the insertion point, with an empty instruction and the editor open (user 2026-10-18).                                                                                                       |
| G10 | A new part made from non-adjacent questions takes the place of the first marked question. The other marked questions move up to it in their current order, and the questions in between follow the part (user 2026-10-18).                    |
| G11 | Only standalone questions get a checkbox. A question already in a part moves with "Flytta till…" (user 2026-10-18).                                                                                                                           |
| G12 | Implementation starts after TASK-SKRIPT-40-04-06 is merged and runs on Hemma in parallel with TASK-SKRIPT-40-04-07. The two leads coordinate the PDF and DOCX printing files (user 2026-10-18).                                               |
| R1  | A part has its own stored place in the document order, so a part with no questions keeps its position. The exporters, printers, printed totals and the left column read that place.                                                           |
| R2  | A part with no questions prints its instruction as a text block in its place in the PDF and DOCX. If the instruction is also empty, the part is skipped in QTI, PDF and DOCX and never blocks export.                                         |
| R3  | A question moved into a part lands at the end of that part.                                                                                                                                                                                   |
| R4  | A question moved out to "Ingen del (fristående)" lands directly after the part it left; the part keeps its place and its remaining questions, and a part left with no questions stays as an instruction block (Mac parent ruling 2026-10-18). |
