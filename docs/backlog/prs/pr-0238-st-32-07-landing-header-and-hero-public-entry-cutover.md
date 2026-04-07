---
type: pr
id: PR-0238
title: "ST-32-07: landing header and hero public-entry cutover"
status: ready
owners: "agents"
created: 2026-04-07
updated: 2026-04-07
stories:
  - "ST-32-07"
tags: ["frontend", "ux", "landing-page", "public-access"]
dependencies:
  - "ST-32-07"
  - "PR-0237"
acceptance_criteria:
  - "Given an unauthenticated visitor opens `/`, when the landing header renders, then a direct `Klassrumskartan` entry is visible and routes to `/public/apps/classroom.group-seating-studio`."
  - "Given the landing header lives in the shared unauthenticated shell, when this slice ships, then header behavior is explicitly defined and verified on `/`, `/register`, password-recovery flows, and `/public/apps/classroom.group-seating-studio`."
  - "Given the hero defines the primary visitor next step, when the hero CTA row renders, then opening the public Klassrumskartan route is the primary action while `Skapa konto` and `Logga in` remain available as clearly secondary paths."
  - "Given both the header and hero appear above the fold, when this slice ships, then the header-level `Klassrumskartan` link remains a quiet discoverability/navigation affordance and the hero remains the only strong primary CTA."
  - "Given the landing copy should describe the public app truthfully, when the new hero copy ships, then it frames Klassrumskartan as a real public usage path rather than a demo, teaser, or login bait."
  - "Given all Swedish copy in this slice is user-facing and provisional until explicit user sign-off, when implementation happens, then draft copy stays short, conversational, verb-led, non-technical, and free of sales language or internal product terminology."
  - "Given this slice changes a layout-heavy public surface, when implementation begins, then it follows the approved `PR-0237` mockup rather than improvising production layout structure in code."
---

## Problem

The current landing header and hero still signal that authentication is the main way into
Skriptoteket, even though Klassrumskartan is now a real public app.

That makes the most important public entry path harder to discover than it should be.

The shared unauthenticated shell also means this slice touches more than the `/` page alone:
header-level behavior must stay coherent across signed-out routes that reuse the same layout.

## Goal

Cut over the landing header and hero so the first-screen hierarchy matches the product:
public app first, account paths second.

## Non-goals

- Building the below-the-fold showcase sections in this slice.
- Adding unmatched-route handling in this slice.
- Rewriting authenticated dashboard behavior.

## Implementation plan

1. Use the approved `PR-0237` mockup as the source layout.
2. Update the shared landing header in `LandingLayout.vue` to expose a direct `Klassrumskartan`
   entry as quiet discoverability nav rather than as a second primary button.
3. Reorder the hero CTA hierarchy so the public app is primary and the hero remains the only strong
   primary action above the fold.
4. Refresh hero copy to support the show-first product direction using short, clear draft Swedish
   copy only; do not treat any sentence as final until user sign-off.
5. Add or update focused frontend specs in the visible-contract layers, including `HomeView.spec.ts`
   plus at least one shared-shell assertion in `LandingLayout` or `App`, and record a live landing
   check in `.agents/handoff.md`.

## Test plan

- Focused frontend tests for the unauthenticated landing header and hero CTA hierarchy, centered on
  `HomeView.spec.ts` plus at least one shared-shell assertion in `LandingLayout` or `App`.
- Live browser proof on `http://127.0.0.1:5173/` and
  `http://127.0.0.1:5173/public/apps/classroom.group-seating-studio`
- Live signed-out shell checks on `/register` and the password-recovery routes that reuse the
  landing shell
- `pdm run fe-type-check`
- `pdm run docs-validate`

## Rollback plan

- Revert only the landing header and hero CTA hierarchy changes if the public-entry emphasis proves
  misleading, without touching the public-app route itself.
