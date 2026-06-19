---
type: pr
id: PR-0372
title: "ST-37-04 public landing header simplification"
status: done
owners: "agents"
created: 2026-06-19
updated: 2026-06-19
stories:
  - "ST-37-04"
tags: ["frontend", "ux", "landing-page", "navigation"]
dependencies:
  - "PR-0371"
  - "REF-public-landing-copy-lock"
acceptance_criteria:
  - "Given the public hero already links to Klassrumskartan, when the signed-out landing header renders, then it no longer exposes a separate Klassrumskartan navigation link."
  - "Given the signed-out header is small-screen navigation, when it renders on mobile widths, then the brand, Logga in, and Hjälp stay on one row without a hamburger."
  - "Given Logga in and Hjälp are sibling header actions, when the header renders, then both actions use the same font treatment, casing, spacing, and hover/focus style."
---

# PR-0372: ST-37-04 Public Landing Header Simplification

## Problem

After `PR-0371`, the public landing page has a strong hero-owned
Klassrumskartan entrypoint. Keeping a second `Klassrumskartan` link in the
header competes with that hierarchy, especially on small screens. The public
header should be a simple single-row utility bar.

## Goal

Simplify the signed-out landing header:

- keep the Skriptoteket brand;
- keep `Logga in`;
- keep `Hjälp`;
- remove the header-level `Klassrumskartan` link;
- make `Logga in` and `Hjälp` visually consistent;
- keep all header links on one row on small screens.

## Non-goals

- No hero copy or CTA rewrite.
- No authenticated shell changes; `PR-0365` owns that surface.
- No route, app-id, backend/API, HuleEdu auth, or help-content changes.
- No hamburger menu or new public navigation drawer.

## Implementation plan

1. [x] Add a focused red `LandingLayout` test proving the header no longer renders
   `Klassrumskartan`, still renders `Logga in` and `Hjälp`, and keeps the
   shared HuleEdu login continuation URL.
2. [x] Update `LandingLayout.vue` to remove the public Klassrumskartan nav link
   and render `Logga in` and `Hjälp` as same-style header actions on one row.
3. [x] Keep the public hero-owned Klassrumskartan CTA unchanged.
4. [x] Update `REF-public-landing-copy-lock`, story docs, handoff evidence, and
   retained review evidence.

## Implementation evidence

- Runtime/header changes are limited to:
  - `frontend/apps/skriptoteket/src/components/layout/LandingLayout.vue`
  - `frontend/apps/skriptoteket/src/components/layout/LandingLayout.spec.ts`
- The signed-out header no longer renders a separate `Klassrumskartan` link;
  the public hero keeps sole ownership of that CTA.
- `Logga in` remains wired to the existing shared HuleEdu continuation URL.
- `Logga in` and `Hjälp` now share the same font size, weight, casing,
  spacing, hover underline, and focus-outline treatment in the header action
  row without adding a hamburger or extra public navigation.

## Verification

- Red first:
  `pdm run fe-test -- --run src/components/layout/LandingLayout.spec.ts`
  failed against the old header because `Klassrumskartan` still rendered in
  the signed-out header.
- Green:
  `pdm run fe-test -- --run src/components/layout/LandingLayout.spec.ts`
  passed with 2 tests.
- Combined frontend regression lane:
  `pdm run fe-test -- --run src/components/layout/AuthSidebar.spec.ts src/components/layout/AuthLayout.spec.ts src/App.spec.ts src/components/layout/LandingLayout.spec.ts src/views/HomeView.spec.ts`
  passed with 17 tests.
- Live in-app-browser proof against `http://localhost:5173/`:
  - desktop snapshot confirmed the header contains only the brand, `Logga in`,
    and `Hjälp`, with no `Klassrumskartan` nav link;
  - mobile snapshot confirmed the brand, `Logga in`, and `Hjälp` remain on the
    same top row with no hamburger.
- Retained in-app-browser screenshots:
  - `.artifacts/pr-0372-public-landing-header-simplification/public-landing-desktop.png`
  - `.artifacts/pr-0372-public-landing-header-simplification/public-landing-mobile.png`

## Test plan

- Red first:
  `pdm run fe-test -- --run src/components/layout/LandingLayout.spec.ts`
- Green:
  `pdm run fe-test -- --run src/components/layout/LandingLayout.spec.ts src/views/HomeView.spec.ts`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`
- Live public landing browser proof at desktop and mobile widths.

## Rollback plan

Restore the prior `LandingLayout.vue` header composition and revert the focused
header tests and copy-lock update.
