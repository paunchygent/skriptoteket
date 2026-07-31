---
type: task
id: TASK-SKRIPT-37-05-03
title: ST-37-05 shared filename editing UI primitives
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
- Given a teacher can name an export, when the filename editor renders, then the editable
  stem and protected extension are visually distinct and validated before action.
- Given apps have different output purposes, when they adopt the primitive, then labels
  and helper copy are app-owned while validation and extension behavior stay shared.
- Given narrow screens and dense app workspaces, when the primitive is used, then
  it does not create layout-heavy save dialogs or duplicate per-app controls.
---

## Context

### Source: Source introduction

### TASK-SKRIPT-37-05-03: ST-SKRIPT-37-05 Shared Filename Editing UI Primitives

### Source: Problem

Filename editing is easy to make layout-heavy or inconsistent if every app adds
its own save/download field.

## Decision And Assumption Ledger

The source snapshot is the governing record for the decisions and assumptions stated above.

## Story Contract Slice

### Source: Goal

Create shared frontend primitives or composables for editing a filename stem,
displaying the protected extension, surfacing validation, and returning a safe
filename intent to app actions.

## Contract Inputs

No separate contract inputs were recorded in the source snapshot.

## Plan

### Source: Implementation Plan

1. Add a compact filename editor primitive aligned with existing dense app UI.
2. Keep validation behavior compatible with the backend contract.
3. Add Vitest coverage for extension preservation, invalid names, and output
   preview text.
4. Document adoption expectations for app PRs.

## Implementation Steps

The source records no separate implementation steps.

## Proof

### Source: Test Plan

- Focused Vitest for the primitive/composable.
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run docs-validate`
- `git diff --check`

## Validation

Validation follows the focused test and verification material recorded above.

## Stop Conditions

### Source: Non-goals

- No app-specific adoption except a minimal playground/test fixture if needed.
- No broad design-system token change.
- No `Mina filer` rename implementation.

### Source: Rollback Plan

Remove the shared primitive and keep app-specific controls unchanged.

## Lessons Learned

No separate lessons learned were recorded in the source snapshot.

## Notes

No additional task-local notes were recorded in the source snapshot.

## Plan Document Review

No separate plan document review was recorded in the source snapshot.

## Implementation Review

No separate implementation review was recorded in the source snapshot.
