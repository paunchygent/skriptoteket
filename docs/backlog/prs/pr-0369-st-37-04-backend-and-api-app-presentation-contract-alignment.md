---
type: pr
id: PR-0369
title: "ST-37-04 backend and API app presentation contract alignment"
status: blocked
owners: "agents"
created: 2026-06-18
updated: 2026-06-23
stories:
  - "ST-37-04"
tags:
  - backend
  - api
  - curated-apps
dependencies:
  - "PR-0362"
  - "PR-0368"
  - "PR-0375"
  - "REF-app-presentation-decomposition-and-naming-plan-v1"
acceptance_criteria:
  - "Given a reviewed route-visible slice has proven the compatibility shell can no longer express the teacher-facing app model truthfully, when this slice runs, then backend/bootstrap or API contracts explicitly represent the required app-presentation split without breaking current authorized consumers."
  - "Given frontend consumers rely on generated contracts, when an API-visible change is introduced, then generated types, focused backend tests, focused frontend tests, and route-visible browser proof all move together."
  - "Given Sir Convert and HuleEdu boundaries are already defined elsewhere, when this slice closes, then it still does not change producer, Gateway, QTI, DOCX, or native exam/transcript ownership doctrine."
---

# PR-0369: ST-37-04 Backend And API App Presentation Contract Alignment

## Problem

The current planning package does not assume a backend or API app-presentation
split is needed. `PR-0375` also keeps the first Document Converter backend/API
follow-up under the existing `documents.conversion_hub` technical app id. If
later route-visible or Document Converter work proves that assumption false,
the contract change must happen in this explicit slice rather than being
smuggled into frontend work.

## Goal

Reserve a separate reviewed slice for any real backend or API work required by
app-presentation decomposition.

## Non-goals

- No contract change unless `PR-0368`, `PR-0375`, or later reviewed
  route-visible/backend work documents a concrete incompatibility.
- No Sir Convert, HuleEdu, QTI, or DOCX contract change.
- No fake Document Converter route or host.

## Review gate

`REV-PR-0369` must be approved before code implementation begins.

## Implementation plan

1. Start only if a reviewed route-visible or Document Converter follow-up closes
   with written evidence that truthful app presentation cannot be maintained on
   the current compatibility bootstrap/API shape.
2. Define the smallest possible backend/bootstrap or API contract adjustment:
   metadata split, capability split, or app-detail decomposition.
3. Update generated frontend consumers and keep app-state ownership doctrine
   aligned with
   [REF-current-product-lanes-and-sir-convert-boundary-v1](../../reference/ref-current-product-lanes-and-sir-convert-boundary-v1.md).
4. Stop and re-plan if the proposal drifts into Sir Convert producer/Gateway
   work or into implementation of a still-hypothetical Document Converter app.

## Test plan

- Red first:
  targeted backend or API contract tests named by the chosen implementation
  path.
- Green:
  rerun the same targeted backend tests plus any changed frontend consumer
  tests.
- `pdm run lint`
- `pdm run typecheck`
- `pdm run fe-type-check`
- Regenerate frontend API types if the contract surface changes.
- Route-visible browser proof through the HuleEdu browser-session ceremony if a
  UI consumer changes.
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Rollback plan

Restore the prior contract surface and keep the route-visible work on the
compatibility path while re-planning the decomposition.
