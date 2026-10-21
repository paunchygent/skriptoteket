---
type: task
id: TASK-SKRIPT-39-10-04
title: The question editor inserts or replaces a picture from a file
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-21'
status: ready
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
  - The question editor has one picture control, Lägg till bild; choosing a picture file inserts it at the cursor, or replaces the selected picture, in every exam
  - The control's look follows huleedu-ui-design and was approved by the user as a mock before the build
story: ST-SKRIPT-39-10
backlog_document_profile: contract-derived
---

## Implementation Contract

The question editor gains one picture control, "Lägg till bild".

- With nothing selected, choosing a picture file inserts the picture at the cursor.
- With a picture selected, the chosen file replaces it.
- It works in every exam, whatever its source, not only PDF imports.

The task runs in two steps:

1. The lead designs the control under huleedu-ui-design and makes a mock. The mock covers placement in the editor toolbar, the glyph, the label and the replace state. The Mac orchestrator takes the mock to the user. Nothing is built before the user approves it.
2. After approval, the lead builds the control.

This task does not depend on TASK-SKRIPT-39-10-01 to 03.

Non-goals: picture resizing, cropping or re-cutting a figure from the original page.

## Contract Inputs

- ST-SKRIPT-39-10 P8 and P9. The Mac plan is in Mac retained root `01a1602d-173d-72ed-b3ac-83c6a24e9070`, `evidence/planning/ST-SKRIPT-39-10/plan.md`.
- The picture node in `examWorkspaceRichTextSchema.ts`, the question editor toolbar, and the existing picture storage and asset limits of the exam document.

## Core Vertical And Performance

A teacher places the cursor in a question, clicks "Lägg till bild", chooses a PNG or JPEG file, and the picture appears at the cursor and is saved with the exam. A teacher who selects a picture and does the same replaces it. The picture follows the exam's existing asset rules and limits.

## Validation

- The mock, approved by the user through the Mac orchestrator, recorded in Progress.
- Focused Vitest for insert at the cursor, replace of the selected picture, a refused file type or size, and saving with the exam, in a signed-in exam and in a guest exam. Backend tests if the build touches the backend.
- fe-type-check and fe-lint, plus backend lint and typecheck if touched.
- A staging walk by the Mac.

## Stop Conditions

- Stop after the mock and wait for the user's approval.
- Stop and report if pictures cannot be added through the existing picture node and asset rules without changing the exam document format.

## Decided Contract Terms

| ID  | Decided contract term                                                           |
| --- | ------------------------------------------------------------------------------- |
| T1  | ST-SKRIPT-39-10 P8 applies as written.                                          |
| T2  | Mock first. The user approves it through the Mac orchestrator before any build. |

## Progress

### 2026-10-21 (Hemma orchestrator)

- Scaffolded from the ST-SKRIPT-39-10 story terms. The story is `ready` by the user's grilling of 2026-10-21, relayed by the Mac orchestrator. This task is `ready` for its mock step, and a lead session is assigned.
