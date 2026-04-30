---
type: mockup
id: MOCK-st-26-06-share-link-ux-and-page-renderer
title: "ST-26-06 share link UX and page renderer direction"
status: approved
owners: "agents"
created: 2026-04-30
updated: 2026-04-30
tags: ["ST-26-06", "klassrumskartan", "sharing", "mockup"]
summary: "Approved visual direction for Klassrumskartan share-link management and shared seating-page spatial rendering."
canonical_preview: "share-popover-and-bottom-sheet-mockup.png"
submission_policy: "Use these mockups as the visual inspection baseline before changing production share-link management or public share-page rendering."
winner_policy: "The copied PNGs are the current product-owner direction; later iterations should replace or supersede them in this bundle."
---

# ST-26-06 Share Link UX And Page Renderer Direction

## Purpose

Retain the approved visual direction for the `ST-26-06` share-link follow-up
work.

This bundle intentionally keeps the design evidence as raster mockups. The
follow-up implementation must be visually inspected against these images rather
than relying on low-value structural tests as a proxy for design quality.

## Assets

- [Share popover and mobile bottom sheet](share-popover-and-bottom-sheet-mockup.png)
- [Shared seating page spatial classroom map](shared-seating-page-spatial-map-mockup.png)

## Direction

- The authenticated workspace manages existing links through an anchored
  `Dela` popover on desktop and a bottom sheet on mobile.
- Active links stay visible by default; revoked links leave the active list and
  move to a collapsed archive.
- Copy/revoke feedback is toast/snackbar based, with undo for revoke where the
  implementation slice can safely support it.
- Seating share pages must render a real spatial classroom map rather than a
  row/place card grid.
