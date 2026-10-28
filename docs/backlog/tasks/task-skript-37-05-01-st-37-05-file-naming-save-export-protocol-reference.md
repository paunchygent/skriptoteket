---
type: task
id: TASK-SKRIPT-37-05-01
title: ST-37-05 file naming/save/export protocol reference
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-07-31'
status: done
closeout_review:
  record: inline
  status: approved
  reviewer: orchestrator
  decided_at: '2026-10-28'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: 'TASK-SKRIPT-37-05-01#closeout'
story: ST-SKRIPT-37-05
task_kind: story
acceptance_criteria:
  - Given current file action drift, when this planning slice closes, then a reviewed reference defines generated filename shape, canonical Swedish purpose vocabulary, extension ownership, duplicate-save behavior, editable stems, and `Mina filer` rename semantics.
  - Given app-owned and producer-replay outputs differ, when the reference is reviewed, then it describes both authority shapes without forcing one artifact model.
  - Given app implementation slices follow, when this PR closes, then each later PR has a clear app-adapter question set and proof obligations for duplicate-save disambiguation or reviewed exceptions, rename-collision behavior, and protected API final filename authority.
dependencies:
  - ST-SKRIPT-37-05
backlog_document_profile: contract-derived
---

## Implementation Contract

Closed as done on 2026-10-28 under TASK-SKRIPT-REP-0055 D1 on merge evidence. The original contract below is kept as history; see Closeout for what shipped and what was not checked.

## Context

### Source: Problem

Curated app downloads and `Mina filer` saves are beginning to repeat the same
problems in separate places: redundant filenames, weak source provenance,
extension drift risk, and app-specific save/export UX for similar work.

## Decision And Assumption Ledger

The source does not record a separate decision and assumption ledger.

## Story Contract Slice

### Source: Goal

Review and finalize
[REF-SKRIPT-GENERAL-file-naming-save-and-export-protocol-v1](../../reference/ref-skript-general-file-naming-save-and-export-protocol-v1-file-naming-save-and-export-protocol-v1.md)
as the cross-app planning contract for generated file names, editable save
names, extension handling, duplicate saves, and `Mina filer` rename behavior.

## Contract Inputs

The source does not record separate contract inputs.

## Core Vertical And Performance

The source record did not define a separate section for this package heading.

## Plan

### Source: Implementation Plan

1. Review current save/export surfaces for Audio Transcription, Exam Converter,
   Document Converter, and `Mina filer`.
2. Update the reference with the smallest shared naming contract that fits all
   current authority shapes.
3. Confirm app-owned versus producer-replay distinctions.
4. Close or revise the follow-up PR slices before implementation begins.

## Implementation Steps

The source does not provide separate implementation steps.

## Proof

### Source: Test Plan

- `pdm run docs-validate`
- `git diff --check`

## Validation

### Source: Test Plan

- `pdm run docs-validate`
- `git diff --check`

## Stop Conditions

### Source: Non-goals

- No production backend or frontend implementation.
- No migration of existing saved files.
- No app-specific adoption beyond planning the sequence.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                                                                 |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | Closed as done on 2026-10-28 on merge evidence confirmed in code and git history (TASK-SKRIPT-REP-0055 D1); the Closeout section lists the evidence and the checks that were not run. |

## Lessons Learned

The source does not record separate lessons learned.

## Notes

### Source: Rollback Plan

Revert this planning package and leave app-specific save/export naming unchanged
until a better shared protocol is reviewed.

## Plan Document Review

The source does not include a plan document review record.

## Implementation Review

The source does not include an implementation review record.

## Closeout

Closed as done on 2026-10-28 under TASK-SKRIPT-REP-0055 D1 (orchestrator closeout on merge evidence).

The shared file naming, save and export protocol reference was added in bc31fbccb, extended in cb198ddc1 and migrated to docs/reference/ref-skript-general-file-naming-save-and-export-protocol-v1-... in 7d2056de1, with status active. It defines filename shape, Swedish purpose labels, extension ownership, editable stems, duplicate saves, Mina filer rename and the two authority shapes, and ends with the app-adapter question set. Review REV-ST-37-05 is approved; the proof obligations sit in tasks 37-05-02 to 37-05-06. docs-validate output was not recorded. Tasks 37-05-02 to 37-05-06 stay blocked with no blocker named in their records. TASK-SKRIPT-REP-0056 D9 later set 37-05-02 and 37-05-03 to `ready` and named 37-05-02 as the blocker of 37-05-04 to 37-05-06.
