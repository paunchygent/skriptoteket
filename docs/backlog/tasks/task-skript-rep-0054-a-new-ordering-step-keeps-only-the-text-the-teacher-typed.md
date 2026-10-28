---
type: task
id: TASK-SKRIPT-REP-0054
title: A new ordering step keeps only the text the teacher typed
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-28'
status: ready
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
  - A step added with Lägg till steg and typed into at once is saved without a leading space
  - The Exam.net QTI export of that step carries no leading space
backlog_document_profile: contract-derived
---

## Implementation Contract

In the exam workspace, an ordering question (Ordna, TASK-SKRIPT-39-06-08) step that the teacher adds with "Lägg till steg" and types into at once is saved with a leading space the teacher did not type: the Mac staging walk of 2026-10-28 at 05b3fc12a saved " Analysera resultatet", and the QTI export carried `<p> Analysera resultatet</p>`. Find where the space enters (the new step's initial text, the editor, or the save) and fix it there, so the saved step and its exports hold exactly the typed text.

## Contract Inputs

- TASK-SKRIPT-39-06-08 and the ordering-step editor and save path in the exam workspace.

## Core Vertical And Performance

One step: add, type, save, export. No performance concern.

## Validation

- A focused test that fails before the fix: a step added and typed into at once is saved without a leading space.
- The existing ordering export tests pass.

## Stop Conditions

- The space comes from an intended separator that other question types depend on. Report it instead.

## Decided Contract Terms

| ID  | Decided contract term                                                                                        |
| --- | ------------------------------------------------------------------------------------------------------------ |
| D1  | Fix the leading space where it enters; the saved step and its exports hold exactly the typed text.           |
| D2  | Light route: one junior, a fail-first focused test, no review and no walk. Orchestrator decision 2026-10-28. |
