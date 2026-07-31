---
type: task
id: TASK-SKRIPT-37-05-04
title: ST-37-05 Mina filer rename and extension contract
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: blocked
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
story: ST-SKRIPT-37-05
task_kind: story
acceptance_criteria:
- Given a teacher has a saved file, when they rename it in `Mina filer`, then only
  the display filename changes and stored bytes/source references remain unchanged.
- Given a teacher edits the name, when they omit or duplicate the extension, then
  the system preserves exactly one safe extension for the stored content type.
- Given the teacher renames a saved file to a filename already used by the same owner,
  when the collision is detected, then rename is rejected with a named validation
  error instead of silently overwriting or auto-disambiguating the record.
- Given a saved file is not owned by the teacher, deleted, or missing, when rename
  is attempted, then the backend rejects it as not found/forbidden.
---

## Context

Source: `docs/backlog/prs/pr-0393-st-37-05-mina-filer-rename-and-extension-contract.md`. ST-37-05 Mina filer rename and extension contract.

Saved file records need user-controlled names after save without letting display name edits mutate file bytes or extension/content-type truth. Implement owner-scoped `Mina filer` rename behavior through the shared naming contract. - No content editing. - No file-type conversion during rename. - No bulk rename or migration. 1. Add backend command/API for owner-scoped vault file rename. 2. Reuse shared filename validation and extension policy. 3. Enforce the canonical rename-collision rule in the backend/API contract. 4. Add UI affordance in `Mina filer` for active saved files. 5. Prove source reference, size, hash where available, and content bytes remain unchanged. - Focused backend/API test

## Decision And Assumption Ledger

| ID | Type | Status | Question/Assumption | Recommendation/Decision | Source |
| --- | --- | --- | --- | --- | --- |
| MIG-TASK-SKRIPT-37-05-04 | migration | closed | How is source meaning preserved? | Preserve the source task contract, current relationships, and status while changing identity only. | ST-SKILL-08-06; TASK-SKRIPT-REP-0003 |

## Story Contract Slice

The task preserves the source implementation slice under its current story parent.

## Contract Inputs

- Source task/PR and audit-approved migration authority.
- Current story or repository relationship in candidate frontmatter.

## Plan

Execute only the bounded plan represented by the source record; do not add scope during migration.

## Implementation Steps

1. Preserve the source implementation or proof sequence.
2. Verify current relationships and focused evidence at task closeout.

## Proof

The source proof obligations are retained as historical evidence below; no execution proof is asserted by this candidate.

## Validation

Run the task-selected focused gates and repository docs validation after parent integration.

## Stop Conditions

Stop for missing authority, unresolved identity/relationship, terminal ancestry, or scope expansion.

## Lessons Learned

The source material is retained verbatim below for migration fidelity.

## Notes

### Source evidence

### PR-0393: ST-37-05 Mina Filer Rename And Extension Contract

### Problem

Saved file records need user-controlled names after save without letting display
name edits mutate file bytes or extension/content-type truth.

### Goal

Implement owner-scoped `Mina filer` rename behavior through the shared naming
contract.

### Non-goals

- No content editing.
- No file-type conversion during rename.
- No bulk rename or migration.

### Implementation Plan

1. Add backend command/API for owner-scoped vault file rename.
2. Reuse shared filename validation and extension policy.
3. Enforce the canonical rename-collision rule in the backend/API contract.
4. Add UI affordance in `Mina filer` for active saved files.
5. Prove source reference, size, hash where available, and content bytes remain
   unchanged.

### Test Plan

- Focused backend/API tests for rename authorization, validation, and
  same-owner collision rejection.
- Focused frontend tests for rename UI and extension handling.
- `pdm run lint`
- `pdm run typecheck`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run docs-validate`
- `git diff --check`

### Rollback Plan

Remove rename route/UI and leave existing `Mina filer` records immutable.

## Plan Document Review

No specialist approval is asserted; parent review remains required.

## Implementation Review

No closeout evidence is asserted in this candidate.
