---
type: pr
id: PR-0393
title: "ST-37-05 Mina filer rename and extension contract"
status: blocked
owners: "agents"
created: 2026-06-26
updated: 2026-06-26
stories:
  - "ST-37-05"
tags:
  - frontend
  - backend
  - mina-filer
dependencies:
  - "PR-0390"
  - "PR-0391"
  - "PR-0392"
acceptance_criteria:
  - "Given a teacher has a saved file, when they rename it in `Mina filer`, then only the display filename changes and stored bytes/source references remain unchanged."
  - "Given a teacher edits the name, when they omit or duplicate the extension, then the system preserves exactly one safe extension for the stored content type."
  - "Given a saved file is not owned by the teacher, deleted, or missing, when rename is attempted, then the backend rejects it as not found/forbidden."
---

# PR-0393: ST-37-05 Mina Filer Rename And Extension Contract

## Problem

Saved file records need user-controlled names after save without letting display
name edits mutate file bytes or extension/content-type truth.

## Goal

Implement owner-scoped `Mina filer` rename behavior through the shared naming
contract.

## Non-goals

- No content editing.
- No file-type conversion during rename.
- No bulk rename or migration.

## Implementation Plan

1. Add backend command/API for owner-scoped vault file rename.
2. Reuse shared filename validation and extension policy.
3. Add UI affordance in `Mina filer` for active saved files.
4. Prove source reference, size, hash where available, and content bytes remain
   unchanged.

## Test Plan

- Focused backend/API tests for rename authorization and validation.
- Focused frontend tests for rename UI and extension handling.
- `pdm run lint`
- `pdm run typecheck`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run docs-validate`
- `git diff --check`

## Rollback Plan

Remove rename route/UI and leave existing `Mina filer` records immutable.
