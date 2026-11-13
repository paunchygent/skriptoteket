---
type: reference
id: REF-SKRIPT-MOCKUP-st-26-06-share-link-ux-and-page-renderer-direction
title: ST-26-06 share link UX and page renderer direction
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: active
reference_kind: mockup
summary: ST-26-06 share link UX and page renderer direction
---

## Intent

### Source: Purpose

Retain the approved visual direction for the `ST-26-06` share-link follow-up
work.

This bundle intentionally keeps the design evidence as raster mockups. The
follow-up implementation must be visually inspected against these images rather
than relying on low-value structural tests as a proxy for design quality.

## Package Manifest

### Source: Assets

- [Share popover and mobile bottom sheet](share-popover-and-bottom-sheet-mockup.png)
- [Shared seating page spatial classroom map](shared-seating-page-spatial-map-mockup.png)

## Design Interpretation

The source does not provide a separate design interpretation section; no additional design interpretation is recorded.

## Runtime And Proof Boundary

The source does not provide a separate runtime and proof boundary section; no additional runtime and proof boundary is recorded.

## Governing Links And Follow-Up

### Source: Direction

- The authenticated workspace manages existing links through an anchored
  `Dela` popover on desktop and a bottom sheet on mobile.
- Active links stay visible by default; revoked links leave the active list and
  move to a collapsed archive.
- Copy/revoke feedback is toast/snackbar based, with undo for revoke where the
  implementation slice can safely support it.
- Seating share pages must render a real spatial classroom map rather than a
  row/place card grid.

### Source: ST-26-06 Share Link UX And Page Renderer Direction
