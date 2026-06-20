---
type: pr
id: PR-0366
title: "ST-37-04 copy-only app lane naming and description alignment"
status: done
owners: "agents"
created: 2026-06-18
updated: 2026-06-20
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

The exact copy changes were approved in-session on 2026-06-20 before
implementation.

## Implementation plan

1. [x] Add focused red tests for the shell surfaces that still present generic
   Conversion Hub copy after `PR-0364` and `PR-0365`.
2. [x] Align authenticated home cards, authenticated navigation labels, lane
   headings, tabs, and nearby helper copy to
   [REF-app-presentation-decomposition-and-naming-plan-v1](../../reference/ref-app-presentation-decomposition-and-naming-plan-v1.md).
3. [x] Keep Document Converter planned-only wording until a truthful route
   exists.
4. [x] Leave registry/bootstrap metadata untouched for `PR-0367`.

## Implementation evidence

- `frontend/apps/skriptoteket/src/components/home/homeWorkApps.ts` now aligns
  authenticated home app-card descriptions for `Klassrumskartan`,
  `Provhantering`, `Ljudtranskribering`, and planned-only
  `Dokumentkonvertering`.
- `frontend/apps/skriptoteket/src/views/apps/ConversionHubModeTabs.vue` now
  labels the authenticated compatibility switch as `Prov och transkribering`
  with the visible options `Provhantering` and `Ljudtranskribering`.
- `frontend/apps/skriptoteket/src/views/apps/ExamConverterAuthenticatedView.vue`
  now exposes the authenticated host frame as
  `Provhantering och ljudtranskribering`.
- `frontend/apps/skriptoteket/src/views/apps/ExamConverterPublicView.vue`
  now uses the public lane eyebrow `Provhantering` instead of the compatibility
  shell name.
- Routes, app ids, curated-app registry metadata, Sir Convert, HuleEdu, QTI,
  DOCX, and backend API contracts were not changed.

## Verification

- Red first:
  `pdm run fe-test -- --run src/views/HomeView.spec.ts src/views/apps/ExamConverterAuthenticatedView.spec.ts src/views/apps/ExamConverterPublicView.spec.ts`
  failed against the old copy because the home cards still rendered the old
  descriptions, the authenticated tabs still exposed `Conversion Hub`, and the
  public page still used the compatibility-shell eyebrow.
- Green:
  `pdm run fe-test -- --run src/views/HomeView.spec.ts src/views/apps/ExamConverterAuthenticatedView.spec.ts src/views/apps/ExamConverterPublicView.spec.ts`
  passed with 28 tests.
- Live public landing proof with Node REPL Playwright and installed Chrome
  against `http://localhost:5173/` confirmed the rendered page contains
  `Lektionsplanera direkt i webbläsaren.`, `När du loggar in`,
  `Skapa PDF:er med hjälp av HTML och CSS`, and
  `Skapa, redigera och konvertera prov`.
- Local public Exam Converter navigation to
  `http://localhost:5173/public/apps/documents.conversion_hub/exam-converter`
  initially reached the SPA shell but returned `Internal Server Error` because
  the host Vite proof lane had no running Skriptoteket backend target for
  public `/api/v1/public/...` traffic. That local runtime issue was remediated
  in `PR-0373`; the `Provhantering` eyebrow remains covered by focused
  component Vitest for this copy-only slice.

## Test plan

- Red first:
  `pdm run fe-test -- --run src/views/HomeView.spec.ts src/views/apps/ExamConverterAuthenticatedView.spec.ts src/views/apps/ExamConverterPublicView.spec.ts`
- Green:
  `pdm run fe-test -- --run src/views/HomeView.spec.ts src/views/apps/ExamConverterAuthenticatedView.spec.ts src/views/apps/ExamConverterPublicView.spec.ts`
- `pdm run fe-type-check`
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Rollback plan

Restore the previous teacher-facing copy while leaving route and registry
surfaces unchanged.
