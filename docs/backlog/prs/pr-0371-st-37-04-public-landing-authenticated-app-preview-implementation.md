---
type: pr
id: PR-0371
title: "ST-37-04 public landing authenticated-app preview implementation"
status: done
owners: "agents"
created: 2026-06-19
updated: 2026-06-19
stories:
  - "ST-37-04"
tags: ["frontend", "ux", "landing-page", "copy"]
dependencies:
  - "PR-0370"
  - "REF-public-landing-copy-lock"
acceptance_criteria:
  - "Given the signed-out landing page currently repeats Klassrumskartan below the hero, when the public landing renders after this slice, then it keeps the approved Klassrumskartan hero and replaces the repeated showcase with the approved authenticated-app preview."
  - "Given the product owner approved the PR-0370 HTML/CSS mockup, when production Vue changes are made, then the layout, hierarchy, and copy stay materially aligned with that mockup while preserving existing Vue structure and styling conventions where possible."
  - "Given labels, badges, Roman numerals, numeric markers, and category/meta labels were rejected, when the authenticated-app preview renders, then it contains none of those rejected markers and uses only the approved panel copy."
  - "Given public landing copy changes, when this slice closes, then `REF-public-landing-copy-lock`, focused landing tests, docs, retained review, and live browser proof all reflect the new production page."
---

# PR-0371: ST-37-04 Public Landing Authenticated-App Preview Implementation

## Problem

The approved PR-0370 landing direction is not yet implemented. The current
production signed-out page still repeats Klassrumskartan after a
Klassrumskartan-led hero, still uses the older generic authenticated-value
ledger, and did not yet reflect the product-owner requirement that the
authenticated-app preview reuse the same app symbols shown on authenticated
home.

## Goal

Implement the approved public landing update with minimal production changes:
keep the current public Klassrumskartan hero, remove the repeated
Klassrumskartan showcase, and render the approved account-backed app preview
with the product-owner-approved copy and the same app symbols used on
authenticated home.

## Non-goals

- No authenticated home redesign.
- No route, app-id, curated-app registry, backend/API, Sir Convert, HuleEdu,
  QTI, DOCX, or Exam.net contract changes.
- No new public capability promise beyond the approved copy.
- No new broad design-token or shared-resource changes.

## Implementation plan

1. [x] Add/update focused `HomeView` signed-out tests so they fail red while
   the old Klassrumskartan showcase, Roman numerals, `Kräver konto`, and
   generic authenticated ledger remain in production.
2. [x] Replace the production signed-out below-hero composition with the
   approved authenticated-app preview, preserving existing component boundaries
   and current Vue/Tailwind conventions where practical.
3. [x] Update `docs/reference/ref-public-landing-copy-lock.md` to match the
   approved copy and removed sections.
4. [x] Update PR/story/mockup docs and `.codex/handoff.md` with implementation
   and verification evidence.
5. [x] Run a retained independent review artifact before closing the slice.

## Implementation evidence

- Focused red-first coverage now lives in
  `frontend/apps/skriptoteket/src/views/HomeView.spec.ts` and locks:
  - approved hero and authenticated-preview copy
  - removal of the repeated Klassrumskartan showcase
  - removal of the retired generic ledger copy, Roman numerals, numeric
    markers, and `Kräver konto`
  - continued direct HuleEdu login/register targets
- Production runtime change is limited to:
  - `frontend/apps/skriptoteket/src/views/HomeView.vue`
  - `frontend/apps/skriptoteket/src/components/home/LandingAuthenticatedPreview.vue`
- The signed-out route no longer renders `LandingFeaturedClassroom`; the hero
  continues to use `LandingClassroomPreview`.
- The approved three-panel preview uses existing Vue/Tailwind conventions and
  the same symbol assets already used by authenticated home rather than
  introducing a new icon or diagram language.
- `REV-PR-0371` requested a proof fix because the retained mobile screenshot
  showed blank lower preview panels. The production landing preview now marks
  those three proof-critical reused app symbols with `loading="eager"`,
  `decoding="sync"`, and `fetchpriority="high"` so mobile/desktop captures
  render deterministically without changing authenticated-home app-card lazy
  behavior.
- HTML/CSS mockup screenshots were refreshed after the shared-symbol
  requirement:
  `.artifacts/pr-0370-public-landing-authenticated-app-preview/html-mockup-desktop.png`
  and
  `.artifacts/pr-0370-public-landing-authenticated-app-preview/html-mockup-mobile.png`.
- Live public landing browser proof was captured from `http://127.0.0.1:5173/`:
  `.artifacts/pr-0371-public-landing-authenticated-app-preview/public-landing-desktop.png`
  and
  `.artifacts/pr-0371-public-landing-authenticated-app-preview/public-landing-mobile.png`.
  The refreshed mobile artifact now visibly contains all three reused app
  symbols.

## Verification

- Red first:
  `pdm run fe-test -- --run src/views/HomeView.spec.ts` failed with the old
  production component restored because the rendered signed-out page did not
  contain `När du loggar in` and still contained the retired
  Klassrumskartan/showcase ledger copy.
- Green:
  `pdm run fe-test -- --run src/views/HomeView.spec.ts` passed with 5 tests.
- Review-fix rerun:
  `pdm run fe-test -- --run src/views/HomeView.spec.ts` passed with 5 tests
  after locking eager/synchronous/high-priority preview image loading.
- `pdm run fe-type-check` passed.
- `pdm run fe-lint` passed.
- `pdm run docs-validate` passed.
- `pdm run handoff-validate` passed.
- `git diff --check` passed.
- Refreshed public-route proof from `http://127.0.0.1:5173/` replaced
  `public-landing-desktop.png` and `public-landing-mobile.png`; direct visual
  inspection confirmed the mobile capture now shows all three approved reused
  app symbols.
- `REV-PR-0371` approved the implementation in
  `docs/backlog/reviews/review-pr-0371-public-landing-authenticated-app-preview-implementation.md`.

## Test plan

- Red first:
  `pdm run fe-test -- --run src/views/HomeView.spec.ts`
- Green:
  `pdm run fe-test -- --run src/views/HomeView.spec.ts`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`
- Live public landing browser proof at desktop and mobile widths.

## Rollback plan

Restore the previous signed-out landing composition and copy lock while leaving
authenticated home, routes, registry metadata, backend/API, and shared auth
surfaces unchanged.
