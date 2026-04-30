---
type: pr
id: PR-0276
title: "ST-26-06 spatial share-page renderer and grouping polish"
status: ready
owners: "agents"
created: 2026-04-30
updated: 2026-04-30
stories:
  - "ST-26-06"
tags: ["backend", "frontend", "renderer", "klassrumskartan", "sharing", "mockup"]
dependencies:
  - "PR-0274"
acceptance_criteria:
  - "Given anyone opens a seating share link, when the artifact is active, then the page renders a real spatial classroom map with room fixtures, benches, seats, empty seats, and placed students rather than a row/place card grid."
  - "Given the shared seating page is viewed at desktop and phone widths, when visually inspected, then it follows the approved spatial-map mockup and remains readable without editor chrome or app APIs."
  - "Given grouping share links remain card-based, when grouping pages render, then their cards receive responsive spacing, hierarchy, and print polish consistent with the share-page visual language."
  - "Given hostile class, room, group, fixture, or student text exists, when share pages render metadata and body content, then escaping, no-script behavior, `noindex,nofollow`, and cache policy remain covered by contract tests."
  - "Given this is a visual rendering correction, when the slice is reviewed, then design acceptance is based on visual inspection screenshots against `docs/mockups/st-26-06-share-link-ux-and-page-renderer/shared-seating-page-spatial-map-mockup.png`, while automated tests cover security/provenance and renderer contracts only."
---

## Problem

The current share renderer technically emits responsive HTML/CSS, but seating
shares are rendered as generic cards with `Rad` and `plats` text. That is not a
classroom map and does not meet the product direction for shareable seating
plans.

## Goal

Reuse or extract the existing poster/room-scene rendering model so seating
share pages preserve spatial classroom structure: whiteboard, teacher desk,
door, benches, seats, empty seats, and students. Keep grouping pages as cards,
but improve their responsive and print presentation.

## Non-goals

- No change to share-token authorization, slug semantics, ownership, TTL, or
  revocation rules.
- No live draft sharing.
- No SPA/editor controls on share pages.
- No visual-quality claims from structural tests alone.

## Implementation plan

1. Extract share-page-safe room-scene rendering from the existing poster
   renderer or create a shared renderer helper that consumes the canonical
   poster scene.
2. Replace the seating share card grid with a spatial classroom scene using the
   prepared seating export contract.
3. Add responsive desktop/mobile CSS for the share page, including controls or
   display toggles only if they are part of the static shared page and do not
   call app APIs.
4. Preserve renderer provenance, presentation hash, content hash, escaping,
   metadata, and cache behavior.
5. Polish grouping share card layout so it belongs to the same share-page
   family.

## Test plan

- Renderer/security tests for escaping, no scripts, robots metadata, cache
  headers, provenance, and content hashes.
- Contract tests proving seating share HTML is produced from the canonical
  poster/room-scene model.
- Browser screenshots at desktop and phone widths for visual inspection against
  the approved mockup.
- `pdm run typecheck`
- Focused backend renderer/share route tests.
- `pdm run docs-validate`
- `git diff --check`

## Rollback plan

Restore the prior static share renderer while keeping existing share artifacts
and routes available.
