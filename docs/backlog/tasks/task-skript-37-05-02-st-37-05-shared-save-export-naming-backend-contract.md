---
type: task
id: TASK-SKRIPT-37-05-02
title: ST-37-05 shared save/export naming backend contract
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
- Given an app requests a generated output name, when it supplies source title, canonical
  output purpose, extension, and authority shape, then a shared backend/domain service
  returns a safe default filename without duplicated extensions.
- Given the same owner saves the same generated output again, when the default visible
  name would collide, then the backend creates a new saved file record with a system-disambiguated
  final filename unless a reviewed app adapter declares and tests an update-in-place
  exception.
- Given a teacher edits a filename stem, when the backend validates it, then unsafe
  characters, path traversal, empty names, unsupported extension changes, reserved
  names, and shared max-length violations are rejected consistently after Unicode
  normalization.
- Given a saved output has source provenance, when `Mina filer` stores the record,
  then display name and stable source reference remain separate fields or explicitly
  separate concepts.
- Given a protected save or download action completes, when the final filename is
  emitted, then the backend/API returns or sets the sanitized final filename, extension,
  and content type as the authoritative result instead of relying on browser-side
  reconstruction.
---

## Context

### PR-0391: ST-37-05 Shared Save/Export Naming Backend Contract

### Problem

Each app can otherwise invent its own filename builder, extension handling, and
source-reference behavior.

### Goal

Add a shared backend/domain contract for generated file names and edited
filename validation that app-specific handlers can reuse.

### Non-goals

- No route-specific UI implementation.
- No migration of existing file records.
- No app-specific producer replay changes beyond adapter hooks needed for tests.

### Implementation Plan

1. Design a small value object or service for generated output names and
   backend-owned final filename disambiguation.
2. Preserve source reference and display filename as separate concepts.
3. Return authoritative final filename metadata for protected save/download
   actions, for example response metadata or `Content-Disposition`.
4. Add focused unit/API tests for extension preservation, duplicate-save
   disambiguation, duplicate-extension prevention, source-derived stems,
   Unicode normalization, reserved-name rejection, and server-owned download
   filename authority.
5. Wire only the minimal surfaces needed for later app adoption.

### Test Plan

- Focused backend/domain tests for naming, duplicate-save disambiguation, and
  validation.
- Focused API tests for authoritative final filename metadata or headers on
  save and download surfaces.
- `pdm run lint`
- `pdm run typecheck`
- `pdm run docs-validate`
- `git diff --check`

### Rollback Plan

Remove the shared naming contract and keep existing app-specific names until a
smaller backend shape is designed.

## Decision And Assumption Ledger

The source material below remains authoritative for this section.

## Story Contract Slice

The source material below remains authoritative for this section.

## Contract Inputs

The source material below remains authoritative for this section.

## Plan

The source material below remains authoritative for this section.

## Implementation Steps

The source material below remains authoritative for this section.

## Proof

Verification expectations remain in the retained source material below.

## Validation

Verification expectations remain in the retained source material below.

## Stop Conditions

The source boundaries and recovery limits remain preserved below.

## Lessons Learned

The source material below remains authoritative for this section.

## Notes

The source material below remains authoritative for this section.

## Plan Document Review

The source material below remains authoritative for this section.

## Implementation Review

The source material below remains authoritative for this section.
