---
type: pr
id: PR-0366
title: "ST-37-04 copy-only app lane naming and description alignment"
status: blocked
owners: "agents"
created: 2026-06-18
updated: 2026-06-18
stories:
  - "ST-37-04"
tags:
  - frontend
  - docs
  - copy
dependencies:
  - "PR-0362"
  - "PR-0363"
  - "PR-0364"
  - "PR-0365"
  - "REF-app-presentation-decomposition-and-naming-plan-v1"
acceptance_criteria:
  - "Given the route-visible shell surfaces are app-first, when teacher-facing copy is aligned, then Klassrumskartan, Audio Transcription, and Exam Converter use the approved lane names and truthful descriptions instead of broad Conversion Hub language."
  - "Given Document Converter has no truthful runnable route yet, when copy is aligned, then it is only described as planned or upcoming and does not send teachers into the current compatibility host."
  - "Given this slice is copy-only, when it closes, then routes, app ids, curated-app registry metadata, Sir Convert, HuleEdu, QTI, DOCX, and backend API contracts remain unchanged."
---

# PR-0366: ST-37-04 Copy-Only App Lane Naming And Description Alignment

## Problem

Even after the authenticated shell becomes app-first, route-visible text can
still carry stale generic Conversion Hub language unless the lane naming is
aligned deliberately.

## Goal

Align teacher-facing names and descriptions across shell surfaces without
changing routes or registry metadata.

## Non-goals

- No route alias or app-id change.
- No curated-app registry title/summary change.
- No Sir Convert, HuleEdu, QTI, DOCX, or backend API contract change.

## Review gate

`REV-PR-0366` must be approved before code implementation begins.

## Implementation plan

1. Add focused red tests for the shell surfaces that still present generic
   Conversion Hub copy after `PR-0364` and `PR-0365`.
2. Align authenticated home cards, authenticated navigation labels, lane
   headings, tabs, and nearby helper copy to
   [REF-app-presentation-decomposition-and-naming-plan-v1](../../reference/ref-app-presentation-decomposition-and-naming-plan-v1.md).
3. Keep Document Converter planned-only wording until a truthful route exists.
4. Leave registry/bootstrap metadata untouched for `PR-0367`.

## Test plan

- Red first:
  `pdm run fe-test -- --run src/views/HomeView.spec.ts src/components/layout/AuthLayout.spec.ts src/App.spec.ts`
- Green:
  `pdm run fe-test -- --run src/views/HomeView.spec.ts src/components/layout/AuthLayout.spec.ts src/App.spec.ts`
- Add focused component or helper tests if copy is extracted into a shared
  model.
- `pdm run fe-type-check`
- Authenticated browser proof through the HuleEdu browser-session ceremony for
  the changed signed-in shell surfaces.
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Rollback plan

Restore the previous teacher-facing copy while leaving route and registry
surfaces unchanged.
