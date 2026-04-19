---
type: pr
id: PR-0270
title: "ST-32-08: landing authenticated-value copy refresh"
status: done
owners: "agents"
created: 2026-04-19
updated: 2026-04-19
stories:
  - "ST-32-08"
tags: ["frontend", "ux", "landing-page", "copy", "mockup"]
dependencies:
  - "EPIC-32"
  - "ST-32-07"
  - "ST-32-08"
  - "PR-0237"
  - "PR-0239"
  - "PR-0247"
acceptance_criteria:
  - "Given the landing copy is still awaiting user direction, when implementation begins, then the developer first uses `docs/mockups/st-32-08-landing-authenticated-value-copy-alternatives/index.html` and records the selected alternative before changing production Vue code."
  - "Given the featured Klassrumskartan copy currently says `Skapa salen, placera eleverna, spara som PDF. Allt i webbläsaren.`, when this slice ships, then it is replaced with the approved copy that includes PDF-or-Excel export and saved authenticated classes, groupings, and classroom placements."
  - "Given the three-step Klassrumskartan strip currently uses numeric markers, when this slice ships, then the visible step markers use `I`, `II`, and `III` while preserving accessible section structure."
  - "Given the authenticated-value section currently over-focuses on saved settings/files and the code editor, when this slice ships, then it also clearly communicates access to more apps and work tools plus the ability to suggest new apps that would ease teacher work."
  - "Given the landing page follows the approved ST-32-07/ST-32-08 visual language, when this copy refresh ships, then it keeps the existing brutalist-academic section rhythm and avoids turning the section into a generic card stack."
  - "Given all Swedish landing copy remains product-owner approved language, when implementation ships, then focused frontend tests assert the approved copy and a live browser proof is recorded in `.codex/handoff.md`."
---

## Problem

The current landing page now has the correct public-entry shape, but the below-the-fold account
section still makes signed-in value feel too narrow. It mainly promises saved settings/files and
approval-gated code-editor access, which makes Skriptoteket feel like `Klassrumskartan + editor`
instead of a broader teacher tool surface.

The featured `Klassrumskartan` copy also needs a small product-truth update: export should mention
PDF or Excel, and signed-in persistence should name the saved classes, groupings, and classroom
placements.

## Goal

Ship the approved landing copy refresh after user selection from the mockup alternatives:

- update the `Klassrumskartan` showcase description
- change visible step markers from `01`/`02`/`03` to `I`/`II`/`III`
- broaden the signed-in section so it covers more apps, work tools, and teacher suggestions for
  future apps
- keep code-editor access as a secondary approved-capability path rather than the whole signed-in
  value proposition

## Non-goals

- Do not reopen the `ST-32-07` header, hero, or primary CTA hierarchy.
- Do not change public curated-app routing, auth continuation, or account provisioning behavior.
- Do not add new public apps in this slice.
- Do not implement the production Vue copy before the mockup direction is selected.

## Implementation Plan

1. Review
   `docs/mockups/st-32-08-landing-authenticated-value-copy-alternatives/index.html`
   with the user and record the selected alternative.
2. Update `LandingFeaturedClassroom.vue` with the approved showcase copy and `I`/`II`/`III`
   markers.
3. Update `LandingAuthenticatedPreview.vue` with the approved signed-in section structure and
   copy.
4. Update `HomeView.spec.ts` and component-level assertions so tests lock the chosen wording and
   marker behavior.
5. Run the focused frontend checks and live landing-page proof.
6. Record the exact verification in `.codex/handoff.md`.

## Test Plan

- `pdm run fe-test -- --run src/views/HomeView.spec.ts`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- Live browser proof on `http://127.0.0.1:5173/`
- `pdm run docs-validate`
- `git diff --check`

## Rollback Plan

Restore the previous `LandingFeaturedClassroom.vue`,
`LandingAuthenticatedPreview.vue`, and focused test expectations. Keep the mockup bundle and this
PR task as retained design history unless the chosen direction itself is rejected.

## Implementation Summary

This slice is complete.

- The user selected Alternative B from the mockup bundle, with a final row I description tweak:
  `Använd alla Skriptotekets appar och verktyg som finns tillgängliga.`
- `LandingFeaturedClassroom.vue` now uses the PDF-or-Excel export copy, the signed-in persistence
  sentence, and visible `I` / `II` / `III` step markers.
- `LandingAuthenticatedPreview.vue` now leads with more apps and work tools, includes teacher app
  suggestions, keeps saved work as the persistence row, and removes the previous code-editor ledger
  row from the signed-out landing page.
- `HomeView.spec.ts` asserts the locked copy, Roman markers, shared-auth links, and absence of
  `kodredigeraren` / `Kräver ansökan` in the landing ledger.
- The approved copy is now locked in
  `docs/reference/ref-public-landing-copy-lock.md`.

## Verification

- `pdm run fe-test -- --run src/views/HomeView.spec.ts` passed (`2 passed`).
- `pdm run fe-type-check` passed.
- `pdm run fe-lint` passed with `0 warnings`.
- Live Playwright landing proof passed on `http://127.0.0.1:5173/`; screenshot retained at
  `.artifacts/st-32-08-landing-proof/landing.png`.
- `pdm run docs-validate` passed during implementation.
- `git diff --check` passed during implementation.
- Closeout rerun passed `pdm run docs-validate`, `pdm run handoff-validate`,
  `pdm run fe-test -- --run src/views/HomeView.spec.ts`, `pdm run fe-type-check`,
  `pdm run fe-lint`, and `git diff --check`.
