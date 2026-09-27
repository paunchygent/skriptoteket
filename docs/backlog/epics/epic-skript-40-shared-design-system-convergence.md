---
type: epic
id: EPIC-SKRIPT-40
title: Shared design-system convergence
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-09-27'
status: proposed
closeout_review:
  record: inline
  status: not_started
outcome: Skriptoteket consumes the shared huleedu-integrated design system through
  design-system sync for tokens, components, action buttons and glyphs, and its local
  extensions live in the shared package.
links:
  decisions: []
backlog_document_profile: contract-derived
---

## Capability Contract

Skriptoteket consumes the shared `huleedu-integrated` design system through
`repository-governance-frontend-catalog design-system sync` instead of hand
copies and local forks. Skriptoteket-local extensions that the shared package
lacks are promoted into the package, so HuleEdu and Skriptoteket render the
same tokens, dense components, messages, toasts, action buttons and glyphs.

Boundaries: the shared package lives in skill-repository
`resources/frontend-design-system/huleedu-integrated`; package releases and
HuleEdu syncs are skill-repository tasks. Skriptoteket owns its adoption map,
local wrappers, call sites and the components the package does not export.
Brand and auth-lifecycle exports stay unadopted. Non-goals: HuleEdu UI changes
beyond syncing package versions, and new product features.

## Contract Inputs

- Retained plan `.orchestration/context/sessions/01a0e42e-f433-727d-a17f-f9eced6d04bc/evidence/planning/TASK-SKRIPT-REP-0033/plan.md` (decisions D1-D18).
- Discovery `.orchestration/context/sessions/01a0e42e-f433-727d-a17f-f9eced6d04bc/discovery/design-system-adoption.md`.
- HuleEdu adoption precedent TASK-HULE-REP-0085.

## Stories

| Story           | Slice                                                                         |
| --------------- | ----------------------------------------------------------------------------- |
| ST-SKRIPT-40-01 | Tokens, theme, logo, dense components, SystemMessage, ToastHost, action buttons |
| ST-SKRIPT-40-02 | Shared glyph vocabulary and icon migration off `lucide-vue-next`              |

## Verification

- Skriptoteket's `design-system-map.json` adopts every export except `brand`
  and `auth-lifecycle`, and a sync from skill-repository main changes no file.
- Skriptoteket has no `lucide-vue-next` dependency and no local copies of
  adopted package components.
- HuleEdu runs the latest package version with its validator passing.

## Decided Contract Terms

| ID  | Decided contract term                                                                                           |
| --- | --------------------------------------------------------------------------------------------------------------- |
| D1  | Skriptoteket-local design extensions are promoted into the shared package rather than kept as local forks.     |
| D2  | Brand and auth-lifecycle exports stay unadopted in Skriptoteket.                                              |
| D3  | The package palette is authority; Skriptoteket accepts the 0.1.7 to current token changes.                    |
| D4  | Adoption uses `design-system sync` and the shared `design-system validate`; no hand copying.                  |
| D5  | Two stories: tokens, components and action buttons first; glyph vocabulary and icon migration second.        |
