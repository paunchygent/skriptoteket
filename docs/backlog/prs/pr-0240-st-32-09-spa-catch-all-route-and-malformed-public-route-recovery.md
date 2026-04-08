---
type: pr
id: PR-0240
title: "ST-32-09: SPA catch-all route and malformed public-route recovery"
status: ready
owners: "agents"
created: 2026-04-07
updated: 2026-04-07
stories:
  - "ST-32-09"
tags: ["frontend", "routing", "public-access", "ux"]
dependencies:
  - "ST-32-09"
  - "ST-32-06"
acceptance_criteria:
  - "Given a visitor enters any unmatched SPA URL, when the route resolves, then Skriptoteket renders a visible not-found or recovery surface instead of an empty layout shell."
  - "Given a visitor enters `/public/<app-id>` instead of `/public/apps/<app-id>`, when the route resolves, then the page explains the canonical public curated-app route shape and offers the correct path for `classroom.group-seating-studio`."
  - "Given the canonical route `/public/apps/classroom.group-seating-studio` is used, when this slice ships, then the current public Klassrumskartan bootstrap and guest workspace behavior remain unchanged."
---

## Problem

Malformed public URLs currently fail badly in the SPA: the landing shell still renders, but the
route body is empty because no matched route component exists.

That makes a simple URL-shape mistake look like a broken product.

## Goal

Add explicit unmatched-route handling and a public-route recovery path so bad URLs fail visibly and
repairably.

## Non-goals

- Reworking the landing header or showcase sections in this slice.
- Replacing the signed-out login modal with the later dedicated auth-entry page from `PR-0242`.
- Changing backend history-fallback behavior.
- Changing the public curated-app route shape itself.

## Implementation plan

1. Add a final SPA catch-all route.
2. Introduce a small not-found or recovery view that renders inside the existing landing or auth
   shells.
3. Add specific guidance for malformed public curated-app URLs that are missing `/apps/`.
4. Lock the behavior with focused router and view tests.
5. Run a live browser proof for both malformed and canonical URLs.

## Test plan

- Focused router/view tests for unmatched-route recovery.
- Live browser proof on:
  - `http://127.0.0.1:5173/public/classroom.group-seating-studio`
  - `http://127.0.0.1:5173/public/apps/classroom.group-seating-studio`
- `pdm run fe-type-check`
- `pdm run docs-validate`

## Rollback plan

- Remove the catch-all route and recovery view if they introduce unintended route collisions, while
  keeping the public app entry surface unchanged.
