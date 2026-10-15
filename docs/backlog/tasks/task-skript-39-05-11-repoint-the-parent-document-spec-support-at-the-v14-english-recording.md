---
type: task
id: TASK-SKRIPT-39-05-11
title: Repoint the parent-document spec support at the v14 English recording
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
- The frontend typecheck passes on main with no import of the removed docx_build_v7
  recording
- The three specs that import examWorkspaceParentDocument.specSupport.ts pass against
  a fixture built from the docx_key_provenance_v14 BF26 English recordings
story: ST-SKRIPT-39-05
backlog_document_profile: contract-derived
---

## Implementation Contract

Commit `87478dcd` removed
`tests/fixtures/exam_conversion/docx_build_v7/`, but
`frontend/apps/skriptoteket/src/views/apps/exam-workspace/examWorkspaceParentDocument.specSupport.ts`
still imports `bf26_english_1_unit_test_kap_1_2_med_facit/round1.json` from it,
so `vue-tsc --noEmit` fails on main. The spec support builds a test-only native
document: three gap_fill children of `parent_001` that share one paragraph
instruction, followed by one standalone single_choice item.

The v14 recordings are per-batch provider replies. `docx_w1-01.json` holds the
shared instruction ("Complete each sentence ...", now `instructions[1]`) and
the same first three gap_fill items (ability, forced, grieve). `docx_w1-04.json`
holds the first single_choice item. The spec support imports both and keeps
its current item mapping; the document shape and item IDs are unchanged.

## Contract Inputs

- `tests/fixtures/exam_conversion/docx_key_provenance_v14/README.md` and
  `bf26_english_1_unit_test_kap_1_2_med_facit/docx_w1-01.json`, `docx_w1-04.json`.
- Consumers: `ExamWorkspaceItemTable.parents.spec.ts`,
  `examWorkspaceParents.spec.ts`, `useExamWorkspaceDocument.parents.spec.ts`.

## Core Vertical And Performance

Test fixture only; no production code, route or UI change, so no browser walk.

## Validation

- `pnpm --filter @skriptoteket/spa typecheck` passes.
- The three consumer specs pass through the SPA Vitest runner.

## Stop Conditions

- A consumer spec asserts v7-only content that the v14 recordings cannot carry.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| D1  | Children and the shared instruction come from `docx_w1-01.json` (`instructions[1]`, `items[0..2]`); the standalone item is the first single_choice of `docx_w1-04.json`. User choice 2026-10-15. |
| D2  | The builder keeps its current field mapping; v14-only fields (`spelling_candidates`, `facit_text`, `printed_label`, `key_source`) are not mapped. User choice 2026-10-15. |
| D3  | Delivery: one Sol 6.1 implementation-specialist (may fan out DeepSeek Flash 4.1 juniors), then an independent Sol 6.1 ruthless review before merge to main. User choice 2026-10-15. |
