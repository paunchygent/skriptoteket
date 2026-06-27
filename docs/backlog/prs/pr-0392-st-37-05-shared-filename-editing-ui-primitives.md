---
type: pr
id: PR-0392
title: "ST-37-05 shared filename editing UI primitives"
status: blocked
owners: "agents"
created: 2026-06-26
updated: 2026-06-26
stories:
  - "ST-37-05"
tags:
  - frontend
  - files
  - exports
dependencies:
  - "PR-0390"
  - "PR-0391"
acceptance_criteria:
  - "Given a teacher can name an export, when the filename editor renders, then the editable stem and protected extension are visually distinct and validated before action."
  - "Given apps have different output purposes, when they adopt the primitive, then labels and helper copy are app-owned while validation and extension behavior stay shared."
  - "Given narrow screens and dense app workspaces, when the primitive is used, then it does not create layout-heavy save dialogs or duplicate per-app controls."
---

# PR-0392: ST-37-05 Shared Filename Editing UI Primitives

## Problem

Filename editing is easy to make layout-heavy or inconsistent if every app adds
its own save/download field.

## Goal

Create shared frontend primitives or composables for editing a filename stem,
displaying the protected extension, surfacing validation, and returning a safe
filename intent to app actions.

## Non-goals

- No app-specific adoption except a minimal playground/test fixture if needed.
- No broad design-system token change.
- No `Mina filer` rename implementation.

## Implementation Plan

1. Add a compact filename editor primitive aligned with existing dense app UI.
2. Keep validation behavior compatible with the backend contract.
3. Add Vitest coverage for extension preservation, invalid names, and output
   preview text.
4. Document adoption expectations for app PRs.

## Test Plan

- Focused Vitest for the primitive/composable.
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run docs-validate`
- `git diff --check`

## Rollback Plan

Remove the shared primitive and keep app-specific controls unchanged.
