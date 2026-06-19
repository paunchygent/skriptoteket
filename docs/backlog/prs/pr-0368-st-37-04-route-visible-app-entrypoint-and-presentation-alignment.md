---
type: pr
id: PR-0368
title: "ST-37-04 route-visible app entrypoint and presentation alignment"
status: blocked
owners: "agents"
created: 2026-06-18
updated: 2026-06-18
stories:
  - "ST-37-04"
tags:
  - frontend
  - routing
  - curated-apps
dependencies:
  - "PR-0362"
  - "PR-0363"
  - "PR-0364"
  - "PR-0365"
  - "PR-0366"
  - "PR-0367"
  - "REF-app-presentation-decomposition-and-naming-plan-v1"
acceptance_criteria:
  - "Given the compatibility deep-link bridge and app-first shell are in place, when route-visible app presentation is revisited, then the repo either records that the compatibility route remains sufficient or adds truthful dedicated teacher-facing route aliases for the current lanes."
  - "Given Document Converter still lacks a real host, when this slice runs, then no Document Converter route or alias is created unless the same slice delivers a truthful dedicated host and browser proof."
  - "Given route-visible app entrypoints are changed, when the slice closes, then focused router or host-view tests plus live browser proof cover every changed protected or public route surface."
---

# PR-0368: ST-37-04 Route-Visible App Entrypoint And Presentation Alignment

## Problem

After the compatibility deep-link bridge and shell realignment ship, the repo
still needs a deliberate answer about whether teacher-facing routes should stay
wrapped around `documents.conversion_hub` or gain dedicated aliases.

## Goal

Resolve remaining route-visible app-presentation debt without inventing a false
Document Converter lane.

## Non-goals

- No backend/API decomposition unless the route-visible work proves it is
  necessary.
- No Sir Convert, HuleEdu, QTI, or DOCX contract change.
- No fake Document Converter implementation.

## Review gate

`REV-PR-0368` must be approved before code implementation begins.

## Implementation plan

1. Reassess the post-`PR-0363` through `PR-0367` state and choose between:
   - keeping the compatibility route because it is still truthful enough; or
   - adding explicit teacher-facing route aliases or host-surface route
     presentation for Exam Converter and Audio Transcription.
2. Add focused red router or host-view tests for the chosen route-visible
   change.
3. Preserve the current public Exam Converter route unless the reviewed slice
   explicitly changes it with matching proof.
4. Stop and return to planning if route-visible truth cannot be achieved
   without new backend/API contract work; that handoff belongs to `PR-0369`.

## Test plan

- Red first:
  `pdm run fe-test -- --run src/router/routes.spec.ts src/App.spec.ts`
- Green:
  `pdm run fe-test -- --run src/router/routes.spec.ts src/App.spec.ts`
- Add focused host-view or home/navigation tests for any changed entry surfaces.
- `pdm run fe-type-check`
- Live browser proof through the HuleEdu browser-session ceremony for each
  changed authenticated route and any changed public route.
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Rollback plan

Remove the new route-visible presentation changes and keep the compatibility
route plus shell copy sequence.
