---
type: pr
id: PR-0396
title: "ST-37-05 Document Converter save/export naming adoption"
status: blocked
owners: "agents"
created: 2026-06-26
updated: 2026-06-26
stories:
  - "ST-37-05"
tags:
  - frontend
  - backend
  - document-converter
  - exports
dependencies:
  - "PR-0385"
  - "PR-0390"
  - "PR-0391"
  - "PR-0392"
acceptance_criteria:
  - "Given Document Converter creates a single-file or project-preview output, when the teacher downloads or saves it, then the default filename derives from source file or project title, output purpose, and correct extension."
  - "Given the teacher uses `Mina filer` as a source, when a new output is saved, then source reference and display filename remain distinct and the name does not imply project workspace restoration."
  - "Given separate project preview outputs exist, when saved or downloaded, then each has a predictable distinguished name without raw artifact ids in visible UI."
---

# PR-0396: ST-37-05 Document Converter Save/Export Naming Adoption

## Problem

`PR-0385` gives Document Converter useful saved-file sources and current-session
history. Filename editing and cross-app naming protocol adoption should remain
a separate follow-up so the save/reopen boundary is not overbuilt.

## Goal

Adopt the shared naming contract for Document Converter download and
`Mina filer` save actions.

## Non-goals

- No saved project/package model.
- No multi-file HTML/CSS source selection from `Mina filer`.
- No change to PR-0385 current-session history semantics.

## Implementation Plan

1. Map local upload, saved-file source, and project-preview source labels into
   source-derived default names.
2. Add editable stems before download/save using the shared UI primitive.
3. Preserve the PR-0385 rule that reopen means using a saved output as a new
   source where supported, not restoring a project workspace.
4. Add tests for single-file, saved-source, and separate/combined project
   preview output names.

## Test Plan

- Focused Document Converter backend/frontend tests.
- `pdm run lint`
- `pdm run typecheck`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run docs-validate`
- `git diff --check`

## Rollback Plan

Revert Document Converter naming adoption and keep the PR-0385 save/export
behavior unchanged.
