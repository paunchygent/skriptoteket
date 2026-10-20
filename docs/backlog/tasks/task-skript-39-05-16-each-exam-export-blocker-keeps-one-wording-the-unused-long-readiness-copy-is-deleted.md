---
type: task
id: TASK-SKRIPT-39-05-16
title: 'Each exam export blocker keeps one wording: the unused long readiness copy is deleted'
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-10-20'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
  - No long-form readiness or export-blocker sentence, map or helper without a production caller remains, a search proves no reference is left, every shown string is unchanged, and fe-type-check, fe-lint and the focused specs pass
story: ST-SKRIPT-39-05
backlog_document_profile: contract-derived
---

## Implementation Contract

### Resume here

- 2026-10-20: contract closed (user request via the Hemma orchestrator
  944b5a5a). One junior unit (U1, scope `u1-delete-readiness-copy`) deletes the
  code; the lead runs the reference search and the focused proof. Evidence root:
  Skriptoteket session `01a156ae-7f31-7338-be23-b8b32352aa02`, work order
  `evidence/work-orders/39-05-16-u1-delete-readiness-copy.md`.

### Problem

The exam workspace keeps two wordings per export blocker: a short label that
the export panel and the question list show ("inte granskad", "facit saknas")
and a long sentence in `EXAM_WORKSPACE_EXPORT_BLOCKER_COPY`
(`useExamWorkspaceExports.ts`) and `READINESS_COPY`
(`examWorkspaceItemReadiness.ts`). The long sentences reach the teacher only
through `examWorkspaceReadinessCopy` and `examWorkspaceReadinessByItemId`,
which no production code calls. Found during TASK-SKRIPT-39-05-15.

### Change

- Delete `READINESS_COPY`, `examWorkspaceReadinessCopy`,
  `examWorkspaceReadinessByItemId` and the long map
  `EXAM_WORKSPACE_EXPORT_BLOCKER_COPY`, plus `GAP_WITHOUT_CORRECT_OPTION_GUIDANCE`,
  whose only consumer is the map.
- The two live uses of the long map keep working with one wording each: the
  server-blocker reason check in `useExamWorkspaceExports.ts` uses an
  exhaustive typed record of the reasons, and the shown title problem
  "Ge provet en titel med bokstäver eller siffror" becomes one constant used
  by `examWorkspaceBlockers.ts`.
- Specs that assert readiness through the deleted copy functions assert the
  readiness reasons instead; specs that only check deleted sentences go.

## Contract Inputs

- User request 2026-10-20 relayed by the Hemma orchestrator: delete the unused
  long-form export-blocker copy, keep every shown string.
- TASK-SKRIPT-39-05-15 finding (examWorkspaceReadinessByItemId has no
  production caller).

## Core Vertical And Performance

Frontend only: the exam workspace readiness rules, export blockers and export
refusal parsing. No backend or API change. No performance concern.

## Validation

- A repository search for every deleted symbol and every deleted sentence
  returns nothing outside history docs.
- `pdm run fe-type-check`, `pdm run fe-lint`, and the focused specs of every
  touched file pass.

## Stop Conditions

- The deletion touches `useExamWorkspaceHistory*`, `useExamWorkspaceDocument*`,
  the edit lease or the sync gate.
- A deleted sentence turns out to be shown somewhere.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                       |
| --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | Each export blocker keeps one wording: the short label the panel and list show; the long sentences and their maps and helpers are deleted.                  |
| D2  | Server-blocker reason validation keeps an exhaustive typed record of `ExamWorkspaceExportBlockerReason`, so a new server reason still fails the type check. |
| D3  | The shown title problem keeps its exact text as one constant; no shown string changes.                                                                      |
| D4  | Coverage of readiness reasons moves from copy assertions to reason assertions; tests that only checked deleted sentences are removed.                       |
| D5  | Skriptoteket is unreleased: no compatibility path.                                                                                                          |
