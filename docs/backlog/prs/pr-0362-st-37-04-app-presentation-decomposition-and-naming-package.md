---
type: pr
id: PR-0362
title: "ST-37-04 app presentation decomposition and naming package"
status: done
owners: "agents"
created: 2026-06-17
updated: 2026-06-18
stories:
  - "ST-37-04"
tags:
  - docs
  - frontend
  - curated-apps
  - conversion
dependencies:
  - "PR-0358"
  - "PR-0359"
  - "PR-0360"
  - "PR-0361"
  - "REF-current-product-lanes-and-sir-convert-boundary-v1"
  - "REF-service-shell-ux-realignment-plan-v1"
acceptance_criteria:
  - "Given current product lanes are documented, when this package closes, then the app registry/presentation implementation sequence separates Exam Converter, Audio Transcription, Document Converter, and Klassrumskartan presentation concerns."
  - "Given generic Conversion Hub naming hides teacher jobs, when future implementation tasks are created, then each app lane has proposed name, description, route/entrypoint impact, docs impact, and proof gates."
  - "Given Exam Converter future work includes editing/sharing/QTI, when tasks are created, then they preserve Skriptoteket ownership of native exam state after heavy import."
---

# PR-0362: ST-37-04 App Presentation Decomposition And Naming Package

## Problem

Current app presentation still groups distinct teacher jobs under broad generic
conversion language.

## Goal

Create the implementation-ready naming, description, and entrypoint sequence for
the app-presentation reset.

## Non-goals

- No immediate route or registry implementation.
- No new conversion backend or Sir Convert contract.
- No DOCX/QTI/editor implementation in this planning package.

## Implementation plan

1. Read the service-shell planning output:
   [REF-service-shell-ux-realignment-plan-v1](../../reference/ref-service-shell-ux-realignment-plan-v1.md).
2. Inventory current curated app registry, route, card, and copy surfaces.
3. Propose app-lane names and descriptions for Klassrumskartan, Audio
   Transcription, Exam Converter, and Document Converter using
   [REF-current-product-lanes-and-sir-convert-boundary-v1](../../reference/ref-current-product-lanes-and-sir-convert-boundary-v1.md)
   as the lane boundary reference.
4. Identify which changes are copy-only, registry-only, route-visible, or
   backend/API-visible.
5. Create PR-sized implementation tasks with frontend tests, generated-type
   needs, docs updates, and browser proof obligations.

## Implementation Summary

Completed on 2026-06-18. The durable planning output is
[REF-app-presentation-decomposition-and-naming-plan-v1](../../reference/ref-app-presentation-decomposition-and-naming-plan-v1.md).
It records the current technical compatibility shell, closes the naming and
entrypoint sequencing for `Klassrumskartan`, `Audio Transcription`,
`Exam Converter`, and future `Document Converter`, includes explicit docs
impact for each lane, and separates copy-only, registry-only, route-visible,
and backend/API-visible follow-up work.

This slice also created the next ST-37-04 backlog sequence:

- [PR-0366](pr-0366-st-37-04-copy-only-app-lane-naming-and-description-alignment.md):
  copy-only lane naming and description alignment.
- [PR-0367](pr-0367-st-37-04-curated-app-registry-presentation-alignment.md):
  curated-app registry metadata alignment.
- [PR-0368](pr-0368-st-37-04-route-visible-app-entrypoint-and-presentation-alignment.md):
  later route-visible app-entrypoint reassessment after the shell foundation
  ships.
- [PR-0369](pr-0369-st-37-04-backend-and-api-app-presentation-contract-alignment.md):
  reserved backend/API-visible follow-up only if later route-visible work proves
  it is truly needed.

No immediate route, registry, app-id, Sir Convert, HuleEdu, QTI, DOCX, or
backend/API contract change was made by this docs-only package. `ST-37-04`
remains open for implementation, while `PR-0363` through `PR-0365` are now
unblocked by planning and remain gated by their own review docs before code
begins.

## Test plan

- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Verification

- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Rollback plan

Revert the package if review decides the naming/decomposition should be handled
inside a different product epic.
