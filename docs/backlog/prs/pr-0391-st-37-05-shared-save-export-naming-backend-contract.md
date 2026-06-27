---
type: pr
id: PR-0391
title: "ST-37-05 shared save/export naming backend contract"
status: blocked
owners: "agents"
created: 2026-06-26
updated: 2026-06-26
stories:
  - "ST-37-05"
tags:
  - backend
  - files
  - exports
dependencies:
  - "PR-0390"
acceptance_criteria:
  - "Given an app requests a generated output name, when it supplies source title, output purpose, extension, and authority shape, then a shared backend/domain service returns a safe default filename without duplicated extensions."
  - "Given a teacher edits a filename stem, when the backend validates it, then unsafe characters, path traversal, empty names, and unsupported extension changes are rejected consistently."
  - "Given a saved output has source provenance, when `Mina filer` stores the record, then display name and stable source reference remain separate fields or explicitly separate concepts."
---

# PR-0391: ST-37-05 Shared Save/Export Naming Backend Contract

## Problem

Each app can otherwise invent its own filename builder, extension handling, and
source-reference behavior.

## Goal

Add a shared backend/domain contract for generated file names and edited
filename validation that app-specific handlers can reuse.

## Non-goals

- No route-specific UI implementation.
- No migration of existing file records.
- No app-specific producer replay changes beyond adapter hooks needed for tests.

## Implementation Plan

1. Design a small value object or service for generated output names.
2. Preserve source reference and display filename as separate concepts.
3. Add focused unit tests for extension preservation, duplicate-extension
   prevention, source-derived stems, and unsafe-name rejection.
4. Wire only the minimal surfaces needed for later app adoption.

## Test Plan

- Focused backend unit tests for naming and validation.
- `pdm run lint`
- `pdm run typecheck`
- `pdm run docs-validate`
- `git diff --check`

## Rollback Plan

Remove the shared naming contract and keep existing app-specific names until a
smaller backend shape is designed.
