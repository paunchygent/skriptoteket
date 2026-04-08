---
type: pr
id: PR-0247
title: "ST-32-08: landing showcase SVG asset cutover and backup preservation"
status: done
owners: "agents"
created: 2026-04-08
updated: 2026-04-08
stories:
  - "ST-32-08"
tags: ["frontend", "ux", "landing-page", "assets", "svg"]
acceptance_criteria:
  - "Given the signed-out landing showcase currently embeds its hero and step illustrations as inline Vue SVG markup, when this slice ships, then those drawings are sourced from versioned SPA asset files instead of inline resources."
  - "Given the user wants the shipped drawings to remain revertable and referenceable, when the new SVG asset structure is introduced, then the current production drawings are preserved as backup SVG assets alongside the approved redesign set."
  - "Given the landing page must keep the current signed-out narrative and structure, when the asset cutover happens, then `HomeView.vue` section ordering, CTA hierarchy, and authenticated-preview behavior stay unchanged."
  - "Given Vite can inline small SVG imports by default, when the new assets are wired, then the implementation explicitly keeps them as file assets rather than bundled inline data URLs."
---

## Problem

The signed-out landing showcase currently keeps its hero illustration and three-step symbols inside
Vue component templates as inline SVG markup.

That makes iteration and revert work awkward because the artwork is not versioned as standalone SPA
assets, and the currently shipped drawings would have to be reconstructed by hand if we ever wanted
to refer back to them.

## Goal

Move the landing showcase artwork to standalone SPA asset files, activate the approved redesign-v5
set, and preserve the current shipped drawings as backup SVG assets in the repo.

## Non-goals

- Changing landing copy, CTA hierarchy, or section ordering.
- Changing the authenticated-only preview ledger.
- Reopening the signed-out auth-entry follow-up planned under `ST-32-10` / `PR-0242`.

## Implementation plan

1. Create a versioned SPA asset folder for the landing showcase artwork.
2. Save the current shipped hero and step drawings as backup SVG assets.
3. Save the approved redesign-v5 hero and step drawings as the active replacement set.
4. Replace inline SVG markup in the landing showcase Vue components with file-asset imports.
5. Force file-based delivery for the SVG imports so the assets do not regress into inline resources.
6. Update focused landing tests and the handoff/docs index records.

## Test plan

- `pdm run fe-test -- --run src/views/HomeView.spec.ts`
- `pdm run fe-type-check`
- `pdm run fe-build`
- Live signed-out browser proof on `http://127.0.0.1:5173/`
- `pdm run docs-validate`

## Rollback plan

- Repoint the landing components from the redesign-v5 SVG asset files to the preserved backup SVG
  assets without reconstructing inline markup.

## Implementation note (2026-04-08)

This slice shipped the landing artwork as versioned SPA assets under
`frontend/apps/skriptoteket/src/assets/home/klassrumskartan/landing/` with two parallel sets:

- `current/` preserves the original shipped hero and step drawings as revertable backup SVG assets
- `redesign-v5/` carries the approved replacement set from `docs/mockups/klassrumskartan-svg-redesign-v5/`

The live components now consume those files via Vite `?no-inline` imports so the hero and step
artwork ship as external file assets instead of inline Vue SVG markup or inlined data URLs.
