---
type: pr
id: PR-0365
title: "ST-37-03 authenticated shell navigation de-duplication"
status: done
owners: "agents"
created: 2026-06-18
updated: 2026-06-19
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
  - "Given authenticated home now owns app navigation through the app-card affordance, when the authenticated sidebar or mobile drawer renders, then it does not duplicate app-card links for Klassrumskartan, Provhantering, Ljudtranskribering, or Kodredigerare."
  - "Given teachers can propose new app ideas, when a normal signed-in user opens authenticated navigation, then Föreslå verktyg is available outside contributor-only gating."
  - "Given route-visible shell navigation changes, when the slice closes, then focused layout/router tests and live browser proof cover desktop sidebar, mobile drawer, focus mode, and protected navigation through the HuleEdu browser-session ceremony."
  - "Given immersive and workspace-heavy routes have special chrome behavior, when navigation is realigned, then Flunk-Out Frenzy immersive mode and Klassrumskartan's wider sidebar breakpoint remain unchanged."
---

# PR-0365: ST-37-03 Authenticated Shell Navigation De-Duplication

## Problem

The authenticated sidebar still reflects a generic catalog/tool hierarchy. It
no longer exposes the retired `Mina körningar` link, but the attempted
app-lane-first sidebar duplicated the authenticated home app-card affordance.
Manual validation on 2026-06-19 showed that duplicating `Klassrumskartan`,
`Provhantering`, `Ljudtranskribering`, and `Kodredigerare` in the left rail
makes the shell too busy and competes with the clearer app navigation already
laid out in the home surface.

## Goal

Keep the authenticated sidebar as utility/platform navigation while
authenticated home owns app navigation through the app cards.

The approved navigation order is:

```text
Hem
Mina filer
Föreslå verktyg            all users
Katalog
Profil

Mina verktyg               contributor+
Hantera verktyg            admin+
Användare                  superuser+
Granska förslag            admin+
```

The sidebar must not render app-card duplicates for `Klassrumskartan`,
`Provhantering`, `Ljudtranskribering`, or `Kodredigerare`. `Hjälp` must remain
owned by the top authenticated header rather than being duplicated in the
sidebar/mobile drawer. No visible group labels such as `Appar`, `Plattform`,
`Vad du gör`, or similar explanatory chrome should be introduced.

## Non-goals

- No public landing/header rewrite.
- No app-id or route rename.
- No authenticated home app-card rewrite.
- No changes to immersive game route behavior or Klassrumskartan workspace
  route-shell internals beyond navigation entrypoints.
- No `Dokumentkonvertering` persistent sidebar link until a reviewed truthful
  route exists.

## Review gate

`REV-PR-0365` must be approved before code implementation begins.

## Implementation plan

1. [x] Add a focused red `AuthSidebar` behavior test proving that current
   navigation duplicated authenticated home app-card links while still hiding
   `Föreslå verktyg` from normal users. Run that test inside the same focused
   shell lane as `AuthLayout.spec.ts` and `App.spec.ts` so the red/green proof
   keeps the route-visible shell boundaries in view.
2. [x] Remove `Klassrumskartan`, `Provhantering`, `Ljudtranskribering`, and
   `Kodredigerare` from the persistent sidebar/mobile drawer navigation.
3. [x] Keep `Hem`, `Mina filer`, `Föreslå verktyg`, `Katalog`, and `Profil`
   available in the normal signed-in sidebar. `Föreslå verktyg` must be
   visible to all signed-in users, and `Hjälp` must stay in the top auth bar
   instead of duplicating into the sidebar/mobile drawer.
4. [x] Keep `Mina verktyg`, admin, and superuser surfaces role-gated below the
   normal user links.
5. [x] Do not reintroduce `Mina körningar` as persistent shell navigation; the
   legacy route may remain for deep-link compatibility until a separate
   route-retirement slice handles it.
6. [x] Preserve focus mode, mobile drawer behavior, immersive route behavior, and
   Klassrumskartan's `xl` sidebar breakpoint.

## Implementation evidence

- Runtime/sidebar changes are limited to:
  - `frontend/apps/skriptoteket/src/components/layout/AuthSidebar.vue`
  - `frontend/apps/skriptoteket/src/components/layout/AuthSidebar.spec.ts`
- The persistent authenticated sidebar/mobile drawer now starts with `Hem`,
  `Mina filer`, `Föreslå verktyg`, `Katalog`, and `Profil`, with role-gated
  links below that shared utility block.
- `Föreslå verktyg` renders for all signed-in users instead of remaining
  contributor-only.
- No visible group labels were added, authenticated home remains the owned
  app-entry surface, the top auth bar retains sole ownership of `Hjälp`,
  `Dokumentkonvertering` remains absent from persistent navigation, and
  `Mina körningar` remains absent from the persistent shell.
- `scripts/playwright_pr_0365_authenticated_shell_navigation.py` now proves the
  corrected utility-first contract and rejects duplicate app labels/targets.
- The existing `AuthLayout.spec.ts` and `App.spec.ts` shell guards stayed in
  the focused lane and continued to protect Flunk-Out Frenzy immersive mode,
  the Klassrumskartan `xl` breakpoint contract, and auth-route recovery.

## Verification

- Red first:
  `pdm run fe-test -- --run src/components/layout/AuthSidebar.spec.ts src/components/layout/AuthLayout.spec.ts src/App.spec.ts`
  failed against the final de-duplication contract because the sidebar still
  rendered `Hjälp` after `Profil` instead of leaving help solely in the top
  authenticated header.
- Green:
  `pdm run fe-test -- --run src/components/layout/AuthSidebar.spec.ts src/components/layout/AuthLayout.spec.ts src/App.spec.ts`
  passed with 10 tests.
- `pdm run test tests/unit/scripts/test_playwright_script_surface.py` passed
  with 3 tests after keeping the retained proof entrypoint on the approved
  script surface.
- `pdm run fe-type-check` passed.
- `pdm run fe-lint` passed.
- Protected live proof passed through the sanctioned HuleEdu browser-session
  ceremony:
  `pdm run python -m scripts.playwright_pr_0365_authenticated_shell_navigation --base-url http://localhost:5173`
  retained desktop-sidebar and mobile-drawer artifacts under
  `.artifacts/playwright-pr-0365-authenticated-shell-navigation/20260619T212625Z/`.

## Test plan

- Red first:
  `pdm run fe-test -- --run src/components/layout/AuthSidebar.spec.ts src/components/layout/AuthLayout.spec.ts src/App.spec.ts`
- Green:
  `pdm run fe-test -- --run src/components/layout/AuthSidebar.spec.ts src/components/layout/AuthLayout.spec.ts src/App.spec.ts`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run test tests/unit/scripts/test_playwright_script_surface.py`
- Browser proof for desktop sidebar and mobile drawer through the HuleEdu
  browser-session ceremony.
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Rollback plan

Restore the prior authenticated sidebar ordering and remove any extracted
navigation model.
