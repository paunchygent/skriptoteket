---
type: pr
id: PR-0365
title: "ST-37-03 authenticated shell navigation realignment"
status: blocked
owners: "agents"
created: 2026-06-18
updated: 2026-06-18
stories:
  - "ST-37-03"
tags:
  - frontend
  - ux
  - navigation
dependencies:
  - "PR-0361"
  - "PR-0362"
  - "PR-0363"
  - "PR-0364"
  - "REF-service-shell-ux-realignment-plan-v1"
  - "REF-current-product-lanes-and-sir-convert-boundary-v1"
  - "REF-app-presentation-decomposition-and-naming-plan-v1"
acceptance_criteria:
  - "Given the authenticated home has an app-first hierarchy, when the authenticated sidebar or mobile drawer renders, then current app-lane links are primary and generic catalog/tool/admin links are grouped as secondary platform or role-gated surfaces."
  - "Given route-visible shell navigation changes, when the slice closes, then focused layout/router tests and live browser proof cover desktop sidebar, mobile drawer, focus mode, and protected app navigation through the HuleEdu browser-session ceremony."
  - "Given immersive and workspace-heavy routes have special chrome behavior, when navigation is realigned, then Flunk-Out Frenzy immersive mode and Klassrumskartan's wider sidebar breakpoint remain unchanged."
---

# PR-0365: ST-37-03 Authenticated Shell Navigation Realignment

## Problem

The authenticated sidebar still reflects a generic catalog/tool hierarchy. Once
the home surface establishes the app-first model, persistent navigation should
match that hierarchy without breaking special route chrome.

## Goal

Rebalance authenticated navigation toward app lanes while keeping platform,
contributor, and admin surfaces accessible and role-gated.

## Non-goals

- No public landing/header rewrite.
- No app-id or route rename.
- No changes to immersive game route behavior or Klassrumskartan workspace
  route-shell internals beyond navigation entrypoints.

## Review gate

`REV-PR-0365` must be approved before code implementation begins.

## Implementation plan

1. Add a focused red layout/navigation test proving current navigation lacks a
   primary app-lane section.
2. Update `AuthSidebar.vue` and any shared shell navigation helpers to present
   app-lane links first.
3. Keep platform links such as `Katalog`, `Mina körningar`, `Mina filer`,
   `Kodredigerare`, suggestions, and admin pages available below the app lanes.
4. Preserve focus mode, mobile drawer behavior, immersive route behavior, and
   Klassrumskartan's `xl` sidebar breakpoint.

## Test plan

- Red first:
  `pdm run fe-test -- --run src/components/layout/AuthLayout.spec.ts src/App.spec.ts`
- Green:
  `pdm run fe-test -- --run src/components/layout/AuthLayout.spec.ts src/App.spec.ts`
- Add/extend `AuthSidebar` focused tests if the navigation model is extracted.
- `pdm run fe-type-check`
- Browser proof for desktop sidebar and mobile drawer through the HuleEdu
  browser-session ceremony.
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Rollback plan

Restore the prior authenticated sidebar ordering and remove any extracted
navigation model.
